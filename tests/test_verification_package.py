from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

from engine.export import (
    COMPONENT_INSPECTION,
    COMPONENT_IR,
    COMPONENT_TRAJECTORY,
    PACKAGE_MANIFEST_FILENAME,
    PACKAGE_SCHEMA_VERSION,
    PackageComponent,
    PackageManifest,
    read_package,
    write_package,
)
from engine.verification import write_inspection_artifacts
from scripts.export_verification_problems import (
    verification_package_inputs,
    write_verification_packages,
)
from scripts.generate_verification_problems import (
    write_verification_packages_for_examples,
)


def _inputs_by_id() -> dict:
    return {problem.id: (problem, trajectory) for problem, trajectory in verification_package_inputs()}


@pytest.mark.parametrize(
    "problem_id",
    ["upright-pendulum-safety", "controlled-spring-regulator-safety"],
)
def test_write_then_read_round_trips_case_study(tmp_path, problem_id) -> None:
    problem, trajectory = _inputs_by_id()[problem_id]

    manifest = write_package(problem, trajectory, tmp_path / problem_id)
    package = read_package(tmp_path / problem_id)

    # The package reconstructs an equal problem and its trajectory.
    assert package.problem == problem
    assert package.trajectory == trajectory
    assert package.inspection is None

    # The manifest indexes every required component and records honest counts.
    assert manifest.schema_version == PACKAGE_SCHEMA_VERSION
    assert manifest.problem_id == problem.id
    assert {component.kind for component in manifest.components} == {
        COMPONENT_IR,
        COMPONENT_TRAJECTORY,
    }
    assert manifest.counts == {
        "regions": len(problem.regions),
        "obligations": len(problem.obligations),
        "candidates": len(problem.candidates),
    }
    assert package.manifest == manifest

    # Every indexed component file exists on disk.
    for component in manifest.components:
        assert (tmp_path / problem_id / component.path).is_file()


def test_write_verification_packages_covers_every_example(tmp_path) -> None:
    manifests = write_verification_packages(tmp_path)
    assert [manifest.problem_id for manifest in manifests] == [
        problem.id for problem, _ in verification_package_inputs()
    ]
    for manifest in manifests:
        package = read_package(tmp_path / manifest.problem_id)
        assert package.problem.id == manifest.problem_id


def test_package_output_is_deterministic(tmp_path) -> None:
    problem, trajectory = verification_package_inputs()[0]

    write_package(problem, trajectory, tmp_path / "first")
    write_package(problem, trajectory, tmp_path / "second")

    for name in (PACKAGE_MANIFEST_FILENAME, "problem.ir.json", "trajectory.json"):
        assert (tmp_path / "first" / name).read_bytes() == (
            tmp_path / "second" / name
        ).read_bytes()


def test_package_carries_optional_inspection_report(tmp_path) -> None:
    problem, trajectory = verification_package_inputs()[0]
    report = write_inspection_artifacts(problem, tmp_path / "artifacts")

    manifest = write_package(
        problem,
        trajectory,
        tmp_path / "pkg",
        inspection=report.to_dict(),
    )
    assert manifest.component(COMPONENT_INSPECTION) is not None

    package = read_package(tmp_path / "pkg")
    assert package.inspection is not None
    assert package.inspection["adapter"] == report.adapter
    assert package.inspection["problemId"] == problem.id


def test_write_package_requires_verification_model(tmp_path) -> None:
    problem, trajectory = verification_package_inputs()[0]
    without_model = replace(problem, metadata=None)
    with pytest.raises(ValueError, match="verificationModel is required"):
        write_package(without_model, trajectory, tmp_path / "pkg")


def test_read_package_requires_manifest(tmp_path) -> None:
    (tmp_path / "empty").mkdir()
    with pytest.raises(ValueError, match=f"missing {PACKAGE_MANIFEST_FILENAME}"):
        read_package(tmp_path / "empty")


def test_read_package_rejects_missing_component_file(tmp_path) -> None:
    problem, trajectory = verification_package_inputs()[0]
    write_package(problem, trajectory, tmp_path / "pkg")
    (tmp_path / "pkg" / "trajectory.json").unlink()
    with pytest.raises(ValueError, match="missing viewer-trajectory file"):
        read_package(tmp_path / "pkg")


