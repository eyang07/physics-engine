from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

from engine.export import (
    COMPONENT_ADAPTER_STUBS,
    COMPONENT_INSPECTION,
    COMPONENT_IR,
    COMPONENT_TRAJECTORY,
    PACKAGE_INDEX_FILENAME,
    PACKAGE_INDEX_SCHEMA_VERSION,
    PACKAGE_MANIFEST_FILENAME,
    PACKAGE_SCHEMA_VERSION,
    PackageComponent,
    PackageIndex,
    PackageManifest,
    build_package_index,
    read_package,
    read_package_index,
    write_package,
)
from engine.verification import obligation_adapter_stubs, write_inspection_artifacts
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


def test_write_verification_packages_writes_discovery_index(tmp_path) -> None:
    manifests = write_verification_packages(tmp_path)

    # The index lands beside the packages and references every written package.
    assert (tmp_path / PACKAGE_INDEX_FILENAME).is_file()
    index = read_package_index(tmp_path)
    assert index.schema_version == PACKAGE_INDEX_SCHEMA_VERSION
    assert [entry.problem_id for entry in index.entries] == [
        manifest.problem_id for manifest in manifests
    ]
    # Each entry summarizes its package and points at the on-disk manifest.
    for manifest, entry in zip(manifests, index.entries, strict=True):
        assert entry.model == manifest.model
        assert entry.status == manifest.status
        assert entry.manifest_path == f"{manifest.problem_id}/{PACKAGE_MANIFEST_FILENAME}"
        assert entry.component_kinds == tuple(c.kind for c in manifest.components)
        assert dict(entry.counts) == dict(manifest.counts)
        # The referenced manifest re-reads as a real package.
        package = read_package(tmp_path / entry.problem_id)
        assert package.problem.id == entry.problem_id


def test_package_index_round_trips() -> None:
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
    index = build_package_index([manifest])
    assert PackageIndex.from_dict(index.to_dict()) == index


def test_read_package_index_requires_index_file(tmp_path) -> None:
    (tmp_path / "empty").mkdir()
    with pytest.raises(ValueError, match=f"missing {PACKAGE_INDEX_FILENAME}"):
        read_package_index(tmp_path / "empty")


def test_read_package_index_rejects_missing_manifest(tmp_path) -> None:
    write_verification_packages(tmp_path)
    first_id = verification_package_inputs()[0][0].id
    # Drop one referenced package's manifest; the index must no longer validate.
    (tmp_path / first_id / PACKAGE_MANIFEST_FILENAME).unlink()
    with pytest.raises(ValueError, match="references missing manifest"):
        read_package_index(tmp_path)


def test_package_index_entry_rejects_bad_manifest_path(tmp_path) -> None:
    write_verification_packages(tmp_path)
    index_path = tmp_path / PACKAGE_INDEX_FILENAME
    payload = json.loads(index_path.read_text())
    payload["packages"][0]["manifestPath"] = "wrong/path.json"
    index_path.write_text(json.dumps(payload, indent=2) + "\n")
    with pytest.raises(ValueError, match="manifestPath must be"):
        read_package_index(tmp_path)


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


def test_package_carries_optional_adapter_stubs(tmp_path) -> None:
    problem, trajectory = verification_package_inputs()[0]

    manifest = write_package(
        problem,
        trajectory,
        tmp_path / "pkg",
        include_adapter_stubs=True,
    )
    assert manifest.component(COMPONENT_ADAPTER_STUBS) is not None

    package = read_package(tmp_path / "pkg")
    assert package.adapter_stubs is not None
    assert package.adapter_stubs == obligation_adapter_stubs(problem).to_dict()
    assert package.adapter_stubs["problemId"] == problem.id
    # Every listed stub names a backend category and discharges nothing.
    assert package.adapter_stubs["stubs"]
    for stub in package.adapter_stubs["stubs"]:
        assert stub["category"] in {category["category"] for category in package.adapter_stubs["categories"]}
        assert stub["discharges"] is False


def test_package_omits_adapter_stubs_by_default(tmp_path) -> None:
    problem, trajectory = verification_package_inputs()[0]
    write_package(problem, trajectory, tmp_path / "pkg")

    package = read_package(tmp_path / "pkg")
    assert package.adapter_stubs is None
    assert package.manifest.component(COMPONENT_ADAPTER_STUBS) is None
    assert not (tmp_path / "pkg" / "adapter-stubs.json").exists()


