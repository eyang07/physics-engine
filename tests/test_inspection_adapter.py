from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

import pytest
import sympy as sp

from metadata_assertions import assert_embedded_certificate_trajectory
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
    AdapterCapabilities,
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
    validate_inspection_artifact_index,
    verification_problem_from_lyapunov,
    write_inspection_artifacts,
)
from scripts.export_verification_problems import (
    DEFAULT_OUTPUT_DIR,
    INSPECTION_ARTIFACT_INDEX_FILENAME,
    INSPECTION_ARTIFACT_INDEX_SCHEMA_VERSION,
    controlled_discrete_decay_problem,
    controlled_spring_problem,
    inspection_artifact_problems,
    main,
    parse_args,
    upright_pendulum_problem,
)
from scripts.generate_verification_problems import write_verification_problems

REPO_ROOT = Path(__file__).resolve().parents[1]


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


def _inspection_artifact_names(problem: VerificationProblem) -> tuple[str, str, str]:
    return (
        f"{problem.id}.verification-problem.json",
        f"{problem.id}.inspection.md",
        f"{problem.id}.inspection-outcome.json",
    )


def _inspection_artifact_path_lines(output_dir, problem: VerificationProblem) -> list[str]:
    problem_name, markdown_name, outcome_name = _inspection_artifact_names(problem)
    return [
        f"wrote {ARTIFACT_PROBLEM_JSON}: {output_dir / problem_name}",
        f"wrote {ARTIFACT_REPORT_MARKDOWN}: {output_dir / markdown_name}",
        f"wrote {ARTIFACT_INSPECTION_OUTCOME_JSON}: {output_dir / outcome_name}",
    ]


def _valid_inspection_artifact_index() -> dict:
    return {
        "schemaVersion": INSPECTION_ARTIFACT_INDEX_SCHEMA_VERSION,
        "problems": [
            {
                "id": "example-problem",
                "name": "example problem",
                "schemaVersion": "verification-problem/v3",
                "artifacts": [
                    {"kind": ARTIFACT_PROBLEM_JSON, "path": "example.json"},
                    {"kind": ARTIFACT_REPORT_MARKDOWN, "path": "example.md"},
                    {
                        "kind": ARTIFACT_INSPECTION_OUTCOME_JSON,
                        "path": "example.outcome.json",
                    },
                ],
            }
        ],
    }


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
        "supportedDynamicsKinds": ["continuous", "discrete"],
        "supportedCandidateKinds": ["lyapunov", "barrier"],
        "supportedObligationShapes": [
            "region-scoped",
            "excluded-points",
            "assumptions",
            "strict-comparison",
            "nonzero-rhs",
        ],
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
        assert "shapeFeatures" in diagnostic["details"]["classification"]
        assert diagnostic["details"]["adapterSupportsTarget"] is False
        assert diagnostic["details"]["capabilityAssessment"]["supported"] is False

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
        "supportedDynamicsKinds": ["continuous", "discrete"],
        "supportedCandidateKinds": ["lyapunov", "barrier"],
        "supportedObligationShapes": [
            "region-scoped",
            "excluded-points",
            "assumptions",
            "strict-comparison",
            "nonzero-rhs",
        ],
        "classifiedTargets": ["obligation-only"],
    }
    assert diagnostics[2].code == "inspection.dynamics_missing"
    assert diagnostics[2].severity == "warning"
    assert diagnostics[3].code == "inspection.target_unsupported"
    assert diagnostics[3].details is not None
    assert diagnostics[3].details["classification"]["target"] == "obligation-only"
    assert diagnostics[4].details is not None
    assert diagnostics[4].details["classification"]["target"] == "obligation-only"


