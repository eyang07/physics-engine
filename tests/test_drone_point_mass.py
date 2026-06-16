from __future__ import annotations

import numpy as np
import pytest
import sympy as sp

from engine.dynamics import Box, ControlledDiscreteSystem, DiscreteSystem
from systems.drone_point_mass import (
    DEFAULT_INITIAL_STATE,
    DEFAULT_OBSTACLE,
    DEFAULT_PLANE_INITIAL_STATE,
    DEFAULT_VERTICAL_AXIS_INITIAL_STATE,
    DRONE_CONTROLS,
    DRONE_STATE,
    DroneParams,
    ObstacleSpec,
    build_system,
    closed_loop,
    guard_band_control_law,
    guard_band_controller,
    horizontal_axis_closed_loop,
    horizontal_axis_control_law,
    horizontal_axis_rollout,
    horizontal_axis_system,
    horizontal_plane_closed_loop,
    horizontal_plane_rollout,
    horizontal_plane_system,
    safe_rollout,
    vertical_axis_closed_loop,
    vertical_axis_control_law,
    vertical_axis_rollout,
    vertical_axis_system,
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


def test_horizontal_axis_system_is_the_decoupled_q1_v1_subsystem() -> None:
    system = horizontal_axis_system()
    q1, v1 = DRONE_STATE[0], DRONE_STATE[3]
    u1 = DRONE_CONTROLS[0]
    assert system.state == (q1, v1)
    assert system.controls == (u1,)
    dt = sp.Rational(1, 4)
    assert sp.simplify(system.update[0] - (q1 + dt * v1 + dt**2 / 2 * u1)) == 0
    assert sp.simplify(system.update[1] - (v1 + dt * u1)) == 0
    assert system.control_bounds == Box(lower=(-1.0,), upper=(1.0,))


def test_horizontal_axis_closed_loop_matches_the_full_system_on_axis_1() -> None:
    closed = horizontal_axis_closed_loop()
    q1, v1 = DRONE_STATE[0], DRONE_STATE[3]
    assert isinstance(closed, DiscreteSystem)
    assert closed.state == (q1, v1)
    # Axis-1 law agrees with the full guard-band law's first component.
    full = guard_band_control_law()[DRONE_CONTROLS[0]]
    axis = horizontal_axis_control_law()[DRONE_CONTROLS[0]]
    sample = {q1: 0.8, v1: 0.25}
    assert axis.subs(sample) == full.subs({**sample, DRONE_STATE[1]: 0, DRONE_STATE[2]: 1,
                                           DRONE_STATE[4]: 0, DRONE_STATE[5]: 0})


def test_horizontal_axis_rollout_stays_in_geofence_and_brakes() -> None:
    params = DroneParams()
    result = horizontal_axis_rollout(params)
    q1 = result.states[:, 0]
    v1 = result.states[:, 1]
    q1_min, q1_max = params.q1_bounds
    assert np.all((q1 >= q1_min) & (q1 <= q1_max))  # P1 on axis 1
    assert np.all(np.abs(v1) <= params.horizontal_velocity_bound + 1e-9)  # P2
    assert q1.max() > q1_max - params.horizontal_band  # entered the guard band
    assert np.any(result.controls[:, 0] < 0)  # braked
    assert result.control_violation == 0.0


def test_vertical_reach_and_velocity_bound_match_spec() -> None:
    params = DroneParams()
    # max(u3Max - g, g - u3Min) = max(2-1, 1-0) = 1; B3 = reach * dt.
    assert params.vertical_reach == pytest.approx(1.0)
    assert params.vertical_velocity_bound == pytest.approx(params.vertical_reach * params.timestep)


def test_vertical_axis_system_is_the_decoupled_q3_v3_subsystem() -> None:
    system = vertical_axis_system()
    q3, v3 = DRONE_STATE[2], DRONE_STATE[5]
    u3 = DRONE_CONTROLS[2]
    assert system.state == (q3, v3)
    assert system.controls == (u3,)
    dt = sp.Rational(1, 4)
    # Carries the gravity offset on both the position and velocity updates.
    assert sp.simplify(system.update[0] - (q3 + dt * v3 + dt**2 / 2 * (u3 - 1))) == 0
    assert sp.simplify(system.update[1] - (v3 + dt * (u3 - 1))) == 0
    assert system.control_bounds == Box(lower=(0.0,), upper=(2.0,))


def test_vertical_axis_closed_loop_matches_the_full_system_on_axis_3() -> None:
    closed = vertical_axis_closed_loop()
    q3, v3 = DRONE_STATE[2], DRONE_STATE[5]
    assert isinstance(closed, DiscreteSystem)
    assert closed.state == (q3, v3)
    # Axis-3 law agrees with the full guard-band law's vertical component.
    full = guard_band_control_law()[DRONE_CONTROLS[2]]
    axis = vertical_axis_control_law()[DRONE_CONTROLS[2]]
    sample = {q3: 1.9, v3: 0.25}  # near the ceiling, ascending -> minimum thrust
    assert axis.subs(sample) == full.subs(
        {**sample, DRONE_STATE[0]: 0, DRONE_STATE[1]: 0, DRONE_STATE[3]: 0, DRONE_STATE[4]: 0}
    )


def test_vertical_axis_rollout_stays_between_floor_ceiling_and_brakes() -> None:
    params = DroneParams()
    result = vertical_axis_rollout(params)
    q3 = result.states[:, 0]
    v3 = result.states[:, 1]
    q3_min, q3_max = params.q3_bounds
    assert np.all((q3 >= q3_min) & (q3 <= q3_max))  # P1 floor/ceiling invariance
    assert np.all(np.abs(v3) <= params.vertical_velocity_bound + 1e-9)  # P2 (B3)
    assert q3.max() > q3_max - params.ceiling_band  # entered the ceiling guard band
    assert np.any(result.controls[:, 0] < params.hover_thrust)  # braked below hover
    assert result.control_violation == 0.0


def test_default_vertical_initial_state_is_inside_the_inner_altitude_set() -> None:
    params = DroneParams()
    q3, v3 = DEFAULT_VERTICAL_AXIS_INITIAL_STATE
    assert params.q3_bounds[0] + params.floor_band <= q3 <= params.q3_bounds[1] - params.ceiling_band
    assert abs(v3) <= params.vertical_velocity_bound + 1e-9


@pytest.mark.parametrize(
    ("kwargs", "match"),
    [
        ({"radius": 0.0}, "obstacle radius must be positive"),
        ({"standoff_radius": 0.25}, "standoff radius must exceed"),
    ],
)
def test_obstacle_spec_validates_invariants(kwargs, match) -> None:
    with pytest.raises(ValueError, match=match):
        ObstacleSpec(**kwargs)


def test_horizontal_plane_system_is_the_coupled_q1_q2_subsystem() -> None:
    system = horizontal_plane_system()
    q1, q2, v1, v2 = DRONE_STATE[0], DRONE_STATE[1], DRONE_STATE[3], DRONE_STATE[4]
    u1, u2 = DRONE_CONTROLS[0], DRONE_CONTROLS[1]
    assert system.state == (q1, q2, v1, v2)
    assert system.controls == (u1, u2)
    dt = sp.Rational(1, 4)
    assert sp.simplify(system.update[0] - (q1 + dt * v1 + dt**2 / 2 * u1)) == 0
    assert sp.simplify(system.update[2] - (v1 + dt * u1)) == 0
    assert system.control_bounds == Box(lower=(-1.0, -1.0), upper=(1.0, 1.0))


def test_horizontal_plane_closed_loop_matches_the_per_axis_laws() -> None:
    closed = horizontal_plane_closed_loop()
    q1, q2, v1, v2 = DRONE_STATE[0], DRONE_STATE[1], DRONE_STATE[3], DRONE_STATE[4]
    assert isinstance(closed, DiscreteSystem)
    assert closed.state == (q1, q2, v1, v2)
    # Each closed-loop axis agrees with the full guard-band law on its own axis:
    # near the +x wall moving out the law brakes (-1); near the -x wall it pushes
    # back in (+1).
    full = guard_band_control_law()
    sample = {q1: 0.8, q2: -0.8, v1: 0.25, v2: -0.25}
    rest = {DRONE_STATE[2]: 1, DRONE_STATE[5]: 0}
    assert full[DRONE_CONTROLS[0]].subs({**sample, **rest}) == sp.Integer(-1)
    assert full[DRONE_CONTROLS[1]].subs({**sample, **rest}) == sp.Integer(1)


def test_horizontal_plane_rollout_coasts_in_interior_and_avoids_the_obstacle() -> None:
    params = DroneParams()
    obstacle = DEFAULT_OBSTACLE
    result = horizontal_plane_rollout(params)
    q1 = result.states[:, 0]
    q2 = result.states[:, 1]
    # Pure coasting in the interior: the guard band commands no thrust and the
    # velocity stays at the initial value.
    assert result.control_violation == 0.0
    assert np.allclose(result.controls, 0.0)
    assert np.allclose(result.states[:, 2], DEFAULT_PLANE_INITIAL_STATE[2])
    assert np.allclose(result.states[:, 3], DEFAULT_PLANE_INITIAL_STATE[3])
    # The path stays outside the obstacle (and even outside the standoff annulus).
    cx, cy = obstacle.center
    distances = np.hypot(q1 - cx, q2 - cy)
    assert np.all(distances >= obstacle.standoff_radius)