def test_read_package_rejects_count_mismatch(tmp_path) -> None:
    problem, trajectory = verification_package_inputs()[0]
    write_package(problem, trajectory, tmp_path / "pkg")
    manifest_path = tmp_path / "pkg" / PACKAGE_MANIFEST_FILENAME
    payload = json.loads(manifest_path.read_text())
    payload["counts"]["obligations"] += 1
    manifest_path.write_text(json.dumps(payload, indent=2) + "\n")
    with pytest.raises(ValueError, match="counts do not match the IR"):
        read_package(tmp_path / "pkg")


def test_read_package_rejects_id_mismatch(tmp_path) -> None:
    problem, trajectory = verification_package_inputs()[0]
    write_package(problem, trajectory, tmp_path / "pkg")
    manifest_path = tmp_path / "pkg" / PACKAGE_MANIFEST_FILENAME
    payload = json.loads(manifest_path.read_text())
    payload["problemId"] = "some-other-problem"
    manifest_path.write_text(json.dumps(payload, indent=2) + "\n")
    with pytest.raises(ValueError, match="does not match manifest problemId"):
        read_package(tmp_path / "pkg")


def test_manifest_round_trips_and_validates() -> None:
    manifest = PackageManifest(
        problem_id="demo",
        name="Demo",
        model="demo-model",
        status="candidate",
        counts={"regions": 1, "obligations": 2, "candidates": 1},
        components=(
            PackageComponent(kind=COMPONENT_IR, path="problem.ir.json"),
            PackageComponent(kind=COMPONENT_TRAJECTORY, path="trajectory.json"),
        ),
    )
    assert PackageManifest.from_dict(manifest.to_dict()) == manifest


def test_manifest_requires_the_core_components() -> None:
    with pytest.raises(ValueError, match="missing required components"):
        PackageManifest(
            problem_id="demo",
            name="Demo",
            model="demo-model",
            status="candidate",
            counts={"regions": 0, "obligations": 1, "candidates": 0},
            components=(PackageComponent(kind=COMPONENT_IR, path="problem.ir.json"),),
        )


def test_component_rejects_unknown_kind() -> None:
    with pytest.raises(ValueError, match="unknown verification package component kind"):
        PackageComponent(kind="mystery", path="mystery.json")


def test_generation_publishes_complete_drone_package(tmp_path) -> None:
    # The generation entry point bundles the flagship drone end-to-end (BE-043).
    manifests = write_verification_packages_for_examples(tmp_path)
    drone = next(m for m in manifests if m.problem_id == "drone-geofence-axis")
    assert drone.model == "drone-geofence-axis"
    # Nothing in the package claims a discharged result.
    assert drone.status == "candidate"

    package = read_package(tmp_path / "drone-geofence-axis")
    problem = package.problem

    # Every VISION §13 milestone component is present and re-reads in Python.
    assert {component.kind for component in package.manifest.components} == {
        COMPONENT_IR,
        COMPONENT_TRAJECTORY,
    }
    assert problem.dynamics is not None and problem.dynamics.kind == "discrete"
    assert {assumption.id for assumption in problem.assumptions} == {
        "speed-within-half-guard-reach",
        "velocity-within-self-reproducing-bound",
        "timestep-small-vs-guard-band",
        "linear-drift-within-inner-interval",
    }
    assert any(region.role == "safe" for region in problem.regions)
    assert {candidate.id for candidate in problem.candidates} == {
        "geofence-barrier",
        "velocity-bound-barrier",
        "inner-set-barrier",
    }
    # The (q1, v1) visualization covers every region.
    assert {geometry.region_id for geometry in problem.region_geometry} == {
        region.id for region in problem.regions
    }
    assert all(
        geometry.plane_variables == ("q1", "v1")
        for geometry in problem.region_geometry
    )
    # Measured traces: a verdict ledger per obligation and a candidate-value series.
    assert {status.obligation_id for status in problem.proof_statuses} == {
        obligation.id for obligation in problem.obligations
    }
    assert package.trajectory["series"]

    # The engine proposes; it never disposes. Obligations stay external-required,
    # candidates stay candidate, and measured evidence stays measured.
    assert {obligation.rigor for obligation in problem.obligations} == {
        "external-required"
    }
    assert {candidate.status for candidate in problem.candidates} == {"candidate"}
    assert {status.rigor for status in problem.proof_statuses} == {"measured"}
