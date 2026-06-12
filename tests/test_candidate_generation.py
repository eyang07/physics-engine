from __future__ import annotations

import pytest
import sympy as sp

from engine.dynamics import (
    FirstOrderSystem,
    MeasuredInfimum,
    SublevelSet,
    barrier_from_lyapunov,
    grid_points,
    measured_infimum_over_set,
    quadratic_lyapunov_from_linearization,
    sample_obligation,
)
from engine.verification import verification_problem_from_lyapunov
from systems.controlled_pendulum import build_system


def _damped_oscillator() -> tuple[FirstOrderSystem, sp.Symbol, sp.Symbol]:
    x, v = sp.symbols("x v", real=True)
    system = FirstOrderSystem(state=(x, v), rhs=(v, -4 * x - sp.Rational(1, 2) * v))
    return system, x, v


def _max_abs_coefficient(expression: sp.Expr) -> float:
    coefficients = sp.expand(expression).as_coefficients_dict()
    return max((abs(float(value)) for value in coefficients.values()), default=0.0)


def test_quadratic_lyapunov_solves_lyapunov_equation() -> None:
    system, x, v = _damped_oscillator()
    candidate = quadratic_lyapunov_from_linearization(system, (0.0, 0.0))

    assert candidate.value_at_equilibrium() == 0
    assert candidate.name == "linearization-lyapunov"
    # For a linear system the construction is exact: dV/dt = -x^T Q x.
    residual = candidate.derivative_along(system) + x**2 + v**2
    assert _max_abs_coefficient(residual) < 1e-9

    points = grid_points(((-1.0, 1.0), (-1.0, 1.0)), (9, 9))
    _, positivity, decrease = candidate.proof_obligations(system)
    assert sample_obligation(positivity, points).satisfied
    assert sample_obligation(decrease, points).satisfied


def test_quadratic_lyapunov_requires_resolved_parameters() -> None:
    x, v = sp.symbols("x v", real=True)
    k, c = sp.symbols("k c", positive=True)
    system = FirstOrderSystem(state=(x, v), rhs=(v, -k * x - c * v), parameters=(k, c))

    candidate = quadratic_lyapunov_from_linearization(
        system, (0.0, 0.0), substitutions={k: 4.0, c: 0.5}
    )
    assert candidate.function.free_symbols == {x, v}

    with pytest.raises(ValueError, match="unresolved"):
        quadratic_lyapunov_from_linearization(system, (0.0, 0.0))


def test_quadratic_lyapunov_rejects_unjustified_constructions() -> None:
    system, x, v = _damped_oscillator()
    with pytest.raises(ValueError, match="equilibrium"):
        quadratic_lyapunov_from_linearization(system, (1.0, 0.0))

    undamped = FirstOrderSystem(state=(x, v), rhs=(v, -4 * x))
    with pytest.raises(ValueError, match="Hurwitz"):
        quadratic_lyapunov_from_linearization(undamped, (0.0, 0.0))


def test_quadratic_lyapunov_validates_q() -> None:
    system, _x, _v = _damped_oscillator()
    with pytest.raises(ValueError, match="square"):
        quadratic_lyapunov_from_linearization(system, (0.0, 0.0), q=[[1.0]])
    with pytest.raises(ValueError, match="symmetric"):
        quadratic_lyapunov_from_linearization(
            system, (0.0, 0.0), q=[[1.0, 0.5], [0.0, 1.0]]
        )
    with pytest.raises(ValueError, match="positive definite"):
        quadratic_lyapunov_from_linearization(
            system, (0.0, 0.0), q=[[1.0, 0.0], [0.0, -1.0]]
        )


def test_barrier_from_lyapunov_builds_sublevel_barrier() -> None:
    system, _x, _v = _damped_oscillator()
    candidate = quadratic_lyapunov_from_linearization(system, (0.0, 0.0))

    barrier = barrier_from_lyapunov(candidate, 1.0)
    assert barrier.name == "linearization-lyapunov:sublevel-barrier"
    assert sp.expand(barrier.function - candidate.function + 1.0) == 0

    non_increase = barrier.proof_obligations(system)[0]
    points = grid_points(((-2.0, 2.0), (-2.0, 2.0)), (9, 9))
    assert sample_obligation(non_increase, points).satisfied

    with pytest.raises(ValueError, match="positive"):
        barrier_from_lyapunov(candidate, 0.0)


def test_measured_infimum_over_set() -> None:
    x, v = sp.symbols("x v", real=True)
    unsafe = SublevelSet(state=(x, v), expression=x, level=-1.0, name="left-wall")

    result = measured_infimum_over_set(
        x**2 + v**2, unsafe, bounds=((-2.0, 2.0), (-2.0, 2.0)), counts=(5, 5)
    )
    assert result.value == pytest.approx(1.0)
    assert result.witness_point == (-1.0, 0.0)
    assert result.rigor == "measured"
    assert result.sample_count == 10
    assert "not a bound" in result.note

    with pytest.raises(ValueError, match="measured"):
        MeasuredInfimum(value=1.0, witness_point=(0.0,), sample_count=1, rigor="proved")
    with pytest.raises(ValueError, match="inside the region"):
        measured_infimum_over_set(
            x**2 + v**2, unsafe, bounds=((0.0, 2.0), (0.0, 2.0)), counts=(5, 5)
        )


def test_pendulum_closed_loop_candidate_exports() -> None:
    pendulum = build_system(mass=1.0, length=1.0, gravity=9.81, damping=0.1)
    theta, omega = pendulum.state
    (u,) = pendulum.controls
    closed = pendulum.closed_loop({u: -20 * (theta - sp.pi) - 5 * omega})

    upright = float(sp.pi)
    candidate = quadratic_lyapunov_from_linearization(
        closed, (upright, 0.0), name="upright-lyapunov"
    )

    decrease = candidate.proof_obligations(closed)[2]
    points = grid_points(
        ((upright - 0.05, upright + 0.05), (-0.05, 0.05)), (8, 8)
    )
    assert sample_obligation(decrease, points).satisfied

    problem = verification_problem_from_lyapunov(
        "upright quadratic lyapunov", closed, candidate
    )
    payload = problem.to_dict()
    assert payload["dynamics"]["state"] == ["theta", "omega"]
    (candidate_payload,) = payload["candidates"]
    assert candidate_payload["kind"] == "lyapunov"
    assert candidate_payload["id"] == "upright-lyapunov"
    assert candidate_payload["equilibrium"] == [upright, 0.0]
