from __future__ import annotations

import pytest
import sympy as sp

from engine.verification import (
    BACKEND_CATEGORIES,
    BACKEND_CATEGORY_STUBS,
    AdapterStubReport,
    AssumptionSpec,
    BackendCategoryStub,
    CandidateSpec,
    ObligationAdapterStub,
    ObligationSpec,
    ParameterSpec,
    VariableSpec,
    VerificationProblem,
    expression_spec,
    obligation_adapter_stubs,
    robust_obligation_disturbances,
)
from engine.verification.adapter_stubs import ADAPTER_STUB_SCHEMA_VERSION


def _generic_problem() -> VerificationProblem:
    x = sp.Symbol("x", real=True)
    return VerificationProblem(
        id="generic",
        name="generic",
        source="test",
        variables=(VariableSpec(name="x", latex="x"),),
        parameters=(),
        regions=(),
        obligations=(
            ObligationSpec(
                id="claim",
                name="claim",
                expression=expression_spec(x),
                comparison="<=",
            ),
        ),
    )


def _malformed_problem() -> VerificationProblem:
    # A candidate-bearing obligation with no dynamics is malformed: certificate
    # discharge needs the model the candidate was derived from.
    x = sp.Symbol("x", real=True)
    obligation = ObligationSpec(
        id="claim", name="claim", expression=expression_spec(x), comparison="<="
    )
    return VerificationProblem(
        id="malformed",
        name="malformed",
        source="test",
        variables=(VariableSpec(name="x", latex="x"),),
        parameters=(),
        regions=(),
        obligations=(obligation,),
        candidates=(
            CandidateSpec(
                id="cand",
                name="cand",
                kind="lyapunov",
                expression=expression_spec(x),
                obligation_ids=("claim",),
                equilibrium=(0.0,),
            ),
        ),
    )


def _robust_problem() -> VerificationProblem:
    # A Tier-3-shaped problem: a disturbance parameter w, a disturbance-bound
    # assumption quantifying over it, and two obligations -- one robust (cites the
    # disturbance bound) and one nominal (does not).
    q = sp.Symbol("q", real=True)
    w = sp.Symbol("w", real=True)
    disturbance_bound = AssumptionSpec(
        id="disturbance-within-wind-bound",
        name="disturbance within wind bound",
        expression=expression_spec(sp.Abs(w)),
        comparison="<=",
        rhs=0.5,
        variables=("w",),
        role="domain",
    )
    return VerificationProblem(
        id="robust",
        name="robust",
        source="test",
        variables=(VariableSpec(name="q", latex="q"),),
        parameters=(ParameterSpec(name="w", latex="w"),),
        regions=(),
        assumptions=(disturbance_bound,),
        obligations=(
            ObligationSpec(
                id="robust-claim",
                name="robust-claim",
                expression=expression_spec(q),
                comparison="<=",
                assumption_ids=("disturbance-within-wind-bound",),
            ),
            ObligationSpec(
                id="nominal-claim",
                name="nominal-claim",
                expression=expression_spec(q),
                comparison="<=",
            ),
        ),
    )


def test_robust_obligation_disturbances_are_ir_derived() -> None:
    robust = robust_obligation_disturbances(_robust_problem())
    # Only the obligation that cites the disturbance bound (ranging a declared
    # parameter) is robust; it records the disturbance set from IR data alone.
    assert robust == {
        "robust-claim": (("w",), ("disturbance-within-wind-bound",))
    }
    # A problem with no disturbance assumptions has no robust obligations.
    assert robust_obligation_disturbances(_generic_problem()) == {}


