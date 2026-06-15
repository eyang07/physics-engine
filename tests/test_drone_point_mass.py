from __future__ import annotations

import numpy as np
import pytest
import sympy as sp

from engine.dynamics import Box, ControlledDiscreteSystem, DiscreteSystem
from systems.drone_point_mass import (
    DEFAULT_INITIAL_STATE,
    DRONE_CONTROLS,
    DRONE_STATE,
    DroneParams,
    build_system,
    closed_loop,
    guard_band_control_law,
    guard_band_controller,
    safe_rollout,
)


def test_build_system_is_exact_zoh_sampled_data_map() -> None:
    system = build_system()
    assert isinstance(system, ControlledDiscreteSystem)
    assert system.state == DRONE_STATE
    assert system.controls == DRONE_CONTROLS

    q1, q2, q3, v1, v2, v3 = DRONE_STATE
    u1, u2, u3 = DRONE_CONTROLS
    dt = sp.Rational(1, 4)
    # Exact double-integral position term (not an Euler step) and gravity on v3.
    assert sp.simplify(system.update[0] - (q1 + dt * v1 + dt**2 / 2 * u1)) == 0
    assert sp.simplify(system.update[2] - (q3 + dt * v3 + dt**2 / 2 * (u3 - 1))) == 0
    assert sp.simplify(system.update[5] - (v3 + dt * (u3 - 1))) == 0


def test_admissible_control_box_straddles_gravity() -> None:
    system = build_system()
    assert system.control_bounds == Box(
        lower=(-1.0, -1.0, 0.0),
        upper=(1.0, 1.0, 2.0),
    )


def test_closed_loop_is_single_valued_autonomous_map() -> None:
    closed = closed_loop()
    assert isinstance(closed, DiscreteSystem)
    assert closed.state == DRONE_STATE
    # No control symbols remain after substituting the feedback law.
    free = set().union(*(expr.free_symbols for expr in closed.update))
    assert not (free & set(DRONE_CONTROLS))


def test_guard_band_law_coasts_interior_and_hovers() -> None:
    law = guard_band_control_law()
    q1, q2, q3, v1, v2, v3 = DRONE_STATE
    interior = {q1: 0, q2: 0, q3: 1, v1: 0, v2: 0, v3: 0}
    # Interior: no horizontal thrust, hover (= gravity) on the vertical axis.
    assert law[DRONE_CONTROLS[0]].subs(interior) == 0
    assert law[DRONE_CONTROLS[1]].subs(interior) == 0
    assert law[DRONE_CONTROLS[2]].subs(interior) == 1


def test_guard_band_law_pushes_inward_at_walls() -> None:
    law = guard_band_control_law()
    q1, q2, q3, v1, v2, v3 = DRONE_STATE
    # Near the upper x-wall moving out -> brake with -uh.
    near_upper = {q1: 0.8, q2: 0, q3: 1, v1: 0.25, v2: 0, v3: 0}
    assert law[DRONE_CONTROLS[0]].subs(near_upper) == -1
    # Near the floor descending -> max upward thrust.
    near_floor = {q1: 0, q2: 0, q3: 0.1, v1: 0, v2: 0, v3: -0.25}
    assert law[DRONE_CONTROLS[2]].subs(near_floor) == 2


def test_numeric_controller_matches_symbolic_law() -> None:
    law = guard_band_control_law()
    controller = guard_band_controller()
    rng = np.random.default_rng(0)
    for _ in range(20):
        state = rng.uniform(low=[-1, -1, 0, -0.3, -0.3, -0.3], high=[1, 1, 2, 0.3, 0.3, 0.3])
        numeric = controller(0, state)
        symbolic = tuple(
            float(law[symbol].subs(dict(zip(DRONE_STATE, state))))
            for symbol in DRONE_CONTROLS
        )
        assert numeric == pytest.approx(symbolic)


def test_safe_rollout_is_deterministic() -> None:
    first = safe_rollout()
    second = safe_rollout()
    assert np.array_equal(first.states, second.states)
    assert np.array_equal(first.controls, second.controls)


def test_safe_rollout_keeps_geofence_and_velocity_bounds() -> None:
    params = DroneParams()
    result = safe_rollout(params)

    positions = result.states[:, :3]
    velocities = result.states[:, 3:]

    # P1: geofence invariance — every visited state stays in the safe box.
    (q1_min, q1_max) = params.q1_bounds
    (q2_min, q2_max) = params.q2_bounds
    (q3_min, q3_max) = params.q3_bounds
    assert np.all((positions[:, 0] >= q1_min) & (positions[:, 0] <= q1_max))
    assert np.all((positions[:, 1] >= q2_min) & (positions[:, 1] <= q2_max))
    assert np.all((positions[:, 2] >= q3_min) & (positions[:, 2] <= q3_max))

    # P2: per-axis velocity bound (self-reproducing velBound).
    tol = 1e-9
    assert np.all(np.abs(velocities) <= params.velocity_bound + tol)

    # The controller only ever emits admissible thrust.
    assert result.control_violation == 0.0


def test_safe_rollout_engages_the_guard_band() -> None:
    # Coasting in +x at the velocity bound, the drone reaches the guard band and
    # the controller brakes it: x-velocity is non-increasing once braking starts
    # and the trajectory settles strictly inside the wall.
    result = safe_rollout()
    q1 = result.states[:, 0]
    assert q1.max() > 0.75  # entered the guard band q1 >= q1Max - dh
    assert q1.max() < 1.0  # but never reached the wall
    # The applied x-thrust includes a braking command at some step.
    assert np.any(result.controls[:, 0] < 0)


def test_default_initial_state_is_inside_the_inner_set() -> None:
    params = DroneParams()
    q1, q2, q3 = DEFAULT_INITIAL_STATE[:3]
    assert params.q1_bounds[0] + params.horizontal_band <= q1 <= params.q1_bounds[1] - params.horizontal_band
    assert params.q2_bounds[0] + params.horizontal_band <= q2 <= params.q2_bounds[1] - params.horizontal_band
    assert params.q3_bounds[0] + params.floor_band <= q3 <= params.q3_bounds[1] - params.ceiling_band


@pytest.mark.parametrize(
    "kwargs, match",
    [
        ({"timestep": 0.0}, "timestep must be positive"),
        ({"horizontal_band": 0.0}, "guard bands must be positive"),
        ({"vertical_thrust_max": 0.5}, "u3Min < g < u3Max"),
        ({"horizontal_band": 1.5}, "guard bands overlap on axis 1"),
    ],
)
def test_drone_params_validates_invariants(kwargs, match) -> None:
    with pytest.raises(ValueError, match=match):
        DroneParams(**kwargs)


def test_velocity_bounds_match_the_spec_formulas() -> None:
    params = DroneParams()
    assert params.horizontal_velocity_bound == pytest.approx(0.25)  # Bh = uh*dt
    assert params.vertical_velocity_bound == pytest.approx(0.25)  # B3 = max(1, 1)*dt
    assert params.velocity_bound == pytest.approx(0.25)  # Vmax
    assert params.hover_thrust == pytest.approx(1.0)  # cancels gravity
