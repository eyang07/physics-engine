from __future__ import annotations

import json

import pytest
import sympy as sp

from engine.dynamics import FirstOrderSystem, LyapunovCandidate, SublevelSet
from engine.verification import (
    ADAPTER_NAME,
    ARTIFACT_PROBLEM_JSON,
    ARTIFACT_REPORT_MARKDOWN,
    InspectionAdapterReport,
    InspectionArtifact,
    REPORT_STATUS,
    VerificationProblem,
    render_inspection_markdown,
    verification_problem_from_lyapunov,
    write_inspection_artifacts,
)
from scripts.export_verification_problems import main, upright_pendulum_problem


def _oscillator_problem() -> VerificationProblem:
    x, v = sp.symbols("x v", real=True)
    k, c = sp.symbols("k c", positive=True)
    system = FirstOrderSystem(state=(x, v), rhs=(v, -k * x - c * v), parameters=(k, c))
    candidate = LyapunovCandidate(
        state=(x, v),
        function=(k * x**2 + v**2) / 2,
        equilibrium=(0.0, 0.0),
        domain=SublevelSet(state=(x, v), expression=x**2 + v**2, level=4.0, name="ball"),
    )
    return verification_problem_from_lyapunov(
        "damped oscillator lyapunov",
        system,
        candidate,
        substitutions={k: 4.0},
        metadata={"system": "damped-oscillator"},
    )


def test_write_inspection_artifacts_round_trips_problem(tmp_path) -> None:
    problem = _oscillator_problem()
    report = write_inspection_artifacts(problem, tmp_path)

    assert report.adapter == ADAPTER_NAME
    assert report.problem_id == problem.id
    assert report.status == REPORT_STATUS
    assert report.obligation_ids == tuple(
        obligation.id for obligation in problem.obligations
    )
    assert [artifact.kind for artifact in report.artifacts] == [
        ARTIFACT_PROBLEM_JSON,
        ARTIFACT_REPORT_MARKDOWN,
    ]

    json_path, markdown_path = (artifact.path for artifact in report.artifacts)
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload == problem.to_dict()
    assert markdown_path.read_text(encoding="utf-8") == render_inspection_markdown(
        problem
    )

    encoded = json.dumps(report.to_dict())
    assert "external" in encoded
    assert "certified" not in encoded
    assert "proven" not in encoded


def test_render_inspection_markdown_is_deterministic_and_honest() -> None:
    problem = _oscillator_problem()
    text = render_inspection_markdown(problem)

    assert text == render_inspection_markdown(problem)
    assert problem.name in text
    for region in problem.regions:
        assert f"`{region.id}`" in text
    for obligation in problem.obligations:
        assert f"`{obligation.id}`" in text
    assert "awaits external sound discharge" in text
    assert "symbolic (no value bound)" in text
    assert "certified" not in text
    assert "proven" not in text

    assert "## Dynamics" in text
    assert "- `x' = v`" in text
    assert "- inputs: none (closed loop)" in text
    assert "## Assumptions" in text
    assert "`parameter-c-positive`" in text
    assert "`parameter-k-positive`" in text
    assert "## Candidate certificates" in text
    assert "kind: lyapunov" in text
    assert "status: candidate (not accepted by any external sound method)" in text
    assert "- assumptions: `parameter-c-positive`, `parameter-k-positive`" in text


def test_report_rejects_discharge_claims(tmp_path) -> None:
    problem = _oscillator_problem()
    report = write_inspection_artifacts(problem, tmp_path)

    with pytest.raises(ValueError, match="inspection"):
        InspectionAdapterReport(
            adapter=ADAPTER_NAME,
            problem_id=report.problem_id,
            schema_version=report.schema_version,
            obligation_ids=report.obligation_ids,
            artifacts=report.artifacts,
            status="discharged",
        )
    with pytest.raises(ValueError, match="artifact kind"):
        InspectionArtifact(kind="proof-result", path=tmp_path / "x")


def test_export_script_writes_pendulum_artifacts(tmp_path, capsys) -> None:
    problem = upright_pendulum_problem()
    assert problem.id == "upright-pendulum-safety"

    main(["--output-dir", str(tmp_path)])
    captured = capsys.readouterr()
    assert "wrote" in captured.out
    assert (tmp_path / "upright-pendulum-safety.verification-problem.json").exists()
    assert (tmp_path / "upright-pendulum-safety.inspection.md").exists()
