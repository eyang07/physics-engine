"""Certified-numeric sqrt keep-out enclosures (BE-072/BE-073)."""

from __future__ import annotations

import itertools
from fractions import Fraction

import pytest
import sympy as sp

from engine.numerics import Interval
from engine.verification import RIGOR_CERTIFIED_NUMERIC, VerificationProblem
from engine.verification.enclosure import enclose_expression
from scripts.export_verification_problems import (
    drone_geofence_obstacle_problem,
    drone_obstacle_keepout_problem,
)


@pytest.fixture(params=[drone_obstacle_keepout_problem, drone_geofence_obstacle_problem])
def keepout_problem(request) -> VerificationProblem:
    return request.param()


def _obligation_name_by_id(problem: VerificationProblem) -> dict[str, str]:
    return {obligation.id: obligation.name for obligation in problem.obligations}


def _nonnegative(value: sp.Expr) -> bool:
    simplified = sp.simplify(value)
    if simplified.is_nonnegative is not None:
        return bool(simplified.is_nonnegative)
    return bool(sp.N(simplified, 80) >= 0)


def _rational(value: Fraction | str | float) -> sp.Rational:
    fraction = Fraction(value)
    return sp.Rational(fraction.numerator, fraction.denominator)


def _constraint_holds(constraint, substitutions: dict[sp.Symbol, sp.Expr]) -> bool:
    value = sp.sympify(constraint.expression.source).subs(substitutions)
    rhs = _rational(constraint.rhs)
    if constraint.comparison == "<=":
        return _nonnegative(rhs - value)
    if constraint.comparison == "<":
        return bool(sp.N(rhs - value, 80) > 0)
    if constraint.comparison == ">=":
        return _nonnegative(value - rhs)
    if constraint.comparison == ">":
        return bool(sp.N(value - rhs, 80) > 0)
    if constraint.comparison == "=":
        return sp.simplify(value - rhs) == 0
    return sp.simplify(value - rhs) != 0


def test_keepout_package_carries_certified_sqrt_avoidance(keepout_problem) -> None:
    names = _obligation_name_by_id(keepout_problem)
    certified = {
        names[status.obligation_id]: status for status in keepout_problem.enclosure_statuses
    }
    assert set(certified) == {"obstacle-keepout:one-step-avoidance"}
    status = certified["obstacle-keepout:one-step-avoidance"]
    assert status.rigor == RIGOR_CERTIFIED_NUMERIC
    assert status.verdict == "certified-holds"
    assert status.external_status == "external-required"
    assert Fraction(status.enclosure_upper) <= 0
    assert tuple(constraint.id for constraint in status.domain_constraints) == (
        "drone-maintains-obstacle-standoff",
    )
    assert "domainConstraints" in status.to_dict()
    assert "sqrt" in status.note
    assert "mpmath" in " ".join(status.soundness_assumptions)


def test_keepout_constrained_refinement_is_tighter_than_unconstrained_box(
    keepout_problem,
) -> None:
    names = _obligation_name_by_id(keepout_problem)
    status = next(
        status
        for status in keepout_problem.enclosure_statuses
        if names[status.obligation_id] == "obstacle-keepout:one-step-avoidance"
    )
    obligation = next(
        obligation
        for obligation in keepout_problem.obligations
        if obligation.id == status.obligation_id
    )
    interval_box = {
        name: Interval(Fraction(lo), Fraction(hi)) for name, lo, hi in status.box
    }
    unconstrained = enclose_expression(obligation.expression, interval_box)

    assert unconstrained.upper > 0
    assert Fraction(status.enclosure_upper) < Fraction(
        int(unconstrained.upper.p), int(unconstrained.upper.q)
    )
    assert Fraction(status.enclosure_upper) <= 0


def test_keepout_sqrt_enclosure_contains_sampled_constrained_exact_values(
    keepout_problem,
) -> None:
    names = _obligation_name_by_id(keepout_problem)
    status = next(
        status
        for status in keepout_problem.enclosure_statuses
        if names[status.obligation_id] == "obstacle-keepout:one-step-avoidance"
    )
    obligation = next(
        obligation
        for obligation in keepout_problem.obligations
        if obligation.id == status.obligation_id
    )
    expr = sp.sympify(obligation.expression.source)
    box = {name: (Fraction(lo), Fraction(hi)) for name, lo, hi in status.box}
    lower = _rational(status.enclosure_lower)
    upper = _rational(status.enclosure_upper)

    symbols = sorted((symbol.name for symbol in expr.free_symbols), key=str)
    samples_by_symbol = []
    for name in symbols:
        lo, hi = box[name]
        samples_by_symbol.append(
            tuple(lo + (hi - lo) * Fraction(k, 4) for k in range(5))
        )
    constrained_samples = 0
    for values in itertools.product(*samples_by_symbol):
        substitutions = {
            sp.Symbol(name, real=True): sp.Rational(value.numerator, value.denominator)
            for name, value in zip(symbols, values, strict=True)
        }
        if not all(
            _constraint_holds(constraint, substitutions)
            for constraint in status.domain_constraints
        ):
            continue
        constrained_samples += 1
        value = expr.subs(substitutions)
        assert _nonnegative(value - lower), (status.id, value, lower)
        assert _nonnegative(upper - value), (status.id, value, upper)
    assert constrained_samples > 0


def test_keepout_points_outside_constraint_are_not_certified(keepout_problem) -> None:
    names = _obligation_name_by_id(keepout_problem)
    status = next(
        status
        for status in keepout_problem.enclosure_statuses
        if names[status.obligation_id] == "obstacle-keepout:one-step-avoidance"
    )
    obligation = next(
        obligation
        for obligation in keepout_problem.obligations
        if obligation.id == status.obligation_id
    )
    expr = sp.sympify(obligation.expression.source)
    origin = {
        sp.Symbol("q1", real=True): sp.Integer(0),
        sp.Symbol("q2", real=True): sp.Integer(0),
    }
    assert not all(
        _constraint_holds(constraint, origin)
        for constraint in status.domain_constraints
    )

    value = expr.subs(origin)
    upper = _rational(status.enclosure_upper)
    assert _nonnegative(value)
    assert not _nonnegative(upper - value)
