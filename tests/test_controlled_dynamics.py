from __future__ import annotations

import numpy as np
import pytest
import sympy as sp

from engine.dynamics import (
    Box,
    ControlledFirstOrderSystem,
    FirstOrderSystem,
    rollout,
)
from systems.controlled_pendulum import build_system, energy_expression


def test_closed_loop_reduction_substitutes_the_law() -> None:
    system = build_system()
    theta, omega = system.state
    (u,) = system.controls
    m, l, g, b = system.parameters
    k = sp.Symbol("k", positive=True)

    closed = system.closed_loop({u: -k * theta})

    assert isinstance(closed, FirstOrderSystem)
    assert closed.state == (theta, omega)
    expected = tuple(sp.simplify(expr.subs(u, -k * theta)) for expr in system.rhs)
    assert all(
        sp.simplify(lhs - rhs) == 0 for lhs, rhs in zip(closed.rhs, expected, strict=True)
    )
    # The gain becomes a closed-loop parameter after the original ones.
    assert closed.parameters == (m, l, g, b, k)


def test_closed_loop_law_validation() -> None:
    system = build_system()
    (u,) = system.controls
    stray = sp.Symbol("v", real=True)

    with pytest.raises(ValueError, match="must cover all controls"):
        system.closed_loop({})
    with pytest.raises(ValueError, match="non-control symbols"):
        system.closed_loop({u: 0, stray: 0})
    with pytest.raises(ValueError, match="reintroduce"):
        system.closed_loop({u: u + 1})


def test_control_jacobian_matches_actuation() -> None:
    system = build_system()
    m, l, _g, _b = system.parameters

    control_jacobian = system.control_jacobian()
    assert control_jacobian.shape == (2, 1)
    assert control_jacobian[0, 0] == 0
    assert sp.simplify(control_jacobian[1, 0] - 1 / (m * l**2)) == 0
    assert system.disturbance_jacobian().shape == (2, 0)


def test_unforced_undamped_closed_loop_conserves_energy() -> None:
    system = build_system(damping=0)
    theta, omega = system.state
    (u,) = system.controls
    m, l, g = system.parameters

    closed = system.closed_loop({u: 0})
    energy = energy_expression(theta, omega, mass=m, length=l, gravity=g)
    derivative = sum(
        sp.diff(energy, state) * rhs
        for state, rhs in zip(closed.state, closed.rhs, strict=True)
    )
    assert sp.simplify(derivative) == 0


def test_gravity_compensation_equilibrium_family() -> None:
    system = build_system()
    theta, omega = system.state
    (u,) = system.controls
    m, l, g, _b = system.parameters
    theta_star = sp.Symbol("theta_star", real=True)

    assert system.is_equilibrium(
        {theta: theta_star, omega: 0},
        {u: m * g * l * sp.sin(theta_star)},
    )
    # Without compensation, a tilted rest point is not an equilibrium.
    residual = system.equilibrium_residual(
        {theta: sp.pi / 4, omega: 0}, {u: 0}
    )
    assert residual[1] != 0


def test_pd_law_stabilizes_upright_equilibrium() -> None:
    # Linearization (proven negative real parts at these gains), then a
    # measured rollout toward the upright equilibrium.
    symbolic = build_system()
    theta, omega = symbolic.state
    (u,) = symbolic.controls
    m, l, g, b = symbolic.parameters
    k_p, k_d = sp.symbols("k_p k_d", positive=True)

    closed = symbolic.closed_loop({u: -k_p * (theta - sp.pi) - k_d * omega})
    linearization = closed.linearization(
        {theta: sp.pi, omega: 0},
        {m: 1, l: 1, g: sp.Rational(981, 100), b: sp.Rational(1, 10), k_p: 20, k_d: 5},
    )
    assert all(sp.re(eig.evalf()) < 0 for eig in linearization.eigenvals())

    numeric = build_system(mass=1.0, length=1.0, gravity=9.81, damping=0.1)

    def pd_law(t: float, x: np.ndarray) -> list[float]:
        return [-20.0 * (x[0] - np.pi) - 5.0 * x[1]]

    result = rollout(
        numeric,
        pd_law,
        initial_state=[np.pi - 0.4, 0.0],
        t_span=(0.0, 10.0),
        dt=0.001,
    )
    assert abs(result.states[-1, 0] - np.pi) < 1e-9
    assert abs(result.states[-1, 1]) < 1e-9
    assert result.controls.shape == (len(result.time), 1)
    assert result.control_violation == 0.0  # no bounds declared