def test_read_package_rejects_adapter_stub_id_mismatch(tmp_path) -> None:
    problem, trajectory = verification_package_inputs()[0]
    write_package(problem, trajectory, tmp_path / "pkg", include_adapter_stubs=True)
    stub_path = tmp_path / "pkg" / "adapter-stubs.json"
    payload = json.loads(stub_path.read_text())
    payload["problemId"] = "some-other-problem"
    stub_path.write_text(json.dumps(payload, indent=2) + "\n")
    with pytest.raises(ValueError, match="adapter stubs problemId"):
        read_package(tmp_path / "pkg")


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
    # The generated package also carries the BE-044 adapter-stub descriptors.
    assert {component.kind for component in package.manifest.components} == {
        COMPONENT_IR,
        COMPONENT_TRAJECTORY,
        COMPONENT_ADAPTER_STUBS,
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

    # BE-044: the package lists adapter stubs naming a target backend category
    # and the obligation shape it would need — honestly non-discharging.
    assert package.adapter_stubs is not None
    stubs = package.adapter_stubs
    assert {category["category"] for category in stubs["categories"]} == {
        "reachability",
        "sos-certificate-synthesis",
        "deductive-prover",
    }
    stubbed_obligation_ids = {stub["obligationId"] for stub in stubs["stubs"]}
    assert stubbed_obligation_ids == {obligation.id for obligation in problem.obligations}
    for stub in stubs["stubs"]:
        assert stub["target"] == "discrete-barrier"
        assert "region-scoped" in stub["requiredShapeFeatures"]
        assert stub["applicable"] is True
        assert stub["discharges"] is False


def test_generation_publishes_complete_vertical_axis_package(tmp_path) -> None:
    # The vertical altitude axis is a second flagship package (BE-046), mirroring
    # the horizontal BE-043 structure on the asymmetric (q3, v3) regime.
    manifests = write_verification_packages_for_examples(tmp_path)
    vertical = next(m for m in manifests if m.problem_id == "drone-vertical-axis")
    assert vertical.model == "drone-vertical-axis"
    assert vertical.status == "candidate"

    package = read_package(tmp_path / "drone-vertical-axis")
    problem = package.problem

    # The vertical axis is a discrete map with the same Tier-1 barrier structure.
    assert problem.dynamics is not None and problem.dynamics.kind == "discrete"
    assert {candidate.id for candidate in problem.candidates} == {
        "geofence-barrier",
        "velocity-bound-barrier",
        "inner-set-barrier",
    }
    assert {assumption.id for assumption in problem.assumptions} == {
        "speed-within-half-guard-reach",
        "velocity-within-self-reproducing-bound",
        "timestep-small-vs-guard-band",
        "linear-drift-within-inner-interval",
    }
    # It renders on the (q3, v3) altitude plane, covering every region.
    assert {geometry.region_id for geometry in problem.region_geometry} == {
        region.id for region in problem.regions
    }
    assert all(
        geometry.plane_variables == ("q3", "v3")
        for geometry in problem.region_geometry
    )

    # Measured proof statuses per obligation; nothing claims discharge.
    assert {status.obligation_id for status in problem.proof_statuses} == {
        obligation.id for obligation in problem.obligations
    }
    assert {obligation.rigor for obligation in problem.obligations} == {
        "external-required"
    }
    assert {candidate.status for candidate in problem.candidates} == {"candidate"}
    assert {status.rigor for status in problem.proof_statuses} == {"measured"}
    # Every obligation measured-holds within its assumption region (nonnegative
    # signed margin), the honest evidence the vertical guard band stays safe.
    for status in problem.proof_statuses:
        assert status.status == "measured-holds"
        assert status.worst_margin is not None and status.worst_margin >= 0.0

    # The discovery index now catalogs both drone axes alongside the case studies.
    index = read_package_index(tmp_path)
    assert "drone-vertical-axis" in {entry.problem_id for entry in index.entries}


def test_generation_publishes_complete_obstacle_package(tmp_path) -> None:
    # The first Tier-2 problem (BE-048): a circular obstacle keep-out on the
    # coupled (q1, q2) horizontal plane, not a single decoupled axis.
    manifests = write_verification_packages_for_examples(tmp_path)
    obstacle = next(m for m in manifests if m.problem_id == "drone-obstacle-keepout")
    assert obstacle.model == "drone-obstacle-keepout"
    assert obstacle.status == "candidate"

    package = read_package(tmp_path / "drone-obstacle-keepout")
    problem = package.problem

    # The keep-out barrier is a candidate over the coupled position plane; the
    # coasting velocity is a bounded parameter of the one-step kinematics.
    assert problem.dynamics is not None and problem.dynamics.kind == "discrete"
    assert {variable.name for variable in problem.variables} == {"q1", "q2"}
    assert {parameter.name for parameter in problem.parameters} == {"v1", "v2"}
    assert {candidate.id for candidate in problem.candidates} == {
        "obstacle-keepout-barrier"
    }
    assert {assumption.id for assumption in problem.assumptions} == {
        "planar-speed-within-velocity-bound",
        "drone-maintains-obstacle-standoff",
        "operating-region-within-guard-band-interior",
        "standoff-exceeds-worst-case-drift",
    }
    # It renders on the (q1, q2) plane, covering every region.
    assert {geometry.region_id for geometry in problem.region_geometry} == {
        region.id for region in problem.regions
    }
    assert all(
        geometry.plane_variables == ("q1", "q2")
        for geometry in problem.region_geometry
    )

    # The engine proposes; it never disposes.
    assert {obligation.rigor for obligation in problem.obligations} == {
        "external-required"
    }
    assert {candidate.status for candidate in problem.candidates} == {"candidate"}
    assert {status.rigor for status in problem.proof_statuses} == {"measured"}

    # The measured avoidance status holds within the standoff annulus and the
    # geofence interior, with a nonnegative signed margin.
    avoidance = next(
        status
        for status in problem.proof_statuses
        if status.obligation_id == "obstacle-keepout-one-step-avoidance"
    )
    assert avoidance.status == "measured-holds"
    assert avoidance.worst_margin is not None and avoidance.worst_margin >= 0.0
    assert avoidance.sample_count > 0

    index = read_package_index(tmp_path)
    assert "drone-obstacle-keepout" in {entry.problem_id for entry in index.entries}


def test_generation_publishes_complete_disturbance_robust_package(tmp_path) -> None:
    # The first Tier-3 problem (BE-049): a bounded additive disturbance w1 on the
    # horizontal (q1, v1) zero-order-hold step, with a robust forward-invariance
    # obligation quantified over the whole disturbance set.
    manifests = write_verification_packages_for_examples(tmp_path)
    disturbed = next(
        m for m in manifests if m.problem_id == "drone-disturbed-geofence-axis"
    )
    assert disturbed.model == "drone-disturbed-geofence-axis"
    assert disturbed.status == "candidate"

    package = read_package(tmp_path / "drone-disturbed-geofence-axis")
    problem = package.problem

    # The disturbed closed loop is a set-valued map: the disturbance w1 is a
    # bounded parameter of the (q1, v1) discrete dynamics, not an extra state.
    assert problem.dynamics is not None and problem.dynamics.kind == "discrete"
    assert {variable.name for variable in problem.variables} == {"q1", "v1"}
    assert {parameter.name for parameter in problem.parameters} == {"w1"}
    assert {candidate.id for candidate in problem.candidates} == {"geofence-barrier"}
    assert {assumption.id for assumption in problem.assumptions} == {
        "disturbance-within-wind-bound",
        "robust-speed-within-tightened-guard-reach",
        "operating-within-geofence-inner-interval",
        "robust-braking-displacement-fits-guard-band",
    }
    # It renders on the (q1, v1) plane, covering every region.
    assert {geometry.region_id for geometry in problem.region_geometry} == {
        region.id for region in problem.regions
    }
    assert all(
        geometry.plane_variables == ("q1", "v1")
        for geometry in problem.region_geometry
    )

    # The engine proposes; it never disposes.
    assert {obligation.rigor for obligation in problem.obligations} == {
        "external-required"
    }
    assert {candidate.status for candidate in problem.candidates} == {"candidate"}
    assert {status.rigor for status in problem.proof_statuses} == {"measured"}

    # The robust forward-invariance obligation cites the disturbance bound and
    # measures a worst-case-over-W signed margin that holds within its region.
    robust = next(
        obligation
        for obligation in problem.obligations
        if obligation.id == "geofence-barrier-robust-forward-invariance"
    )
    assert "disturbance-within-wind-bound" in robust.assumption_ids
    robust_status = next(
        status
        for status in problem.proof_statuses
        if status.obligation_id == "geofence-barrier-robust-forward-invariance"
    )
    assert robust_status.status == "measured-holds"
    assert robust_status.worst_margin is not None and robust_status.worst_margin >= 0.0
    assert robust_status.sample_count > 0

    index = read_package_index(tmp_path)
    assert "drone-disturbed-geofence-axis" in {
        entry.problem_id for entry in index.entries
    }


def test_generation_publishes_complete_geofence_obstacle_package(tmp_path) -> None:
    # The first intersection-safe-set problem (BE-050): one coupled (q1, q2)
    # package carrying both the geofence box barrier and the obstacle keep-out
    # barrier, so the drone stays inside the geofence AND outside the obstacle.
    manifests = write_verification_packages_for_examples(tmp_path)
    coupled = next(m for m in manifests if m.problem_id == "drone-geofence-obstacle")
    assert coupled.model == "drone-geofence-obstacle"
    assert coupled.status == "candidate"

    package = read_package(tmp_path / "drone-geofence-obstacle")
    problem = package.problem

    # Two candidate barriers over the coupled position plane; the coasting
    # velocity is a bounded parameter of the one-step kinematics.
    assert problem.dynamics is not None and problem.dynamics.kind == "discrete"
    assert {variable.name for variable in problem.variables} == {"q1", "q2"}
    assert {parameter.name for parameter in problem.parameters} == {"v1", "v2"}
    assert {candidate.id for candidate in problem.candidates} == {
        "geofence-box-barrier",
        "obstacle-keepout-barrier",
    }
    # The safe set is the intersection of the two candidate regions.
    safe = next(region for region in problem.regions if region.role == "safe")
    assert safe.name == "geofence-and-keepout"
    # It renders on the (q1, q2) plane, covering every region.
    assert {geometry.region_id for geometry in problem.region_geometry} == {
        region.id for region in problem.regions
    }
    assert all(
        geometry.plane_variables == ("q1", "q2")
        for geometry in problem.region_geometry
    )

    # The engine proposes; it never disposes.
    assert {obligation.rigor for obligation in problem.obligations} == {
        "external-required"
    }
    assert {candidate.status for candidate in problem.candidates} == {"candidate"}
    assert {status.rigor for status in problem.proof_statuses} == {"measured"}

    # Both the geofence and keep-out one-step obligations measure-hold within
    # their assumption regions, with nonnegative signed margins.
    for obligation_id in (
        "geofence-box-one-step-forward-invariance",
        "obstacle-keepout-one-step-avoidance",
    ):
        status = next(
            s for s in problem.proof_statuses if s.obligation_id == obligation_id
        )
        assert status.status == "measured-holds"
        assert status.worst_margin is not None and status.worst_margin >= 0.0
        assert status.sample_count > 0

    index = read_package_index(tmp_path)
    assert "drone-geofence-obstacle" in {entry.problem_id for entry in index.entries}


def test_generation_publishes_complete_vertical_disturbance_robust_package(
    tmp_path,
) -> None:
    # The vertical Tier-3 problem (BE-051): a bounded additive disturbance w3 on
    # the asymmetric (q3, v3) altitude step, with a robust floor/ceiling
    # forward-invariance obligation quantified over the disturbance set.
    manifests = write_verification_packages_for_examples(tmp_path)
    disturbed = next(
        m
        for m in manifests
        if m.problem_id == "drone-disturbed-vertical-geofence-axis"
    )
    assert disturbed.model == "drone-disturbed-vertical-geofence-axis"
    assert disturbed.status == "candidate"

    package = read_package(tmp_path / "drone-disturbed-vertical-geofence-axis")
    problem = package.problem

    # The disturbed altitude closed loop is set-valued: w3 is a bounded parameter
    # of the (q3, v3) discrete dynamics, not an extra state.
    assert problem.dynamics is not None and problem.dynamics.kind == "discrete"
    assert {variable.name for variable in problem.variables} == {"q3", "v3"}
    assert {parameter.name for parameter in problem.parameters} == {"w3"}
    assert {candidate.id for candidate in problem.candidates} == {"geofence-barrier"}
    assert {assumption.id for assumption in problem.assumptions} == {
        "disturbance-within-wind-bound",
        "robust-speed-within-tightened-guard-reach",
        "operating-within-geofence-inner-interval",
        "robust-braking-displacement-fits-guard-band",
    }
    # It renders on the (q3, v3) altitude plane, covering every region.
    assert {geometry.region_id for geometry in problem.region_geometry} == {
        region.id for region in problem.regions
    }
    assert all(
        geometry.plane_variables == ("q3", "v3")
        for geometry in problem.region_geometry
    )

    # The engine proposes; it never disposes.
    assert {obligation.rigor for obligation in problem.obligations} == {
        "external-required"
    }
    assert {candidate.status for candidate in problem.candidates} == {"candidate"}
    assert {status.rigor for status in problem.proof_statuses} == {"measured"}

    # The robust floor/ceiling forward-invariance obligation cites the disturbance
    # bound and measures a worst-case-over-W signed margin that holds.
    robust = next(
        obligation
        for obligation in problem.obligations
        if obligation.id == "geofence-barrier-robust-forward-invariance"
    )
    assert "disturbance-within-wind-bound" in robust.assumption_ids
    robust_status = next(
        status
        for status in problem.proof_statuses
        if status.obligation_id == "geofence-barrier-robust-forward-invariance"
    )
    assert robust_status.status == "measured-holds"
    assert robust_status.worst_margin is not None and robust_status.worst_margin >= 0.0
    assert robust_status.sample_count > 0

    index = read_package_index(tmp_path)
    assert "drone-disturbed-vertical-geofence-axis" in {
        entry.problem_id for entry in index.entries
    }
