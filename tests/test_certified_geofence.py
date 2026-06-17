"""Certified Tier-1 geofence enclosure status (BE-068).

The first level-2 claim on a real package: the geofence barrier's
initial-containment obligation (B <= 0 on the inner-start set S_in) is closed by
an exact-rational interval enclosure. The closed-loop guard-band one-step
obligations (forward invariance / velocity / inner set) stay measured-only here
— their monolithic enclosure does not close them — so nothing reads as proof and
the measured evidence is untouched.
"""

from __future__ import annotations

from fractions import Fraction

import pytest
import sympy as sp

from engine.verification import RIGOR_CERTIFIED_NUMERIC, VerificationProblem
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


def test_certified_enclosure_satisfies_the_obligation(geofence_problem) -> None:
    names = _obligation_name_by_id(geofence_problem)
    status = next(
        s
        for s in geofence_problem.enclosure_statuses
        if names[s.obligation_id] == "geofence-barrier:initial-containment"
    )
    # comparison is <= rhs (0): the whole enclosure must satisfy upper <= rhs.
    assert status.comparison == "<="
    assert Fraction(status.enclosure_upper) <= Fraction(str(status.rhs))
    assert Fraction(status.enclosure_lower) <= Fraction(status.enclosure_upper)


def test_certified_enclosure_is_sound_against_sampling(geofence_problem) -> None:
    """Independently re-check: B at every sampled box point lies in the enclosure."""

    names = _obligation_name_by_id(geofence_problem)
    obligation = next(
        ob
        for ob in geofence_problem.obligations
        if ob.name == "geofence-barrier:initial-containment"
    )
    status = next(
        s
        for s in geofence_problem.enclosure_statuses
        if names[s.obligation_id] == "geofence-barrier:initial-containment"
    )
    expr = sp.sympify(obligation.expression.source)
    box = {name: (Fraction(lo), Fraction(hi)) for name, lo, hi in status.box}
    lower, upper = Fraction(status.enclosure_lower), Fraction(status.enclosure_upper)

    # B depends only on position; sweep it across the box.
    (pos_name,) = [s.name for s in expr.free_symbols]
    lo, hi = box[pos_name]
    for k in range(0, 41):
        q = lo + (hi - lo) * Fraction(k, 40)
        value = Fraction(sp.Rational(expr.subs({sp.Symbol(pos_name, real=True): sp.Rational(q.numerator, q.denominator)})))
        assert lower <= value <= upper


def test_forward_invariance_stays_measured_only(geofence_problem) -> None:
    names = _obligation_name_by_id(geofence_problem)
    certified_obligation_names = {
        names[s.obligation_id] for s in geofence_problem.enclosure_statuses
    }
    # The guard-band closed-loop one-step claims are not certified by a monolithic
    # enclosure; they remain measured-only (an honest "not certified").
    assert "geofence-barrier:forward-invariance" not in certified_obligation_names
    assert "velocity-bound:one-step-invariance" not in certified_obligation_names
    # but they still carry their measured proof statuses, unchanged.
    measured_obligations = {
        s.obligation_id for s in geofence_problem.proof_statuses
    }
    forward = next(
        ob.id
        for ob in geofence_problem.obligations
        if ob.name == "geofence-barrier:forward-invariance"
    )
    assert forward in measured_obligations


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
