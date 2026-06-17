"""Certified Tier-1 geofence enclosure status (BE-068/BE-070).

The first level-2 claim on a real package: the geofence barrier's
initial-containment obligation (B <= 0 on the inner-start set S_in) is closed by
an exact-rational interval enclosure. BE-069 adds exact-rational coast-core
boxes for the inner-set one-step obligation. BE-070 partitions the guard-band
branches for forward invariance and P2 velocity-bound, so those full rectangular
assumption boxes close at level 2 without claiming proof.
"""

from __future__ import annotations

import itertools
from fractions import Fraction

import pytest
import sympy as sp

from engine.numerics import Interval
from engine.verification import (
    RIGOR_CERTIFIED_NUMERIC,
    VerificationProblem,
    enclose_expression,
)
from scripts.export_verification_problems import (
    drone_geofence_problem,
    drone_vertical_geofence_problem,
)


@pytest.fixture(params=[drone_geofence_problem, drone_vertical_geofence_problem])
def geofence_problem(request) -> VerificationProblem:
    return request.param()


def _obligation_name_by_id(problem: VerificationProblem) -> dict[str, str]:
    return {ob.id: ob.name for ob in problem.obligations}


def test_geofence_carries_certified_initial_containment(geofence_problem) -> None:
    names = _obligation_name_by_id(geofence_problem)
    certified = {
        names[s.obligation_id]: s for s in geofence_problem.enclosure_statuses
    }
    assert "geofence-barrier:initial-containment" in certified
    status = certified["geofence-barrier:initial-containment"]
    assert status.rigor == RIGOR_CERTIFIED_NUMERIC
    assert status.verdict == "certified-holds"
    assert status.external_status == "external-required"
    assert status.soundness_assumptions  # explicit assumptions recorded


def test_geofence_carries_certified_forward_velocity_and_inner_core(
    geofence_problem,
) -> None:
    names = _obligation_name_by_id(geofence_problem)
    certified = {
        names[s.obligation_id]: s for s in geofence_problem.enclosure_statuses
    }
    assert "geofence-barrier:forward-invariance" in certified
    assert "velocity-bound:one-step-invariance" in certified
    assert "inner-set:one-step-invariance" in certified
    for name in (
        "geofence-barrier:forward-invariance",
        "velocity-bound:one-step-invariance",
        "inner-set:one-step-invariance",
    ):
        status = certified[name]
        assert status.rigor == RIGOR_CERTIFIED_NUMERIC
        assert status.verdict == "certified-holds"
        assert status.external_status == "external-required"
        assert status.soundness_assumptions
    assert "guard-partitioned" in certified["geofence-barrier:forward-invariance"].note
    assert "guard-partitioned" in certified["velocity-bound:one-step-invariance"].note
    assert "coast" in certified["inner-set:one-step-invariance"].note


def test_certified_enclosures_satisfy_their_obligations(geofence_problem) -> None:
    # Every emitted certified status is a <= 0 hold whose whole enclosure closes.
    for status in geofence_problem.enclosure_statuses:
        assert status.comparison == "<="
        assert Fraction(status.enclosure_upper) <= Fraction(str(status.rhs))
        assert Fraction(status.enclosure_lower) <= Fraction(status.enclosure_upper)


def test_certified_enclosure_is_sound_against_sampling(geofence_problem) -> None:
    """Independently re-check sampled exact values lie in each enclosure."""

    names = _obligation_name_by_id(geofence_problem)
    obligations = {ob.id: ob for ob in geofence_problem.obligations}
    for status in geofence_problem.enclosure_statuses:
        expr = sp.sympify(obligations[status.obligation_id].expression.source)
        box = {name: (Fraction(lo), Fraction(hi)) for name, lo, hi in status.box}
        lower = Fraction(status.enclosure_lower)
        upper = Fraction(status.enclosure_upper)
        symbols = sorted((symbol.name for symbol in expr.free_symbols), key=str)
        samples_by_symbol = []
        for name in symbols:
            lo, hi = box[name]
            samples_by_symbol.append(
                tuple(lo + (hi - lo) * Fraction(k, 4) for k in range(0, 5))
            )
        for values in itertools.product(*samples_by_symbol):
            substitutions = {
                sp.Symbol(name, real=True): sp.Rational(value.numerator, value.denominator)
                for name, value in zip(symbols, values, strict=True)
            }
            value = Fraction(sp.Rational(expr.subs(substitutions)))
            assert lower <= value <= upper, (names[status.obligation_id], value, status)


def test_partitioned_forward_enclosure_is_tighter_than_free_control_box(
    geofence_problem,
) -> None:
    """The branch partition closes where a monolithic free-control box overinflates."""

    names = _obligation_name_by_id(geofence_problem)
    status = next(
        s
        for s in geofence_problem.enclosure_statuses
        if names[s.obligation_id] == "geofence-barrier:forward-invariance"
    )
    q_name, v_name = (name for name, *_ in status.box)
    q = sp.Symbol(q_name, real=True)
    v = sp.Symbol(v_name, real=True)
    a = sp.Symbol("a", real=True)
    box = {name: Interval(Fraction(lo), Fraction(hi)) for name, lo, hi in status.box}
    q_lo = box[q_name].lower
    q_hi = box[q_name].upper
    dt = sp.Rational(1, 4)
    reach = sp.Integer(1)
    free_control_margin = sp.Max(
        q_lo - (q + dt * v + dt**2 * a / 2),
        (q + dt * v + dt**2 * a / 2) - q_hi,
    )
    loose = enclose_expression(
        free_control_margin,
        {**box, "a": Interval(-reach, reach)},
    )
    assert Fraction(status.enclosure_upper) == 0
    assert Fraction(str(loose.upper)) > 0


def test_measured_statuses_remain_present(geofence_problem) -> None:
    # Certified-numeric statuses do not replace the measured ledger; the sampled
    # evidence remains available and still external-required.
    measured_obligations = {
        s.obligation_id for s in geofence_problem.proof_statuses
    }
    assert {ob.id for ob in geofence_problem.obligations} <= measured_obligations


def test_problem_round_trips_with_enclosure_status(geofence_problem) -> None:
    payload = geofence_problem.to_dict()
    assert payload["enclosureStatuses"]
    restored = VerificationProblem.from_dict(payload)
    assert restored.to_dict() == payload


def test_nothing_reads_as_proof(geofence_problem) -> None:
    import json

    encoded = json.dumps(geofence_problem.to_dict())
    assert '"proved"' not in encoded
    assert '"certified"' not in encoded  # the tag is "certified-numeric", never bare "certified"
    for status in geofence_problem.enclosure_statuses:
        assert status.rigor == RIGOR_CERTIFIED_NUMERIC
