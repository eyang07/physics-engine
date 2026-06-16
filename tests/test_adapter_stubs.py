from __future__ import annotations

import pytest
import sympy as sp

from engine.verification import (
    BACKEND_CATEGORIES,
    BACKEND_CATEGORY_STUBS,
    AdapterStubReport,
    BackendCategoryStub,
    CandidateSpec,
    ObligationAdapterStub,
    ObligationSpec,
    VariableSpec,
    VerificationProblem,
    expression_spec,
    obligation_adapter_stubs,
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