def test_inspection_diagnostics_report_future_adapter_capability_facets() -> None:
    problem = _oscillator_problem()
    limited = AdapterCapabilities(
        adapter="limited-certificate-adapter",
        supported_targets=("continuous-lyapunov",),
        supports_discharge=True,
        supported_dynamics_kinds=("discrete",),
        supported_candidate_kinds=("barrier",),
        supported_obligation_shapes=("region-scoped", "assumptions"),
    )

    diagnostics = inspection_diagnostics(problem, capabilities=limited)

    assert [
        diagnostic.code
        for diagnostic in diagnostics
        if diagnostic.code == "inspection.target_unsupported"
    ] == []
    assert [
        diagnostic.obligation_id
        for diagnostic in diagnostics
        if diagnostic.code == "inspection.dynamics_kind_unsupported"
    ] == [obligation.id for obligation in problem.obligations]
    assert [
        diagnostic.obligation_id
        for diagnostic in diagnostics
        if diagnostic.code == "inspection.candidate_kind_unsupported"
    ] == [obligation.id for obligation in problem.obligations]

    shape_diagnostics = [
        diagnostic
        for diagnostic in diagnostics
        if diagnostic.code == "inspection.obligation_shape_unsupported"
    ]
    assert [diagnostic.obligation_id for diagnostic in shape_diagnostics] == [
        "lyapunov-candidate-positivity"
    ]
    shape_details = shape_diagnostics[0].details
    assert shape_details is not None
    assert shape_details["classification"]["shapeFeatures"] == [
        "region-scoped",
        "excluded-points",
        "assumptions",
        "strict-comparison",
    ]
    assert shape_details["capabilityAssessment"]["unsupportedShapeFeatures"] == [
        "excluded-points",
        "strict-comparison",
    ]
    assert shape_details["capabilityAssessment"]["dynamicsKindSupported"] is False
    assert shape_details["capabilityAssessment"]["candidateKindSupported"] is False


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


