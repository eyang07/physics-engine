from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from engine.electrodynamics import maxwell_source_constraint_diagnostics
from engine.verification import (
    ObligationSpec,
    VerificationProblem,
    em_invariant_obligations,
)
from scripts.generate_relativistic_charged_particle import (
    generate_relativistic_charged_particle,
    generate_relativistic_charged_particle_verification,
    write_relativistic_charged_particle_verification,
)


def test_maxwell_source_constraints_are_measured_diagnostics() -> None:
    diagnostics = maxwell_source_constraint_diagnostics(
        electric=(0.08, -0.03, 0.0),
        magnetic=(0.0, 0.0, 0.9),
    )

    assert [item["name"] for item in diagnostics] == ["divB", "divE"]
    for item in diagnostics:
        assert item["kind"] == "maxwell-source-constraint"
        assert item["rigor"] == "measured"
        assert item["evaluation"] == "measured-finite-difference-grid"
        assert item["residualMaxAbs"] < 1e-12
        assert item["diagnostic"]["rigor"] == "measured"
        assert "proof" in item["note"]


def test_em_invariant_obligations_are_external_required() -> None:
    obligations = em_invariant_obligations(
        {
            "faraday_scalar": 1.607,
            "electric_magnetic": 0.0,
        },
        tolerance=1e-9,
    )

    assert all(isinstance(obligation, ObligationSpec) for obligation in obligations)
    assert [obligation.id for obligation in obligations] == [
        "faraday_scalar-invariant",
        "electric_magnetic-invariant",
    ]
    for obligation in obligations:
        assert obligation.rigor == "external-required"
        assert obligation.comparison == "<="
        assert obligation.rhs == 1e-9


def test_relativistic_charged_particle_exports_maxwell_diagnostics_and_obligations() -> None:
    trajectory = generate_relativistic_charged_particle(dt=0.002)
    metadata = trajectory.metadata

    source_diagnostics = metadata["maxwellSourceDiagnostics"]
    assert [item["name"] for item in source_diagnostics] == ["divB", "divE"]
    assert all(item["rigor"] == "measured" for item in source_diagnostics)
    assert all(item["residualMaxAbs"] < 1e-12 for item in source_diagnostics)

    problems = metadata["verificationProblems"]
    assert len(problems) == 1
    problem = VerificationProblem.from_dict(problems[0])
    assert problem.system == "relativistic_charged_particle"
    assert {obligation.rigor for obligation in problem.obligations} == {
        "external-required"
    }
    assert [obligation.id for obligation in problem.obligations] == [
        "faraday_scalar-invariant",
        "electric_magnetic-invariant",
    ]
    assert len(problem.proof_statuses) == 2
    for status in problem.proof_statuses:
        assert status.status == "measured-holds"
        assert status.rigor == "measured"
        assert status.external_status == "external-required"
        assert status.sample_count == len(trajectory.time)
        assert status.worst_margin is not None and status.worst_margin >= 0.0

    residuals = {record["name"]: record for record in metadata["invariantResiduals"]}
    assert residuals["faraday_scalar"]["rigor"] == "measured"
    assert residuals["electric_magnetic"]["rigor"] == "measured"
    np.testing.assert_allclose(trajectory.series["electric_magnetic"], 0.0)


def test_relativistic_charged_particle_verification_round_trips(tmp_path: Path) -> None:
    output = tmp_path / "relativistic_charged_particle_verification.json"
    viewer_output = tmp_path / "viewer" / "relativistic_charged_particle_verification.json"

    problem = write_relativistic_charged_particle_verification(
        output,
        viewer_output=viewer_output,
    )

    for path in (output, viewer_output):
        payload = json.loads(path.read_text(encoding="utf-8"))
        assert VerificationProblem.from_dict(payload) == problem
        assert all(
            obligation["rigor"] == "external-required"
            for obligation in payload["obligations"]
        )
        assert all(
            status["status"] == "measured-holds"
            for status in payload["proofStatuses"]
        )


def test_em_invariant_obligations_reject_nonpositive_tolerance() -> None:
    with pytest.raises(ValueError):
        em_invariant_obligations({"faraday_scalar": 1.0}, tolerance=0.0)


def test_generate_verification_matches_embedded_problem() -> None:
    trajectory = generate_relativistic_charged_particle()
    embedded = VerificationProblem.from_dict(trajectory.metadata["verificationProblems"][0])

    assert generate_relativistic_charged_particle_verification() == embedded
