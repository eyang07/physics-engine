from __future__ import annotations

import json

import pytest
import sympy as sp

from engine.dynamics import (
    Box,
    ControlledDiscreteSystem,
    DiscreteSystem,
    FirstOrderSystem,
    LyapunovCandidate,
    SublevelSet,
)
from engine.verification import (
    ADAPTER_NAME,
    ARTIFACT_INSPECTION_OUTCOME_JSON,
    ARTIFACT_PROBLEM_JSON,
    ARTIFACT_REPORT_MARKDOWN,
    CandidateSpec,
    InspectionAdapterReport,
    InspectionArtifact,
    REPORT_STATUS,
    VerificationDiagnostic,
    VerificationProblem,
    ObligationSpec,
    ParameterSpec,
    VariableSpec,
    dynamics_spec_from_controlled_discrete,
    dynamics_spec_from_discrete,
    expression_spec,
    inspection_diagnostics,
    render_inspection_markdown,
    verification_problem_from_lyapunov,
    write_inspection_artifacts,
)
from scripts.export_verification_problems import main, upright_pendulum_problem
from scripts.generate_verification_problems import write_verification_problems


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
        ARTIFACT_INSPECTION_OUTCOME_JSON,
    ]

    json_path, markdown_path, outcome_path = (
        artifact.path for artifact in report.artifacts
    )
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload == problem.to_dict()
    assert markdown_path.read_text(encoding="utf-8") == render_inspection_markdown(
        problem
    )
    outcome_payload = json.loads(outcome_path.read_text(encoding="utf-8"))
    assert outcome_payload == report.to_dict()
    assert outcome_payload["diagnostics"][0]["status"] == "not-attempted"
    assert outcome_payload["diagnostics"][1]["code"] == "inspection.capability_check"
    assert outcome_payload["diagnostics"][1]["details"] == {
        "adapter": ADAPTER_NAME,
        "supportsDischarge": False,
        "supportedTargets": [],
        "classifiedTargets": ["continuous-lyapunov"],
    }
    assert {
        diagnostic["status"] for diagnostic in outcome_payload["diagnostics"]
    } == {"not-attempted", "unsupported", "externally-required"}
    assert [
        diagnostic["obligationId"]
        for diagnostic in outcome_payload["diagnostics"]
        if diagnostic["code"] == "inspection.target_unsupported"
    ] == list(report.obligation_ids)
    assert [
        diagnostic["obligationId"]
        for diagnostic in outcome_payload["diagnostics"]
        if diagnostic["status"] == "externally-required"
    ] == list(report.obligation_ids)
    for diagnostic in outcome_payload["diagnostics"]:
        if diagnostic["status"] != "externally-required":
            continue
        assert diagnostic["details"]["classification"]["target"] == "continuous-lyapunov"
        assert diagnostic["details"]["classification"]["requiredCapability"] == (
            "discharge:continuous-lyapunov"
        )
        assert diagnostic["details"]["adapterSupportsTarget"] is False

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


def test_render_inspection_markdown_handles_discrete_dynamics() -> None:
    x = sp.Symbol("x", real=True)
    u = sp.Symbol("u", real=True)
    r = sp.Symbol("r", positive=True)
    system = DiscreteSystem(state=(x,), update=(r * x * (1 - x),), parameters=(r,))
    controlled = ControlledDiscreteSystem(
        state=(x,),
        controls=(u,),
        update=(r * x * (1 - x) + u,),
        parameters=(r,),
        control_bounds=Box(lower=(-1.0,), upper=(1.0,)),
    )
    problem = VerificationProblem(
        id="logistic-map",
        name="logistic map",
        source="test",
        variables=(VariableSpec(name="x", latex="x"),),
        parameters=(ParameterSpec(name="r", latex="r"),),
        regions=(),
        obligations=(
            ObligationSpec(
                id="bounded",
                name="bounded",
                expression=expression_spec(x),
                comparison="<=",
                rhs=1.0,
            ),
        ),
        dynamics=dynamics_spec_from_discrete(system),
        open_loop_dynamics=dynamics_spec_from_controlled_discrete(controlled),
    )

    text = render_inspection_markdown(problem)

    assert "- kind: discrete (step variable `k`)" in text
    assert "- `x_next = r*x*(1 - x)`" in text
    assert "## Open-loop dynamics" in text
    assert "- control `u` in [-1.0, 1.0]" in text


def test_inspection_diagnostics_mark_missing_dynamics_unsupported() -> None:
    x = sp.Symbol("x", real=True)
    problem = VerificationProblem(
        id="obligation-only",
        name="obligation only",
        source="test",
        variables=(VariableSpec(name="x", latex="x"),),
        parameters=(),
        regions=(),
        obligations=(
            ObligationSpec(
                id="nonpositive",
                name="nonpositive",
                expression=expression_spec(x),
                comparison="<=",
                rhs=0.0,
            ),
        ),
    )

    diagnostics = inspection_diagnostics(problem)

    assert [diagnostic.status for diagnostic in diagnostics] == [
        "not-attempted",
        "not-attempted",
        "unsupported",
        "unsupported",
        "externally-required",
    ]
    assert diagnostics[1].code == "inspection.capability_check"
    assert diagnostics[1].details == {
        "adapter": ADAPTER_NAME,
        "supportsDischarge": False,
        "supportedTargets": [],
        "classifiedTargets": ["obligation-only"],
    }
    assert diagnostics[2].code == "inspection.dynamics_missing"
    assert diagnostics[2].severity == "warning"
    assert diagnostics[3].code == "inspection.target_unsupported"
    assert diagnostics[3].details is not None
    assert diagnostics[3].details["classification"]["target"] == "obligation-only"
    assert diagnostics[4].details is not None
    assert diagnostics[4].details["classification"]["target"] == "obligation-only"


