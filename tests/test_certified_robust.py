"""Certified-numeric Tier-3 disturbance enclosures (BE-071)."""

from __future__ import annotations

import itertools
from fractions import Fraction

import pytest
import sympy as sp

from engine.verification import RIGOR_CERTIFIED_NUMERIC, VerificationProblem
from scripts.export_verification_problems import (
    drone_disturbed_geofence_problem,
    drone_vertical_disturbed_geofence_problem,
)


@pytest.fixture(
    params=[drone_disturbed_geofence_problem, drone_vertical_disturbed_geofence_problem]
)
def disturbed_axis_problem(request) -> VerificationProblem:
    return request.param()


def _names_by_id(problem: VerificationProblem) -> dict[str, str]:
    return {obligation.id: obligation.name for obligation in problem.obligations}


def _candidate_expression(problem: VerificationProblem, candidate_id: str) -> sp.Expr:
    candidate = next(
        candidate for candidate in problem.candidates if candidate.id == candidate_id
    )
    return sp.sympify(candidate.expression.source)


def test_disturbed_axis_carries_certified_robust_statuses(
    disturbed_axis_problem,
) -> None:
    names = _names_by_id(disturbed_axis_problem)
    certified = {
        names[status.obligation_id]: status
        for status in disturbed_axis_problem.enclosure_statuses
    }
    assert set(certified) == {
        "geofence-barrier:robust-forward-invariance",
        "robust-velocity-bound:one-step-invariance",
    }
    for status in certified.values():
        assert status.rigor == RIGOR_CERTIFIED_NUMERIC
        assert status.verdict == "certified-holds"
        assert status.external_status == "external-required"
        assert Fraction(status.enclosure_upper) <= 0
        assert any(name.startswith("w") for name, *_ in status.box)
        assert "disturbance" in status.note


def test_disturbed_axis_enclosures_contain_sampled_wind_values(
    disturbed_axis_problem,
) -> None:
    """Sample q/v/w and evaluate the actual disturbed Piecewise update."""

    assert disturbed_axis_problem.dynamics is not None
    q_name, v_name = disturbed_axis_problem.dynamics.state
    q = sp.Symbol(q_name, real=True)
    v = sp.Symbol(v_name, real=True)
    q_next = sp.sympify(disturbed_axis_problem.dynamics.rhs[0].source)
    v_next = sp.sympify(disturbed_axis_problem.dynamics.rhs[1].source)
    geofence_expr = _candidate_expression(disturbed_axis_problem, "geofence-barrier")
    velocity_expr = _candidate_expression(
        disturbed_axis_problem, "robust-velocity-bound-barrier"
    )
    actual_by_obligation = {
        "geofence-barrier-robust-forward-invariance": geofence_expr.subs(
            {q: q_next}, simultaneous=True
        ),
        "robust-velocity-bound-one-step-invariance": velocity_expr.subs(
            {v: v_next}, simultaneous=True
        ),
    }

    for status in disturbed_axis_problem.enclosure_statuses:
        expr = actual_by_obligation[status.obligation_id]
        box = {name: (Fraction(lo), Fraction(hi)) for name, lo, hi in status.box}
        lower = Fraction(status.enclosure_lower)
        upper = Fraction(status.enclosure_upper)
        symbols = sorted((symbol.name for symbol in expr.free_symbols), key=str)
        samples_by_symbol = []
        for name in symbols:
            lo, hi = box[name]
            samples_by_symbol.append(
                tuple(lo + (hi - lo) * Fraction(k, 4) for k in range(5))
            )
        for values in itertools.product(*samples_by_symbol):
            substitutions = {
                sp.Symbol(name, real=True): sp.Rational(value.numerator, value.denominator)
                for name, value in zip(symbols, values, strict=True)
            }
            value = Fraction(sp.Rational(expr.subs(substitutions)))
            assert lower <= value <= upper, (status.id, value)