def test_export_script_writes_inspection_artifact_contract(tmp_path, capsys) -> None:
    problem = upright_pendulum_problem()
    assert problem.id == "upright-pendulum-safety"
    # Self-contained: the verification world names no gallery system.
    assert problem.system is None

    payload = problem.to_dict()
    assert payload["schemaVersion"] == "verification-problem/v3"
    assert payload["system"] is None
    assert "system" not in payload["metadata"]
    assert payload["metadata"]["verificationModel"] == "controlled-pendulum-closed-loop"
    assert len(payload["regionGeometry"]) == len(payload["regions"])
    assert len(payload["proofStatuses"]) == len(payload["obligations"])

    geometry_by_region = {
        geometry["regionId"]: geometry for geometry in payload["regionGeometry"]
    }
    assert set(geometry_by_region) == {region["id"] for region in payload["regions"]}
    safe_geometry = geometry_by_region["safe-corridor"]
    assert safe_geometry["role"] == "safe"
    assert safe_geometry["projection"] == "phase"
    assert safe_geometry["plane"] == {
        "variables": ["theta", "omega"],
        "stateAxes": ["theta", "omega"],
        "variableToStateAxis": {"theta": "theta", "omega": "omega"},
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
    statuses_by_obligation = {
        status["obligationId"]: status for status in payload["proofStatuses"]
    }
    assert set(statuses_by_obligation) == {
        "energy-barrier-non-increase",
        "energy-barrier-initial-containment",
        "energy-barrier-excludes-near-bottom",
    }
    non_increase_status = statuses_by_obligation["energy-barrier-non-increase"]
    assert non_increase_status["status"] == "measured-holds"
    assert non_increase_status["rigor"] == "measured"
    assert non_increase_status["externalStatus"] == "external-required"
    assert non_increase_status["candidateId"] == "energy-barrier"
    assert non_increase_status["regionId"] == "domain-energy-barrier-region"
    assert non_increase_status["comparison"] == "<="
    assert non_increase_status["evaluation"]["kind"] == "region-grid"
    assert "system" not in non_increase_status["evaluation"]
    assert non_increase_status["evaluation"]["sampleCount"] > 0
    assert non_increase_status["evaluation"]["variableToStateAxis"] == {
        "theta": "theta",
        "omega": "omega",
    }
    assert "worst" in non_increase_status

    main(["--output-dir", str(tmp_path)])
    captured = capsys.readouterr()
    exported_problems = inspection_artifact_problems()
    expected_names = {
        name
        for exported_problem in exported_problems
        for name in _inspection_artifact_names(exported_problem)
    }
    expected_names.add(INSPECTION_ARTIFACT_INDEX_FILENAME)
    assert {path.name for path in tmp_path.iterdir()} == expected_names

    index_path = tmp_path / INSPECTION_ARTIFACT_INDEX_FILENAME
    assert f"wrote inspection artifact index: {index_path}" in captured.out
    index_payload = json.loads(index_path.read_text(encoding="utf-8"))
    validate_inspection_artifact_index(
        index_payload,
        schema_version=INSPECTION_ARTIFACT_INDEX_SCHEMA_VERSION,
    )
    assert index_payload["schemaVersion"] == INSPECTION_ARTIFACT_INDEX_SCHEMA_VERSION
    assert [entry["id"] for entry in index_payload["problems"]] == [
        exported_problem.id for exported_problem in exported_problems
    ]

    for exported_problem, index_entry in zip(
        exported_problems,
        index_payload["problems"],
        strict=True,
    ):
        problem_name, markdown_name, outcome_name = _inspection_artifact_names(
            exported_problem
        )
        problem_path = tmp_path / problem_name
        markdown_path = tmp_path / markdown_name
        outcome_path = tmp_path / outcome_name

        assert f"wrote {ARTIFACT_PROBLEM_JSON}: {problem_path}" in captured.out
        assert f"wrote {ARTIFACT_REPORT_MARKDOWN}: {markdown_path}" in captured.out
        assert (
            f"wrote {ARTIFACT_INSPECTION_OUTCOME_JSON}: {outcome_path}"
            in captured.out
        )
        assert index_entry == {
            "id": exported_problem.id,
            "name": exported_problem.name,
            "schemaVersion": exported_problem.schema_version,
            "artifacts": [
                {"kind": ARTIFACT_PROBLEM_JSON, "path": str(problem_path)},
                {"kind": ARTIFACT_REPORT_MARKDOWN, "path": str(markdown_path)},
                {"kind": ARTIFACT_INSPECTION_OUTCOME_JSON, "path": str(outcome_path)},
            ],
        }

        assert json.loads(problem_path.read_text(encoding="utf-8")) == (
            exported_problem.to_dict()
        )
        assert markdown_path.read_text(encoding="utf-8") == (
            render_inspection_markdown(exported_problem)
        )

        outcome = json.loads(outcome_path.read_text(encoding="utf-8"))
        expected_obligation_ids = [
            obligation.id for obligation in exported_problem.obligations
        ]
        assert outcome["adapter"] == ADAPTER_NAME
        assert outcome["problemId"] == exported_problem.id
        assert outcome["schemaVersion"] == exported_problem.schema_version
        assert outcome["status"] == REPORT_STATUS
        assert outcome["obligationIds"] == expected_obligation_ids
        assert outcome["artifacts"] == [
            {"kind": ARTIFACT_PROBLEM_JSON, "path": str(problem_path)},
            {"kind": ARTIFACT_REPORT_MARKDOWN, "path": str(markdown_path)},
            {"kind": ARTIFACT_INSPECTION_OUTCOME_JSON, "path": str(outcome_path)},
        ]
        assert {
            diagnostic["status"] for diagnostic in outcome["diagnostics"]
        } == {"not-attempted", "unsupported", "externally-required"}
        assert [
            diagnostic["obligationId"]
            for diagnostic in outcome["diagnostics"]
            if diagnostic["code"] == "inspection.target_unsupported"
        ] == expected_obligation_ids
        assert [
            diagnostic["obligationId"]
            for diagnostic in outcome["diagnostics"]
            if diagnostic["status"] == "externally-required"
        ] == expected_obligation_ids
        capability_checks = [
            diagnostic
            for diagnostic in outcome["diagnostics"]
            if diagnostic["code"] == "inspection.capability_check"
        ]
        assert len(capability_checks) == 1
        assert capability_checks[0]["details"]["adapter"] == ADAPTER_NAME
        assert capability_checks[0]["details"]["supportsDischarge"] is False


def test_export_script_default_output_dir_is_ignored_generated_path() -> None:
    args = parse_args([])

    assert args.output_dir == DEFAULT_OUTPUT_DIR
    assert DEFAULT_OUTPUT_DIR.startswith("data/generated/")
    assert "data/generated/" in (REPO_ROOT / ".gitignore").read_text(
        encoding="utf-8"
    )


def test_export_script_cli_writes_custom_output_dir(tmp_path) -> None:
    output_dir = tmp_path / "inspection-artifacts"

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "scripts.export_verification_problems",
            "--output-dir",
            str(output_dir),
        ],
        cwd=REPO_ROOT,
        check=True,
        text=True,
        capture_output=True,
    )

    exported_problems = inspection_artifact_problems()
    expected_path_lines = [
        line
        for problem in exported_problems
        for line in _inspection_artifact_path_lines(output_dir, problem)
    ]
    expected_path_lines.append(
        f"wrote inspection artifact index: "
        f"{output_dir / INSPECTION_ARTIFACT_INDEX_FILENAME}"
    )
    actual_path_lines = [
        line for line in result.stdout.splitlines() if line.startswith("wrote ")
    ]
    assert actual_path_lines == expected_path_lines
    assert str(DEFAULT_OUTPUT_DIR) not in result.stdout
    assert result.stderr == ""

    expected_names = {
        name
        for exported_problem in exported_problems
        for name in _inspection_artifact_names(exported_problem)
    }
    expected_names.add(INSPECTION_ARTIFACT_INDEX_FILENAME)
    assert {path.name for path in output_dir.iterdir()} == expected_names