def test_rollout_reports_torque_bound_violations_without_clipping() -> None:
    system = build_system(
        mass=1.0, length=1.0, gravity=9.81, damping=0.1, torque_bound=1.0
    )

    def pd_law(t: float, x: np.ndarray) -> list[float]:
        return [-20.0 * (x[0] - np.pi) - 5.0 * x[1]]

    unbounded = rollout(
        system, pd_law, initial_state=[np.pi - 0.4, 0.0], t_span=(0.0, 2.0), dt=0.01
    )
    # Initial demand is kp * 0.4 = 8.0 against a bound of 1.0.
    assert unbounded.control_violation == pytest.approx(7.0, abs=1e-9)
    assert np.max(np.abs(unbounded.controls)) > 1.0  # the law was not clipped

    bounds = system.control_bounds
    assert bounds is not None
    saturated = rollout(
        system,
        lambda t, x: bounds.clip(pd_law(t, x)),
        initial_state=[np.pi - 0.4, 0.0],
        t_span=(0.0, 2.0),
        dt=0.01,
    )
    assert saturated.control_violation == 0.0


def test_rollout_is_deterministic() -> None:
    system = build_system(mass=1.0, length=1.0, gravity=9.81, damping=0.1)

    def law(t: float, x: np.ndarray) -> list[float]:
        return [-2.0 * x[1]]

    first = rollout(system, law, initial_state=[0.5, 0.0], t_span=(0.0, 1.0), dt=0.01)
    second = rollout(system, law, initial_state=[0.5, 0.0], t_span=(0.0, 1.0), dt=0.01)

    assert np.array_equal(first.time, second.time)
    assert np.array_equal(first.states, second.states)
    assert np.array_equal(first.controls, second.controls)


def test_disturbance_channel_and_box_validation() -> None:
    x = sp.Symbol("x", real=True)
    u = sp.Symbol("u", real=True)
    d = sp.Symbol("d", real=True)
    system = ControlledFirstOrderSystem(
        state=(x,),
        controls=(u,),
        disturbances=(d,),
        rhs=(-x + u + d,),
        disturbance_bounds=Box(lower=(-0.1,), upper=(0.1,)),
    )

    result = rollout(
        system,
        lambda t, s: [0.0],
        disturbance=lambda t, s: [0.2],
        initial_state=[1.0],
        t_span=(0.0, 0.5),
        dt=0.1,
    )
    assert result.disturbance_violation == pytest.approx(0.1)
    assert result.disturbances.shape == (len(result.time), 1)

    closed = system.closed_loop({u: -x})  # disturbance defaults to zero
    assert sp.simplify(closed.rhs[0] + 2 * x) == 0

    with pytest.raises(ValueError, match="disjoint"):
        ControlledFirstOrderSystem(state=(x,), controls=(x,), rhs=(x,))
    with pytest.raises(ValueError, match="non-empty"):
        ControlledFirstOrderSystem(state=(x,), controls=(), rhs=(x,))
    with pytest.raises(ValueError, match="lower bounds"):
        Box(lower=(1.0,), upper=(-1.0,))
    with pytest.raises(ValueError, match="dimension"):
        Box(lower=(0.0, 0.0), upper=(1.0, 1.0)).violation([0.5])
