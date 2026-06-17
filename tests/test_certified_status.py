"""Tests for the certified-numeric rigor tier and EnclosureStatusSpec (BE-067).

A certified-numeric status is rigor level 2: a sound interval enclosure over a
stated box. It must round-trip, stay locked to rigor="certified-numeric",
record the box / enclosure / soundness assumptions, be rejected if it claims a
proved/certified verdict, have a verdict supported by the recorded enclosure,
and be produced only by the trusted enclosure evaluator.
"""

from __future__ import annotations

import pytest
import sympy as sp

from engine.numerics import Interval
from engine.verification import (
    EnclosureStatusSpec,
    ExpressionSpec,
    ObligationSpec,
    RIGOR_CERTIFIED_NUMERIC,
    VariableSpec,
    VerificationProblem,
    certified_enclosure_status,
    expression_spec,
)


def _obligation(expr: sp.Expr, comparison: str, *, rhs: float = 0.0) -> ObligationSpec:
    return ObligationSpec(
        id="ob-1",
        name="one-step margin",
        expression=expression_spec(expr),
        comparison=comparison,
        rhs=rhs,
    )


# -- producer: only emits when the enclosure closes the obligation --------


def test_producer_certifies_holding_obligation() -> None:
    x = sp.Symbol("x", real=True)
    # obligation: x - 5 <= 0, box x in [0, 2] -> enclosure [-5, -3] <= 0 holds
    status = certified_enclosure_status(
        id="enc-1",
        obligation=_obligation(x - 5, "<="),
        box={"x": Interval(0, 2)},
        soundness_assumptions=("exact-rational map",),
    )
    assert status is not None
    assert status.verdict == "certified-holds"
    assert status.rigor == RIGOR_CERTIFIED_NUMERIC
    assert status.external_status == "external-required"
    assert status.enclosure_lower == "-5"
    assert status.enclosure_upper == "-3"
    assert status.box == (("x", "0", "2"),)
    assert status.soundness_assumptions == ("exact-rational map",)


def test_producer_returns_none_when_enclosure_does_not_close() -> None:
    x = sp.Symbol("x", real=True)
    # x <= 0 over box x in [-1, 1] -> enclosure [-1, 1] straddles 0: inconclusive
    status = certified_enclosure_status(
        id="enc-2",
        obligation=_obligation(x, "<="),
        box={"x": Interval(-1, 1)},
    )
    assert status is None


def test_producer_certifies_violation() -> None:
    x = sp.Symbol("x", real=True)
    # x <= 0 over box x in [3, 4] -> enclosure entirely positive: certified-violated
    status = certified_enclosure_status(
        id="enc-3",
        obligation=_obligation(x, "<="),
        box={"x": Interval(3, 4)},
    )
    assert status is not None
    assert status.verdict == "certified-violated"


def test_producer_preserves_exact_rational_endpoints() -> None:
    x, dt = sp.symbols("x dt", real=True)
    # x + dt - 1 >= 0 over x in [1/3, 2/3], dt = 1/4:
    #   x + dt in [7/12, 11/12], so x + dt - 1 in [-5/12, -1/12], entirely < 0.
    # For the >= 0 obligation that whole enclosure violates -> certified-violated,
    # with endpoints kept as exact rationals.
    status = certified_enclosure_status(
        id="enc-4",
        obligation=_obligation(x + dt - 1, ">="),
        box={
            "x": Interval(sp.Rational(1, 3), sp.Rational(2, 3)),
            "dt": Interval(sp.Rational(1, 4), sp.Rational(1, 4)),
        },
    )
    assert status is not None
    assert status.verdict == "certified-violated"
    assert status.enclosure_lower == "-5/12"
    assert status.enclosure_upper == "-1/12"
    assert ("dt", "1/4", "1/4") in status.box


# -- round-trip ----------------------------------------------------------


def test_enclosure_status_round_trips() -> None:
    status = EnclosureStatusSpec(
        id="enc",
        obligation_id="ob-1",
        comparison="<=",
        verdict="certified-holds",
        box=(("q1", "-1", "1"), ("v1", "-1/2", "1/2")),
        enclosure_lower="-5/4",
        enclosure_upper="-1/8",
        soundness_assumptions=("exact zero-order-hold map", "rational params"),
    )
    restored = EnclosureStatusSpec.from_dict(status.to_dict())
    assert restored == status
    assert restored.to_dict() == status.to_dict()