def test_validate_inspection_artifact_index_accepts_export_shape() -> None:
    payload = _valid_inspection_artifact_index()

    validate_inspection_artifact_index(
        payload,
        schema_version=INSPECTION_ARTIFACT_INDEX_SCHEMA_VERSION,
    )


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        ({}, "schemaVersion"),
        (
            {
                **_valid_inspection_artifact_index(),
                "schemaVersion": "wrong",
            },
            "schemaVersion",
        ),
        (
            {
                **_valid_inspection_artifact_index(),
                "problems": [
                    *_valid_inspection_artifact_index()["problems"],
                    *_valid_inspection_artifact_index()["problems"],
                ],
            },
            "duplicate inspection artifact problem id",
        ),
        (
            {
                **_valid_inspection_artifact_index(),
                "problems": [
                    {
                        **_valid_inspection_artifact_index()["problems"][0],
                        "artifacts": [
                            {
                                **_valid_inspection_artifact_index()["problems"][0][
                                    "artifacts"
                                ][0],
                                "path": "",
                            },
                            *_valid_inspection_artifact_index()["problems"][0][
                                "artifacts"
                            ][1:],
                        ],
                    }
                ],
            },
            "path missing",
        ),
        (
            {
                **_valid_inspection_artifact_index(),
                "problems": [
                    {
                        **_valid_inspection_artifact_index()["problems"][0],
                        "artifacts": [
                            {
                                **_valid_inspection_artifact_index()["problems"][0][
                                    "artifacts"
                                ][0],
                                "kind": "proof-result",
                            },
                            *_valid_inspection_artifact_index()["problems"][0][
                                "artifacts"
                            ][1:],
                        ],
                    }
                ],
            },
            "unknown inspection artifact kind",
        ),
    ],
)
def test_validate_inspection_artifact_index_rejects_invalid_payloads(
    payload,
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        validate_inspection_artifact_index(
            payload,
            schema_version=INSPECTION_ARTIFACT_INDEX_SCHEMA_VERSION,
        )


def test_controlled_discrete_fixture_writes_inspection_diagnostics(tmp_path) -> None:
    problem = controlled_discrete_decay_problem()
    assert problem.id == "controlled-discrete-decay-lyapunov"
    assert problem.dynamics is not None
    assert problem.dynamics.kind == "discrete"
    assert problem.open_loop_dynamics is not None
    assert problem.open_loop_dynamics.kind == "discrete"

    payload = problem.to_dict()
    assert payload["dynamics"]["update"][0]["display"] == "x/2"
    assert payload["openLoopDynamics"]["update"][0]["display"] == "u + x"
    assert payload["openLoopDynamics"]["inputs"] == [
        {"name": "u", "latex": "u", "role": "control", "lower": -1.0, "upper": 1.0}
    ]
    assert payload["metadata"]["verificationModel"] == "controlled-discrete-decay"
    assert payload["metadata"]["feedbackLaw"]["control"]["u"]["display"] == "-x/2"
    assert payload["candidates"][0]["obligationIds"] == [
        obligation["id"] for obligation in payload["obligations"]
    ]

    report = write_inspection_artifacts(problem, tmp_path)
    outcome_path = next(
        artifact.path
        for artifact in report.artifacts
        if artifact.kind == ARTIFACT_INSPECTION_OUTCOME_JSON
    )
    outcome = json.loads(outcome_path.read_text(encoding="utf-8"))
    assert outcome["status"] == REPORT_STATUS
    assert {diagnostic["status"] for diagnostic in outcome["diagnostics"]} == {
        "not-attempted",
        "unsupported",
        "externally-required",
    }
    unsupported = [
        diagnostic
        for diagnostic in outcome["diagnostics"]
        if diagnostic["code"] == "inspection.target_unsupported"
    ]
    assert [diagnostic["obligationId"] for diagnostic in unsupported] == [
        obligation.id for obligation in problem.obligations
    ]
    for diagnostic in unsupported:
        classification = diagnostic["details"]["classification"]
        assessment = diagnostic["details"]["capabilityAssessment"]
        assert classification["target"] == "discrete-lyapunov"
        assert classification["dynamicsKind"] == "discrete"
        assert classification["candidateKind"] == "lyapunov"
        assert assessment["supportsDischarge"] is False
        assert assessment["supported"] is False
        assert "discharged" not in json.dumps(diagnostic).lower()


def test_controlled_spring_problem_exports_viewer_contract() -> None:
    problem = controlled_spring_problem()
    assert problem.id == "controlled-spring-regulator-safety"
    assert problem.system is None

    payload = problem.to_dict()
    assert payload["metadata"]["verificationModel"] == "controlled-spring-regulator"
    assert len(payload["regionGeometry"]) == len(payload["regions"])
    assert len(payload["proofStatuses"]) == len(payload["obligations"])

    geometry_by_region = {
        geometry["regionId"]: geometry for geometry in payload["regionGeometry"]
    }
    assert set(geometry_by_region) == {region["id"] for region in payload["regions"]}
    safe_geometry = geometry_by_region["safe-regulated-energy"]
    assert safe_geometry["projection"] == "phase"
    assert safe_geometry["plane"] == {
        "variables": ["x", "v"],
        "stateAxes": ["x", "v"],
        "variableToStateAxis": {"x": "x", "v": "v"},
    }
    assert len(safe_geometry["grid"]["x"]) == 81
    assert len(safe_geometry["grid"]["y"]) == 81
    assert safe_geometry["boundaryPolylines"]

    statuses_by_obligation = {
        status["obligationId"]: status for status in payload["proofStatuses"]
    }
    assert set(statuses_by_obligation) == {
        "regulated-energy-barrier-non-increase",
        "regulated-energy-barrier-initial-containment",
        "regulated-energy-barrier-excludes-outside-energy-envelope",
    }
    assert {
        status["status"] for status in statuses_by_obligation.values()
    } == {"measured-holds"}
    non_increase_status = statuses_by_obligation[
        "regulated-energy-barrier-non-increase"
    ]
    assert non_increase_status["candidateId"] == "regulated-energy-barrier"
    assert non_increase_status["regionId"] == "domain-regulated-energy-barrier-region"
    assert non_increase_status["evaluation"]["variableToStateAxis"] == {
        "x": "x",
        "v": "v",
    }


def test_generate_verification_problems_writes_self_contained_index(tmp_path) -> None:
    generated_dir = tmp_path / "generated"
    viewer_dir = tmp_path / "viewer"

    ids = write_verification_problems(
        generated_dir=generated_dir,
        viewer_dir=viewer_dir,
    )

    assert ids == [
        "upright-pendulum-safety",
        "controlled-spring-regulator-safety",
    ]
    payload = json.loads(
        (viewer_dir / "upright-pendulum-safety.json").read_text(encoding="utf-8")
    )
    spring_payload = json.loads(
        (viewer_dir / "controlled-spring-regulator-safety.json").read_text(
            encoding="utf-8"
        )
    )
    index = json.loads((viewer_dir / "index.json").read_text(encoding="utf-8"))

    assert payload["system"] is None
    assert payload["regionGeometry"]
    assert payload["proofStatuses"]
    assert {status["status"] for status in payload["proofStatuses"]} <= {
        "measured-holds",
        "measured-violated",
        "external-required",
    }

    # The embedded controlled trajectory the Verification world animates, with
    # candidate-certificate series along the same system the obligations describe.
    trajectory = payload["trajectory"]
    assert_embedded_certificate_trajectory(
        trajectory,
        state_names=("theta", "omega"),
        series_names={
            "certificate_energy_barrier_value",
            "certificate_energy_barrier_flow_derivative",
        },
        certificate_kinds={"candidate-value", "flow-derivative"},
    )
    # Starts near upright (theta = pi) inside the initial set and the controller
    # holds it there, so the path never approaches the unsafe bottom.
    assert abs(trajectory["states"][0][0] - float(sp.pi)) < 0.3
    assert abs(trajectory["states"][-1][0] - float(sp.pi)) < 0.05

    spring_trajectory = spring_payload["trajectory"]
    assert_embedded_certificate_trajectory(
        spring_trajectory,
        state_names=("x", "v"),
        series_names={
            "certificate_regulated_energy_barrier_value",
            "certificate_regulated_energy_barrier_flow_derivative",
        },
        certificate_kinds={"candidate-value", "flow-derivative"},
    )
    assert spring_trajectory["states"][0] == [0.35, -0.1]
    assert abs(spring_trajectory["states"][-1][0]) < 0.01
    assert abs(spring_trajectory["states"][-1][1]) < 0.01

    assert [problem["model"] for problem in index["problems"]] == [
        "controlled-pendulum-closed-loop",
        "controlled-spring-regulator",
    ]
    assert [problem["dataPath"] for problem in index["problems"]] == [
        "/data/verification/upright-pendulum-safety.json",
        "/data/verification/controlled-spring-regulator-safety.json",
    ]
