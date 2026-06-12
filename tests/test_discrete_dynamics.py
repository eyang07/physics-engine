from __future__ import annotations

import numpy as np
import pytest
import sympy as sp

from engine.dynamics import (
    Box,
    ControlledDiscreteSystem,
    DiscreteSystem,
    FirstOrderSystem,
    discrete_rollout,
    euler_discretization,
    rollout,
)
from systems.controlled_pendulum import build_system


def _logistic_map() -> tuple[DiscreteSystem, sp.Symbol, sp.Symbol]:
    x = sp.Symbol("x", real=True)
    r = sp.Symbol("r", positive=True)
    system = DiscreteSystem(state=(x,), update=(r * x * (1 - x),), parameters=(r,))
    return system, x, r


def _double_integrator() -> tuple[ControlledDiscreteSystem, sp.Symbol, sp.Symbol, sp.Symbol]:
    x, v = sp.symbols("x v", real=True)
    u = sp.Symbol("u", real=True)
    system = ControlledDiscreteSystem(
        state=(x, v),
        controls=(u,),
        update=(x + sp.Rational(1, 10) * v, v + sp.Rational(1, 10) * u),
        control_bounds=Box(lower=(-1.0,), upper=(1.0,)),
    )
    return system, x, v, u


def test_discrete_system_structure() -> None:
    system, x, r = _logistic_map()

    fixed_points = system.fixed_points()
    assert {point[x] for point in fixed_points} == {0, (r - 1) / r}
    assert sp.simplify(system.jacobian()[0, 0] - r * (1 - 2 * x)) == 0
    assert system.linearization({x: 0.0}, {r: 2.0})[0, 0] == 2.0

    with pytest.raises(ValueError, match="same length"):
        DiscreteSystem(state=(x,), update=(x, x))


def test_discrete_iterate_is_deterministic() -> None:
    system, _x, r = _logistic_map()
    steps, states = system.iterate((0.2,), 60, substitutions={r: 2.0})

    assert steps[-1] == 60
    assert states[-1, 0] == pytest.approx(0.5)
    _, repeated = system.iterate((0.2,), 60, substitutions={r: 2.0})
    assert np.array_equal(states, repeated)

    with pytest.raises(ValueError, match="unresolved"):
        system.iterate((0.2,), 10)
    with pytest.raises(ValueError, match="at least 1"):
        system.iterate((0.2,), 0, substitutions={r: 2.0})


def test_controlled_discrete_validation() -> None:
    x, v = sp.symbols("x v", real=True)
    u = sp.Symbol("u", real=True)

    with pytest.raises(ValueError, match="non-empty"):
        ControlledDiscreteSystem(state=(x,), controls=(), update=(x,))
    with pytest.raises(ValueError, match="disjoint"):
        ControlledDiscreteSystem(state=(x, v), controls=(x,), update=(x, v))
    with pytest.raises(ValueError, match="control_bounds"):
        ControlledDiscreteSystem(
            state=(x, v),
            controls=(u,),
            update=(x, v + u),
            control_bounds=Box(lower=(-1.0, -1.0), upper=(1.0, 1.0)),
        )


def test_closed_loop_reduction_is_schur_stable() -> None:
    system, x, v, u = _double_integrator()
    g1, g2 = sp.symbols("g1 g2", positive=True)

    closed = system.closed_loop({u: -g1 * x - g2 * v})
    assert isinstance(closed, DiscreteSystem)
    assert closed.parameters == (g1, g2)

    eigenvalues = closed.linearization({x: 0.0, v: 0.0}, {g1: 1.0, g2: 2.0}).eigenvals()
    assert all(abs(complex(value)) < 1.0 for value in eigenvalues)

    _, states = closed.iterate((1.0, 0.0), 200, substitutions={g1: 1.0, g2: 2.0})
    assert np.allclose(states[-1], [0.0, 0.0], atol=1e-6)

    with pytest.raises(ValueError, match="non-control"):
        system.closed_loop({x: -v})
    with pytest.raises(ValueError, match="cover all controls"):
        system.closed_loop({})
    with pytest.raises(ValueError, match="reintroduce"):
        system.closed_loop({u: u})


def test_disturbance_channels_default_to_zero() -> None:
    x = sp.Symbol("x", real=True)
    u, d = sp.symbols("u d", real=True)
    system = ControlledDiscreteSystem(
        state=(x,),
        controls=(u,),
        update=(x + u + d,),
        disturbances=(d,),
    )

    nominal = system.closed_loop({u: -x / 2})
    assert sp.simplify(nominal.update[0] - x / 2) == 0
    perturbed = system.closed_loop({u: -x / 2}, {d: sp.Rational(1, 4)})
    assert sp.simplify(perturbed.update[0] - x / 2 - sp.Rational(1, 4)) == 0


def test_discrete_rollout_reports_violations_without_clipping() -> None:
    system, _x, _v, _u = _double_integrator()

    def aggressive(_k: int, state: np.ndarray) -> list[float]:
        return [-5.0 * state[0]]

    result = discrete_rollout(system, aggressive, initial_state=(1.0, 0.0), step_count=5)
    assert result.control_violation == pytest.approx(4.0)
    assert result.controls[0, 0] == pytest.approx(-5.0)
    # The unclipped torque is what was applied: v_1 = 0.1 * (-5.0).
    assert result.states[1, 1] == pytest.approx(-0.5)

    def saturated(k: int, state: np.ndarray) -> np.ndarray:
        assert system.control_bounds is not None
        return system.control_bounds.clip(aggressive(k, state))

    clipped = discrete_rollout(system, saturated, initial_state=(1.0, 0.0), step_count=5)
    assert clipped.control_violation == 0.0
    with pytest.raises(ValueError, match="at least 1"):
        discrete_rollout(system, aggressive, initial_state=(1.0, 0.0), step_count=0)


def test_euler_discretization_bridges_continuous_layer() -> None:
    pendulum = build_system(mass=1.0, length=1.0, gravity=9.81, damping=0.1, torque_bound=50.0)
    theta, omega = pendulum.state
    discrete = euler_discretization(pendulum, 0.001)

    assert isinstance(discrete, ControlledDiscreteSystem)
    assert discrete.control_bounds == pendulum.control_bounds
    assert sp.simplify(discrete.update[0] - (theta + 0.001 * omega)) == 0

    def pd_law(_index: float, state: np.ndarray) -> list[float]:
        return [-20.0 * (state[0] - np.pi) - 5.0 * state[1]]

    discrete_result = discrete_rollout(
        discrete, pd_law, initial_state=(np.pi - 0.3, 0.0), step_count=1000
    )
    continuous_result = rollout(
        pendulum, pd_law, initial_state=(np.pi - 0.3, 0.0), t_span=(0.0, 1.0), dt=0.001
    )
    assert np.allclose(discrete_result.states[-1], continuous_result.states[-1], atol=2e-2)

    h = sp.Symbol("h", positive=True)
    symbolic_dt = euler_discretization(pendulum, h)
    assert h in symbolic_dt.parameters

    t = sp.Symbol("t", real=True)
    x = sp.Symbol("x", real=True)
    driven = FirstOrderSystem(state=(x,), rhs=(sp.sin(t),), time=t)
    with pytest.raises(ValueError, match="autonomous"):
        euler_discretization(driven, 0.1)

    plain = euler_discretization(FirstOrderSystem(state=(x,), rhs=(-x,)), 0.1)
    assert isinstance(plain, DiscreteSystem)
    _, states = plain.iterate((1.0,), 10)
    assert states[-1, 0] == pytest.approx(0.9**10)