# -- locked rigor / rejection of fabricated claims -----------------------


def test_rigor_is_locked_to_certified_numeric() -> None:
    with pytest.raises(ValueError, match="rigor"):
        EnclosureStatusSpec(
            id="enc",
            obligation_id="ob-1",
            comparison="<=",
            verdict="certified-holds",
            box=(("x", "0", "1"),),
            enclosure_lower="-1",
            enclosure_upper="0",
            rigor="proved",
        )


def test_external_status_is_locked() -> None:
    with pytest.raises(ValueError, match="external"):
        EnclosureStatusSpec(
            id="enc",
            obligation_id="ob-1",
            comparison="<=",
            verdict="certified-holds",
            box=(("x", "0", "1"),),
            enclosure_lower="-1",
            enclosure_upper="0",
            external_status="proved",
        )


def test_verdict_must_be_supported_by_enclosure() -> None:
    # claims certified-holds for <= 0 but the enclosure is positive
    with pytest.raises(ValueError, match="not supported"):
        EnclosureStatusSpec(
            id="enc",
            obligation_id="ob-1",
            comparison="<=",
            verdict="certified-holds",
            box=(("x", "0", "1"),),
            enclosure_lower="2",
            enclosure_upper="3",
        )


def test_inverted_enclosure_rejected() -> None:
    with pytest.raises(ValueError, match="lower endpoint"):
        EnclosureStatusSpec(
            id="enc",
            obligation_id="ob-1",
            comparison="<=",
            verdict="certified-holds",
            box=(("x", "0", "1"),),
            enclosure_lower="0",
            enclosure_upper="-1",
        )


# -- integration with VerificationProblem --------------------------------


def _problem_with_enclosure(status: EnclosureStatusSpec) -> VerificationProblem:
    x = sp.Symbol("x", real=True)
    obligation = ObligationSpec(
        id="ob-1",
        name="margin",
        expression=expression_spec(x - 5),
        comparison="<=",
    )
    return VerificationProblem(
        id="p",
        name="problem",
        source="test",
        variables=(VariableSpec(name="x", latex="x"),),
        parameters=(),
        regions=(),
        obligations=(obligation,),
        enclosure_statuses=(status,),
    )


def test_problem_serializes_and_round_trips_enclosure_status() -> None:
    status = certified_enclosure_status(
        id="enc-1",
        obligation=ObligationSpec(
            id="ob-1", name="m", expression=expression_spec(sp.Symbol("x", real=True) - 5), comparison="<="
        ),
        box={"x": Interval(0, 2)},
    )
    assert status is not None
    problem = _problem_with_enclosure(status)
    payload = problem.to_dict()
    assert payload["enclosureStatuses"][0]["verdict"] == "certified-holds"
    assert payload["enclosureStatuses"][0]["rigor"] == RIGOR_CERTIFIED_NUMERIC
    restored = VerificationProblem.from_dict(payload)
    assert restored.to_dict() == payload


def test_problem_rejects_enclosure_status_for_unknown_obligation() -> None:
    bad = EnclosureStatusSpec(
        id="enc",
        obligation_id="does-not-exist",
        comparison="<=",
        verdict="certified-holds",
        box=(("x", "0", "1"),),
        enclosure_lower="-1",
        enclosure_upper="0",
    )
    with pytest.raises(ValueError, match="unknown enclosure status obligation id"):
        _problem_with_enclosure(bad)


def test_problem_without_enclosure_statuses_has_no_certified_claim() -> None:
    import json

    x = sp.Symbol("x", real=True)
    problem = VerificationProblem(
        id="p",
        name="problem",
        source="test",
        variables=(VariableSpec(name="x", latex="x"),),
        parameters=(),
        regions=(),
        obligations=(
            ObligationSpec(id="ob-1", name="m", expression=expression_spec(x - 5), comparison="<="),
        ),
    )
    assert problem.to_dict()["enclosureStatuses"] == []
    assert "certified" not in json.dumps(problem.to_dict())
