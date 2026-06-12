from __future__ import annotations

import numpy as np
import pytest
import sympy as sp

from engine.dynamics import (
    BarrierCandidate,
    FirstOrderSystem,
    LyapunovCandidate,
    ProofObligation,
    SafetySpecification,
    SublevelSet,
    grid_points,
    lie_derivative,
    rollout,
    sample_obligation,
)
from systems.controlled_pendulum import build_system


def _damped_oscillator(damping: float = 0.5) -> FirstOrderSystem:
    x, v = sp.symbols("x v", real=True)
    return FirstOrderSystem(state=(x, v), rhs=(v, -4 * x - damping * v))


def _pendulum_closed_loop():
    pendulum = build_system(mass=1.0, length=1.0, gravity=9.81, damping=0.1)
    theta, omega = pendulum.state
    (u,) = pendulum.controls
    closed = pendulum.closed_loop({u: -20 * (theta - sp.pi) - 5 * omega})
    return pendulum, closed, theta, omega


def test_sublevel_set_margin_signs() -> None:
    x, v = sp.symbols("x v", real=True)
    ball = SublevelSet(state=(x, v), expression=x**2 + v**2, level=1.0, name="ball")

    margins = ball.margin([[0.0, 0.0], [1.0, 0.0], [2.0, 0.0]])
    assert margins[0] == pytest.approx(1.0)
    assert margins[1] == pytest.approx(0.0)
    assert margins[2] == pytest.approx(-3.0)
    assert list(ball.contains([[0.5, 0.5], [2.0, 0.0]])) == [True, False]

    stray = sp.Symbol("a", real=True)
    with pytest.raises(ValueError, match="outside the state"):
        SublevelSet(state=(x, v), expression=x + stray)


def test_lie_derivative_of_oscillator_energy() -> None:
    x, v = sp.symbols("x v", real=True)
    k, c = sp.symbols("k c", positive=True)
    system = FirstOrderSystem(state=(x, v), rhs=(v, -k * x - c * v), parameters=(k, c))
    energy = (k * x**2 + v**2) / 2

    assert sp.simplify(lie_derivative(energy, system) + c * v**2) == 0

    stray = sp.Symbol("z", real=True)
    with pytest.raises(ValueError, match="outside the system"):
        lie_derivative(energy + stray, system)


def test_lyapunov_candidate_obligations_hold_for_damped_oscillator() -> None:
    x, v = sp.symbols("x v", real=True)
    system = _damped_oscillator()
    candidate = LyapunovCandidate(
        state=(x, v),
        function=(4 * x**2 + v**2) / 2,
        equilibrium=(0.0, 0.0),
        domain=SublevelSet(state=(x, v), expression=x**2 + v**2, level=4.0, name="ball"),
    )

    assert candidate.value_at_equilibrium() == 0
    assert sp.simplify(candidate.derivative_along(system) + 0.5 * v**2) == 0

    points = grid_points([(-2.0, 2.0), (-2.0, 2.0)], [21, 21])
    for obligation in candidate.proof_obligations(system):
        sample = sample_obligation(obligation, points)
        assert sample.satisfied, obligation.name
        assert sample.rigor == "measured"
        assert "not a certificate" in sample.note


def test_broken_lyapunov_candidate_yields_counterexample() -> None:
    x, v = sp.symbols("x v", real=True)
    anti_damped = _damped_oscillator(damping=-0.5)
    candidate = LyapunovCandidate(
        state=(x, v),
        function=(4 * x**2 + v**2) / 2,
        equilibrium=(0.0, 0.0),
    )

    decrease = candidate.proof_obligations(anti_damped)[2]
    sample = sample_obligation(decrease, grid_points([(-2.0, 2.0), (-2.0, 2.0)], [21, 21]))

    assert not sample.satisfied
    # dV/dt = +0.5 v^2 is maximal at |v| = 2 on this grid.
    assert sample.worst_value == pytest.approx(2.0)
    assert abs(sample.worst_point[1]) == pytest.approx(2.0)


def test_theta_only_corridor_barrier_fails_non_increase() -> None:
    # Honest negative example: a corridor in theta alone is not invariant
    # for the closed-loop pendulum; dB/dt = 2 omega (theta - pi) > 0 where
    # the state moves outward. The sampler must find the counterexample.
    _pendulum, closed, theta, omega = _pendulum_closed_loop()
    barrier = BarrierCandidate(
        state=(theta, omega), function=(theta - sp.pi) ** 2 - 0.25, name="corridor"
    )

    assert sp.simplify(barrier.derivative_along(closed) - 2 * omega * (theta - sp.pi)) == 0
    non_increase = barrier.proof_obligations(closed)[0]
    sample = sample_obligation(
        non_increase,
        grid_points([(np.pi - 0.6, np.pi + 0.6), (-2.0, 2.0)], [25, 25]),
    )
    assert not sample.satisfied
    assert sample.worst_value > 0.0