def test_inspection_diagnostics_mark_malformed_targets() -> None:
    x = sp.Symbol("x", real=True)
    obligation = ObligationSpec(
        id="candidate-claim",
        name="candidate claim",
        expression=expression_spec(x),
        comparison="<=",
    )
    problem = VerificationProblem(
        id="candidate-without-dynamics",
        name="candidate without dynamics",
        source="test",
        variables=(VariableSpec(name="x", latex="x"),),
        parameters=(),
        regions=(),
        obligations=(obligation,),
        candidates=(
            CandidateSpec(
                id="candidate",
                name="candidate",
                kind="lyapunov",
                expression=expression_spec(x),
                obligation_ids=("candidate-claim",),
                equilibrium=(0.0,),
            ),
        ),
    )

    diagnostics = inspection_diagnostics(problem)

    malformed = [
        diagnostic
        for diagnostic in diagnostics
        if diagnostic.code == "inspection.target_malformed"
    ]
    assert len(malformed) == 1
    assert malformed[0].status == "malformed"
    assert malformed[0].severity == "error"
    assert malformed[0].details is not None
    assert malformed[0].details["classification"]["target"] == (
        "candidate-without-dynamics"
    )
    assert "dynamics model" in malformed[0].message


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
            diagnostics=report.diagnostics,
            status="discharged",
        )
    with pytest.raises(ValueError, match="artifact kind"):
        InspectionArtifact(kind="proof-result", path=tmp_path / "x")
    with pytest.raises(ValueError, match="diagnostic code"):
        VerificationDiagnostic(
            code="Bad Code",
            status="not-attempted",
            message="bad",
        )
    with pytest.raises(ValueError, match="diagnostic status"):
        VerificationDiagnostic(
            code="inspection.bad",
            status="certified",
            message="bad",
        )


def test_export_script_writes_pendulum_artifacts(tmp_path, capsys) -> None:
    problem = upright_pendulum_problem()
    assert problem.id == "upright-pendulum-safety"
    assert problem.system == "pendulum"

    payload = problem.to_dict()
    assert payload["schemaVersion"] == "verification-problem/v3"
    assert payload["system"] == "pendulum"
    assert payload["metadata"]["system"] == "pendulum"
    assert payload["metadata"]["verificationModel"] == "controlled-pendulum-closed-loop"
    assert len(payload["regionGeometry"]) == len(payload["regions"])

    geometry_by_region = {
        geometry["regionId"]: geometry for geometry in payload["regionGeometry"]
    }
    assert set(geometry_by_region) == {region["id"] for region in payload["regions"]}
    safe_geometry = geometry_by_region["safe-corridor"]
    assert safe_geometry["role"] == "safe"
    assert safe_geometry["projection"] == "phase"
    assert safe_geometry["plane"] == {
        "variables": ["theta", "omega"],
        "stateAxes": ["theta", "theta_dot"],
        "variableToStateAxis": {"theta": "theta", "omega": "theta_dot"},
    }
    assert safe_geometry["kind"] == "scalar-field-grid"
    assert safe_geometry["rigor"] == "measured"
    assert safe_geometry["level"] == 0.25
    assert safe_geometry["convention"] == "expression <= level"
    assert len(safe_geometry["grid"]["x"]) == 91
    assert len(safe_geometry["grid"]["y"]) == 91
    assert len(safe_geometry["grid"]["values"]) == 91
    assert len(safe_geometry["grid"]["values"][0]) == 91
    assert safe_geometry["boundaryPolylines"]
    assert all(len(polyline) >= 2 for polyline in safe_geometry["boundaryPolylines"])
    boundary_x_values = [
        point[0]
        for polyline in safe_geometry["boundaryPolylines"]
        for point in polyline
    ]
    assert min(abs(value - (float(sp.pi) - 0.5)) for value in boundary_x_values) < 1e-3
    assert min(abs(value - (float(sp.pi) + 0.5)) for value in boundary_x_values) < 1e-3
    center_index = min(
        range(len(safe_geometry["grid"]["x"])),
        key=lambda index: abs(safe_geometry["grid"]["x"][index] - float(sp.pi)),
    )
    omega_zero_index = min(
        range(len(safe_geometry["grid"]["y"])),
        key=lambda index: abs(safe_geometry["grid"]["y"][index]),
    )
    assert safe_geometry["grid"]["values"][omega_zero_index][center_index] < 0.01

    main(["--output-dir", str(tmp_path)])
    captured = capsys.readouterr()
    assert "wrote" in captured.out
    assert (tmp_path / "upright-pendulum-safety.verification-problem.json").exists()
    assert (tmp_path / "upright-pendulum-safety.inspection.md").exists()
    assert (tmp_path / "upright-pendulum-safety.inspection-outcome.json").exists()


def test_generate_verification_problems_writes_cross_linked_index(tmp_path) -> None:
    generated_dir = tmp_path / "generated"
    viewer_dir = tmp_path / "viewer"

    ids = write_verification_problems(
        generated_dir=generated_dir,
        viewer_dir=viewer_dir,
    )

    assert ids == ["upright-pendulum-safety"]
    payload = json.loads(
        (viewer_dir / "upright-pendulum-safety.json").read_text(encoding="utf-8")
    )
    index = json.loads((viewer_dir / "index.json").read_text(encoding="utf-8"))

    assert payload["system"] == "pendulum"
    assert payload["regionGeometry"]
    assert index["problems"][0]["system"] == "pendulum"
    assert index["problems"][0]["dataPath"] == (
        "/data/verification/upright-pendulum-safety.json"
    )