def test_robust_obligation_stubs_carry_disturbance_set_without_discharge() -> None:
    report = obligation_adapter_stubs(_robust_problem())

    robust_stubs = [stub for stub in report.stubs if stub.obligation_id == "robust-claim"]
    nominal_stubs = [stub for stub in report.stubs if stub.obligation_id == "nominal-claim"]
    assert robust_stubs and nominal_stubs

    for stub in robust_stubs:
        assert stub.robust is True
        assert stub.disturbance_parameters == ("w",)
        assert stub.disturbance_assumption_ids == ("disturbance-within-wind-bound",)
        # A robust stub records the obligation *shape*, never a discharge.
        assert stub.discharges is False
        payload = stub.to_dict()
        assert payload["robust"] is True
        assert payload["disturbanceParameters"] == ["w"]
        assert payload["disturbanceAssumptionIds"] == ["disturbance-within-wind-bound"]

    # Nominal obligations are unchanged: no robustness flag or disturbance keys.
    for stub in nominal_stubs:
        assert stub.robust is False
        assert stub.disturbance_parameters == ()
        assert "robust" not in stub.to_dict()

    # The extended descriptors survive the round trip.
    assert AdapterStubReport.from_dict(report.to_dict()) == report


def test_obligation_adapter_stub_rejects_inconsistent_disturbance_descriptor() -> None:
    # A robust flag with no disturbance set, and a disturbance set on a nominal
    # stub, are both rejected.
    with pytest.raises(ValueError, match="must name the disturbance parameter"):
        ObligationAdapterStub(
            obligation_id="claim",
            category="reachability",
            target="obligation-only",
            applicable=True,
            required_shape_features=(),
            robust=True,
        )
    with pytest.raises(ValueError, match="must not name a disturbance set"):
        ObligationAdapterStub(
            obligation_id="claim",
            category="reachability",
            target="obligation-only",
            applicable=True,
            required_shape_features=(),
            robust=False,
            disturbance_parameters=("w",),
        )


def test_obligation_adapter_stubs_name_categories_without_discharge() -> None:
    report = obligation_adapter_stubs(_generic_problem())

    assert report.problem_id == "generic"
    assert report.schema_version == ADAPTER_STUB_SCHEMA_VERSION
    assert tuple(category.category for category in report.categories) == BACKEND_CATEGORIES

    # A generic (obligation-only) target is consumed by reachability and the
    # deductive prover, but not by SOS certificate synthesis.
    by_category = {stub.category for stub in report.stubs}
    assert by_category == {"reachability", "deductive-prover"}
    for stub in report.stubs:
        assert stub.obligation_id == "claim"
        assert stub.target == "obligation-only"
        assert stub.applicable is True
        assert stub.discharges is False


def test_adapter_stubs_skip_malformed_obligations() -> None:
    # No backend category can consume an ill-posed obligation.
    report = obligation_adapter_stubs(_malformed_problem())
    assert report.stubs == ()
    # The category catalog is still published so the posture is legible.
    assert tuple(category.category for category in report.categories) == BACKEND_CATEGORIES


def test_adapter_stub_report_round_trips() -> None:
    report = obligation_adapter_stubs(_generic_problem())
    assert AdapterStubReport.from_dict(report.to_dict()) == report


def test_backend_category_catalog_is_internally_consistent() -> None:
    names = [category.category for category in BACKEND_CATEGORY_STUBS]
    assert sorted(names) == sorted(BACKEND_CATEGORIES)
    for category in BACKEND_CATEGORY_STUBS:
        assert category.consumes_targets
        assert "mixed-candidate" not in category.consumes_targets


def test_obligation_adapter_stub_rejects_discharge_claim() -> None:
    with pytest.raises(ValueError, match="never discharge"):
        ObligationAdapterStub(
            obligation_id="claim",
            category="reachability",
            target="obligation-only",
            applicable=True,
            required_shape_features=(),
            discharges=True,
        )


def test_backend_category_stub_rejects_malformed_target() -> None:
    with pytest.raises(ValueError, match="unknown targets"):
        BackendCategoryStub(
            category="reachability",
            summary="s",
            consumes_targets=("mixed-candidate",),
            consumes="c",
            produces="p",
        )