def test_energy_barrier_obligations_hold_on_samples() -> None:
    # B = V - 1.2 with V = omega^2/2 + 10 d^2 + 9.81 (cos d - 1), d = theta - pi.
    # Along the PD closed loop dV/dt = -5.1 omega^2 exactly, so {B <= 0} is a
    # candidate invariant region; sampled obligations must all pass.
    _pendulum, closed, theta, omega = _pendulum_closed_loop()
    d = theta - sp.pi
    lyapunov = omega**2 / 2 + 10 * d**2 + sp.Rational(981, 100) * (sp.cos(d) - 1)

    assert sp.simplify(lie_derivative(lyapunov, closed) + sp.Rational(51, 10) * omega**2) == 0

    specification = SafetySpecification(
        state=(theta, omega),
        safe_set=SublevelSet(state=(theta, omega), expression=d**2, level=0.25, name="corridor"),
        unsafe_sets=(
            SublevelSet(state=(theta, omega), expression=theta, level=0.2, name="near-bottom"),
        ),
        initial_set=SublevelSet(
            state=(theta, omega), expression=d**2 + omega**2, level=0.09, name="start-ball"
        ),
    )
    barrier = BarrierCandidate(
        state=(theta, omega), function=lyapunov - sp.Rational(12, 10), name="energy-barrier"
    )

    obligations = barrier.proof_obligations(closed, specification)
    assert [obligation.name for obligation in obligations] == [
        "energy-barrier:non-increase",
        "energy-barrier:initial-containment",
        "energy-barrier:excludes:near-bottom",
    ]
    points = grid_points([(-0.5, 2 * np.pi), (-3.0, 3.0)], [61, 41])
    for obligation in obligations:
        sample = sample_obligation(obligation, points)
        assert sample.satisfied, obligation.name


def test_trajectory_safety_report_for_stabilized_pendulum() -> None:
    pendulum, _closed, theta, omega = _pendulum_closed_loop()
    d = theta - sp.pi
    specification = SafetySpecification(
        state=(theta, omega),
        safe_set=SublevelSet(state=(theta, omega), expression=d**2, level=0.25, name="corridor"),
        unsafe_sets=(
            SublevelSet(state=(theta, omega), expression=theta, level=0.2, name="near-bottom"),
        ),
    )

    def pd_law(t: float, state: np.ndarray) -> list[float]:
        return [-20.0 * (state[0] - np.pi) - 5.0 * state[1]]

    result = rollout(
        pendulum, pd_law, initial_state=[np.pi - 0.3, 0.0], t_span=(0.0, 10.0), dt=0.001
    )
    report = specification.trajectory_report(result.time, result.states)

    assert report.rigor == "measured"
    assert report.stayed_safe
    assert report.min_safe_margin == pytest.approx(0.16, abs=1e-9)
    assert report.min_safe_margin_time == pytest.approx(0.0)
    assert not report.unsafe_sets[0].entered
    assert report.unsafe_sets[0].first_entry_time is None
    assert report.unsafe_sets[0].max_margin < 0.0

    # A corridor tighter than the initial condition is left at t = 0.
    tight = SafetySpecification(
        state=(theta, omega),
        safe_set=SublevelSet(state=(theta, omega), expression=d**2, level=0.04, name="tight"),
        unsafe_sets=(
            SublevelSet(state=(theta, omega), expression=d**2, level=0.04, name="start-zone"),
        ),
    )
    tight_report = tight.trajectory_report(result.time, result.states)
    assert not tight_report.stayed_safe
    assert tight_report.min_safe_margin < 0.0
    assert tight_report.unsafe_sets[0].entered
    assert tight_report.unsafe_sets[0].first_entry_time is not None


def test_grid_points_is_deterministic() -> None:
    first = grid_points([(0.0, 1.0), (-1.0, 1.0)], [3, 5])
    second = grid_points([(0.0, 1.0), (-1.0, 1.0)], [3, 5])

    assert first.shape == (15, 2)
    assert np.array_equal(first, second)
    with pytest.raises(ValueError, match="at least 2"):
        grid_points([(0.0, 1.0)], [1])


def test_validation_errors() -> None:
    x, v = sp.symbols("x v", real=True)
    y = sp.Symbol("y", real=True)
    ball = SublevelSet(state=(x, v), expression=x**2 + v**2, level=1.0)
    other = SublevelSet(state=(x, y), expression=x**2 + y**2, level=1.0)

    with pytest.raises(ValueError, match="share the specification state"):
        SafetySpecification(state=(x, v), safe_set=other)
    with pytest.raises(ValueError, match="comparison"):
        ProofObligation(name="bad", state=(x, v), expression=x, comparison="==")
    with pytest.raises(ValueError, match="excluded_point"):
        ProofObligation(
            name="bad", state=(x, v), expression=x, comparison="<=", excluded_point=(0.0,)
        )
    with pytest.raises(ValueError, match="no sample points"):
        sample_obligation(
            ProofObligation(
                name="empty", state=(x, v), expression=x, comparison="<=", region=ball
            ),
            np.array([[5.0, 5.0]]),
        )
    with pytest.raises(ValueError, match="equilibrium"):
        LyapunovCandidate(state=(x, v), function=x**2, equilibrium=(0.0,))
