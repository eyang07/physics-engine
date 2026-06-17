"""Self-contained verification-package bundle (writer + reader).

A verification package gathers everything one external backend or the viewer
needs for a single verification problem into one deterministic, re-readable
directory: the backend-agnostic IR (dynamics, assumptions, regions/sets,
candidates, obligations, region geometry, measured proof statuses), the viewer
trajectory it animates, and — optionally — the stub inspection report. A
``package.json`` manifest indexes the components.

The package unifies the two existing export paths (the viewer payload and the
backend-only inspection artifacts) behind one bundle. It claims nothing beyond
the rigor of its parts: obligations stay ``external-required``, candidates stay
``candidate``, and measured evidence stays measured. Writing then reading a
package reconstructs an equal problem and trajectory; malformed or incomplete
packages raise clear ``ValueError``s.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

import sympy as sp

from engine.export.verification_contract import (
    validate_viewer_verification_problem_payload,
    validate_viewer_verification_problems,
    validate_viewer_verification_trajectory,
)
from engine.verification import VerificationProblem
from engine.verification.adapter_stubs import (
    AdapterStubReport,
    obligation_adapter_stubs,
    robust_obligation_disturbances,
)

PACKAGE_SCHEMA_VERSION = "verification-package/v1"
PACKAGE_MANIFEST_FILENAME = "package.json"

# A deterministic discovery index written beside the generated packages so
# external tools and the viewer can enumerate every package without walking the
# directory tree. It catalogs only; it claims nothing beyond the rigor of the
# packages it lists.
PACKAGE_INDEX_SCHEMA_VERSION = "verification-packages/v1"
PACKAGE_INDEX_FILENAME = "packages.index.json"

# Component kinds the manifest may index, with their on-disk filenames. The IR
# and the viewer trajectory are required; the inspection report and the
# adapter-stub descriptors are optional.
COMPONENT_IR = "problem-ir"
COMPONENT_TRAJECTORY = "viewer-trajectory"
COMPONENT_INSPECTION = "inspection-report"
COMPONENT_ADAPTER_STUBS = "adapter-stubs"

PACKAGE_COMPONENT_KINDS = (
    COMPONENT_IR,
    COMPONENT_TRAJECTORY,
    COMPONENT_INSPECTION,
    COMPONENT_ADAPTER_STUBS,
)
_REQUIRED_COMPONENT_KINDS = (COMPONENT_IR, COMPONENT_TRAJECTORY)
_COMPONENT_FILENAMES = {
    COMPONENT_IR: "problem.ir.json",
    COMPONENT_TRAJECTORY: "trajectory.json",
    COMPONENT_INSPECTION: "inspection.json",
    COMPONENT_ADAPTER_STUBS: "adapter-stubs.json",
}
_COMPONENT_DESCRIPTIONS = {
    COMPONENT_IR: "Backend-agnostic verification-problem IR (no viewer trajectory).",
    COMPONENT_TRAJECTORY: "Self-contained controlled trajectory and certificate series.",
    COMPONENT_INSPECTION: "Stub inspection-adapter report; no obligation discharged.",
    COMPONENT_ADAPTER_STUBS: (
        "Non-discharging adapter-stub descriptors: how external backend "
        "categories would consume each obligation."
    ),
}
_COUNT_KEYS = ("regions", "obligations", "candidates")

# Regime descriptor: an honest, IR-derived classification of whether a package is
# nominal (Tier-1/2) or disturbance-robust (Tier-3). A disturbance-robust package
# carries a bounded disturbance set the dynamics are set-valued over and at least
# one obligation quantified over it. It claims nothing beyond the rigor of the
# package: a robust obligation is still external-required, not discharged.
REGIME_NOMINAL = "nominal"
REGIME_DISTURBANCE_ROBUST = "disturbance-robust"
PACKAGE_REGIME_KINDS = (REGIME_NOMINAL, REGIME_DISTURBANCE_ROBUST)
# The convention the drone packages use to mark a bounded disturbance/wind set:
# the assumption id carries this marker (e.g. 'disturbance-within-wind-bound',
# 'planar-disturbance-within-wind-bound'). Detecting the regime keys off the IR's
# own assumptions, never off the package id or the model name.
_DISTURBANCE_ASSUMPTION_MARKER = "disturbance"


def _dump_json(payload: Any) -> str:
    """Deterministic JSON text matching the generators' formatting."""

    return json.dumps(payload, indent=2) + "\n"


@dataclass(frozen=True)
class PackageComponent:
    """One file the package manifest indexes."""

    kind: str
    path: str
    description: str = ""

    def __post_init__(self) -> None:
        if self.kind not in PACKAGE_COMPONENT_KINDS:
            raise ValueError(f"unknown verification package component kind: {self.kind!r}")
        if not self.path:
            raise ValueError(f"verification package component {self.kind} path is empty")

    def to_dict(self) -> dict[str, str]:
        return {"kind": self.kind, "path": self.path, "description": self.description}

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "PackageComponent":
        if not isinstance(data, Mapping):
            raise ValueError("verification package component must be a mapping")
        kind = data.get("kind")
        path = data.get("path")
        if not isinstance(kind, str) or not kind:
            raise ValueError("verification package component kind is invalid")
        if not isinstance(path, str) or not path:
            raise ValueError(f"verification package component {kind} path is invalid")
        return cls(kind=kind, path=path, description=data.get("description", ""))


@dataclass(frozen=True)
class PackageRegime:
    """An IR-derived classification of a package's disturbance regime.

    ``kind`` is nominal (Tier-1/2) or disturbance-robust (Tier-3). For a
    disturbance-robust package, ``disturbance_parameters`` are the IR parameters
    the set-valued dynamics range over and ``robust_obligation_ids`` are the
    obligations quantified over that disturbance set. Cataloging only; a robust
    obligation stays external-required, never discharged.
    """

    kind: str
    disturbance_parameters: tuple[str, ...] = ()
    robust_obligation_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.kind not in PACKAGE_REGIME_KINDS:
            raise ValueError(
                f"package regime kind must be one of {list(PACKAGE_REGIME_KINDS)}, "
                f"got {self.kind!r}"
            )
        for label, names in (
            ("disturbance_parameters", self.disturbance_parameters),
            ("robust_obligation_ids", self.robust_obligation_ids),
        ):
            if any(not isinstance(name, str) or not name for name in names):
                raise ValueError(f"package regime {label} must be non-empty strings")
            if len(names) != len(set(names)):
                raise ValueError(f"package regime {label} must be unique")
        if self.kind == REGIME_NOMINAL:
            if self.disturbance_parameters or self.robust_obligation_ids:
                raise ValueError(
                    "nominal package regime must not list disturbance parameters or "
                    "robust obligations"
                )
        else:
            if not self.disturbance_parameters:
                raise ValueError(
                    "disturbance-robust package regime must list its disturbance "
                    "parameter(s)"
                )
            if not self.robust_obligation_ids:
                raise ValueError(
                    "disturbance-robust package regime must list at least one "
                    "obligation quantified over the disturbance"
                )

    @property
    def is_disturbance_robust(self) -> bool:
        return self.kind == REGIME_DISTURBANCE_ROBUST

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {"kind": self.kind}
        if self.disturbance_parameters:
            payload["disturbanceParameters"] = list(self.disturbance_parameters)
        if self.robust_obligation_ids:
            payload["robustObligationIds"] = list(self.robust_obligation_ids)
        return payload

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "PackageRegime":
        if not isinstance(data, Mapping):
            raise ValueError("package regime must be a mapping")
        kind = data.get("kind")
        if not isinstance(kind, str) or not kind:
            raise ValueError("package regime kind is invalid")
        parameters = data.get("disturbanceParameters", [])
        obligations = data.get("robustObligationIds", [])
        if not isinstance(parameters, list) or not isinstance(obligations, list):
            raise ValueError("package regime parameter/obligation lists are invalid")
        return cls(
            kind=kind,
            disturbance_parameters=tuple(parameters),
            robust_obligation_ids=tuple(obligations),
        )


@dataclass(frozen=True)
class PackageManifest:
    """The index of one verification package's contents."""

    problem_id: str
    name: str
    model: str
    status: str
    counts: Mapping[str, int]
    components: tuple[PackageComponent, ...]
    regime: PackageRegime | None = None
    schema_version: str = PACKAGE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != PACKAGE_SCHEMA_VERSION:
            raise ValueError(f"package schema_version must be {PACKAGE_SCHEMA_VERSION!r}")
        for label, value in (
            ("problem_id", self.problem_id),
            ("name", self.name),
            ("model", self.model),
            ("status", self.status),
        ):
            if not isinstance(value, str) or not value:
                raise ValueError(f"package manifest {label} must be a non-empty string")
        if set(self.counts) != set(_COUNT_KEYS):
            raise ValueError(f"package manifest counts must have keys {list(_COUNT_KEYS)}")
        for key in _COUNT_KEYS:
            count = self.counts[key]
            if not isinstance(count, int) or isinstance(count, bool) or count < 0:
                raise ValueError(f"package manifest count {key} must be a nonnegative int")
        if not self.components:
            raise ValueError("package manifest must index at least one component")
        kinds = [component.kind for component in self.components]
        if len(kinds) != len(set(kinds)):
            raise ValueError("package manifest component kinds must be unique")
        missing = set(_REQUIRED_COMPONENT_KINDS) - set(kinds)
        if missing:
            raise ValueError(
                f"package manifest missing required components: {sorted(missing)}"
            )

    def component(self, kind: str) -> PackageComponent | None:
        for component in self.components:
            if component.kind == kind:
                return component
        return None

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schemaVersion": self.schema_version,
            "problemId": self.problem_id,
            "name": self.name,
            "model": self.model,
            "status": self.status,
            "counts": {key: int(self.counts[key]) for key in _COUNT_KEYS},
            "components": [component.to_dict() for component in self.components],
        }
        if self.regime is not None:
            payload["regime"] = self.regime.to_dict()
        return payload

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "PackageManifest":
        if not isinstance(data, Mapping):
            raise ValueError("package manifest payload must be a mapping")
        counts = data.get("counts")
        if not isinstance(counts, Mapping):
            raise ValueError("package manifest counts are invalid")
        components = data.get("components")
        if not isinstance(components, list):
            raise ValueError("package manifest components must be a list")
        regime = data.get("regime")
        return cls(
            problem_id=_require_string(data, "problemId", "package manifest"),
            name=_require_string(data, "name", "package manifest"),
            model=_require_string(data, "model", "package manifest"),
            status=_require_string(data, "status", "package manifest"),
            counts={key: _require_int(counts, key, "package manifest counts") for key in _COUNT_KEYS},
            components=tuple(PackageComponent.from_dict(item) for item in components),
            regime=None if regime is None else PackageRegime.from_dict(regime),
            schema_version=data.get("schemaVersion", PACKAGE_SCHEMA_VERSION),
        )


@dataclass(frozen=True)
class VerificationPackage:
    """A verification package read back from disk."""

    manifest: PackageManifest
    problem: VerificationProblem
    trajectory: Mapping[str, Any]
    inspection: Mapping[str, Any] | None = None
    adapter_stubs: Mapping[str, Any] | None = None


@dataclass(frozen=True)
class DroneFlagshipConsistencyReport:
    """Diagnostic summary for cross-package drone flagship validation.

    The report is cataloging only. It records which packages were compared and
    which IR-derived consistency groups were checked; it does not certify any
    obligation or candidate.
    """

    problem_ids: tuple[str, ...]
    signature_groups: Mapping[str, tuple[str, ...]]


@dataclass(frozen=True)
class PackageIndexEntry:
    """One package's summary in the discovery index."""

    problem_id: str
    name: str
    model: str
    status: str
    manifest_path: str
    component_kinds: tuple[str, ...]
    counts: Mapping[str, int]
    regime: PackageRegime | None = None

    def __post_init__(self) -> None:
        for label, value in (
            ("problem_id", self.problem_id),
            ("name", self.name),
            ("model", self.model),
            ("status", self.status),
            ("manifest_path", self.manifest_path),
        ):
            if not isinstance(value, str) or not value:
                raise ValueError(f"package index entry {label} must be a non-empty string")
        expected_path = f"{self.problem_id}/{PACKAGE_MANIFEST_FILENAME}"
        if self.manifest_path != expected_path:
            raise ValueError(
                f"package index entry manifestPath must be {expected_path!r}, "
                f"got {self.manifest_path!r}"
            )
        if not self.component_kinds:
            raise ValueError("package index entry must list at least one component kind")
        unknown = set(self.component_kinds) - set(PACKAGE_COMPONENT_KINDS)
        if unknown:
            raise ValueError(f"package index entry has unknown component kinds: {sorted(unknown)}")
        if len(self.component_kinds) != len(set(self.component_kinds)):
            raise ValueError("package index entry component kinds must be unique")
        missing = set(_REQUIRED_COMPONENT_KINDS) - set(self.component_kinds)
        if missing:
            raise ValueError(
                f"package index entry missing required component kinds: {sorted(missing)}"
            )
        if set(self.counts) != set(_COUNT_KEYS):
            raise ValueError(f"package index entry counts must have keys {list(_COUNT_KEYS)}")
        for key in _COUNT_KEYS:
            count = self.counts[key]
            if not isinstance(count, int) or isinstance(count, bool) or count < 0:
                raise ValueError(f"package index entry count {key} must be a nonnegative int")

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "problemId": self.problem_id,
            "name": self.name,
            "model": self.model,
            "status": self.status,
            "manifestPath": self.manifest_path,
            "componentKinds": list(self.component_kinds),
            "counts": {key: int(self.counts[key]) for key in _COUNT_KEYS},
        }
        if self.regime is not None:
            payload["regime"] = self.regime.to_dict()
        return payload

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "PackageIndexEntry":
        if not isinstance(data, Mapping):
            raise ValueError("package index entry must be a mapping")
        component_kinds = data.get("componentKinds")
        if not isinstance(component_kinds, list):
            raise ValueError("package index entry componentKinds must be a list")
        counts = data.get("counts")
        if not isinstance(counts, Mapping):
            raise ValueError("package index entry counts are invalid")
        regime = data.get("regime")
        return cls(
            problem_id=_require_string(data, "problemId", "package index entry"),
            name=_require_string(data, "name", "package index entry"),
            model=_require_string(data, "model", "package index entry"),
            status=_require_string(data, "status", "package index entry"),
            manifest_path=_require_string(data, "manifestPath", "package index entry"),
            component_kinds=tuple(component_kinds),
            counts={key: _require_int(counts, key, "package index entry counts") for key in _COUNT_KEYS},
            regime=None if regime is None else PackageRegime.from_dict(regime),
        )


@dataclass(frozen=True)
class PackageIndex:
    """The discovery catalog of every generated verification package."""

    entries: tuple[PackageIndexEntry, ...]
    schema_version: str = PACKAGE_INDEX_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != PACKAGE_INDEX_SCHEMA_VERSION:
            raise ValueError(f"package index schema_version must be {PACKAGE_INDEX_SCHEMA_VERSION!r}")
        ids = [entry.problem_id for entry in self.entries]
        if len(ids) != len(set(ids)):
            raise ValueError("package index entries must have unique problem ids")

    def entry(self, problem_id: str) -> PackageIndexEntry | None:
        for entry in self.entries:
            if entry.problem_id == problem_id:
                return entry
        return None

    def to_dict(self) -> dict[str, Any]:
        return {
            "schemaVersion": self.schema_version,
            "packages": [entry.to_dict() for entry in self.entries],
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "PackageIndex":
        if not isinstance(data, Mapping):
            raise ValueError("package index payload must be a mapping")
        if data.get("schemaVersion") != PACKAGE_INDEX_SCHEMA_VERSION:
            raise ValueError("package index schemaVersion is invalid")
        packages = data.get("packages")
        if not isinstance(packages, list):
            raise ValueError("package index packages must be a list")
        return cls(
            entries=tuple(PackageIndexEntry.from_dict(item) for item in packages),
        )


def build_package_index(manifests: "list[PackageManifest] | tuple[PackageManifest, ...]") -> PackageIndex:
    """Catalog a set of written package manifests into a discovery index."""

    entries = tuple(
        PackageIndexEntry(
            problem_id=manifest.problem_id,
            name=manifest.name,
            model=manifest.model,
            status=manifest.status,
            manifest_path=f"{manifest.problem_id}/{PACKAGE_MANIFEST_FILENAME}",
            component_kinds=tuple(component.kind for component in manifest.components),
            counts=dict(manifest.counts),
            regime=manifest.regime,
        )
        for manifest in manifests
    )
    return PackageIndex(entries=entries)


def write_package_index(
    directory: str | Path,
    manifests: "list[PackageManifest] | tuple[PackageManifest, ...]",
) -> PackageIndex:
    """Write the discovery index beside the generated packages.

    Output is deterministic and regenerable; keep it uncommitted with the rest of
    the generated verification data.
    """

    index = build_package_index(manifests)
    output_dir = Path(directory)
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / PACKAGE_INDEX_FILENAME).write_text(
        _dump_json(index.to_dict()), encoding="utf-8"
    )
    return index


def read_package_index(directory: str | Path) -> PackageIndex:
    """Read and validate the discovery index from ``directory``.

    Re-checks the index shape and that every referenced package manifest exists
    on disk and matches the entry's ``problemId``. Missing files or drift raise
    ``ValueError``.
    """

    package_dir = Path(directory)
    index_path = package_dir / PACKAGE_INDEX_FILENAME
    if not index_path.is_file():
        raise ValueError(f"verification package index missing {PACKAGE_INDEX_FILENAME} in {package_dir}")
    index = PackageIndex.from_dict(_read_json(index_path))
    for entry in index.entries:
        manifest_path = package_dir / entry.manifest_path
        if not manifest_path.is_file():
            raise ValueError(
                f"verification package index references missing manifest {entry.manifest_path}"
            )
        manifest = PackageManifest.from_dict(_read_json(manifest_path))
        if manifest.problem_id != entry.problem_id:
            raise ValueError(
                f"verification package index entry {entry.problem_id!r} references manifest "
                f"with problemId {manifest.problem_id!r}"
            )
        if entry.regime != manifest.regime:
            raise ValueError(
                f"verification package index entry {entry.problem_id!r} regime does not "
                "match its manifest regime"
            )
    return index


def _require_string(data: Mapping[str, Any], key: str, owner: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(f"{owner} {key} is invalid")
    return value


def _require_int(data: Mapping[str, Any], key: str, owner: str) -> int:
    value = data.get(key)
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError(f"{owner} {key} is invalid")
    return value


def _problem_counts(problem: VerificationProblem) -> dict[str, int]:
    return {
        "regions": len(problem.regions),
        "obligations": len(problem.obligations),
        "candidates": len(problem.candidates),
    }


def _problem_regime(problem: VerificationProblem) -> PackageRegime:
    """Classify a problem's disturbance regime from its IR alone.

    A package is disturbance-robust when it carries a bounded disturbance set --
    an assumption marked as a disturbance/wind bound -- whose parameters the
    dynamics range over and that at least one obligation is quantified over.
    Otherwise it is nominal. Derived purely from the IR's assumptions, parameters,
    and obligation citations; it reads neither the model name nor the package id.
    """

    disturbance_assumptions = {
        assumption.id
        for assumption in problem.assumptions
        if _DISTURBANCE_ASSUMPTION_MARKER in assumption.id
    }
    if not disturbance_assumptions:
        return PackageRegime(kind=REGIME_NOMINAL)

    parameter_names = {parameter.name for parameter in problem.parameters}
    disturbance_parameters = tuple(
        dict.fromkeys(
            name
            for assumption in problem.assumptions
            if assumption.id in disturbance_assumptions
            for name in assumption.variables
            if name in parameter_names
        )
    )
    robust_obligation_ids = tuple(
        obligation.id
        for obligation in problem.obligations
        if disturbance_assumptions.intersection(obligation.assumption_ids)
    )
    # A package that merely names a disturbance bound but ranges no parameter over
    # it, or quantifies no obligation over it, is not robust in any honest sense.
    if not disturbance_parameters or not robust_obligation_ids:
        return PackageRegime(kind=REGIME_NOMINAL)
    return PackageRegime(
        kind=REGIME_DISTURBANCE_ROBUST,
        disturbance_parameters=disturbance_parameters,
        robust_obligation_ids=robust_obligation_ids,
    )


def _problem_model_and_status(problem: VerificationProblem) -> tuple[str, str]:
    metadata = problem.metadata or {}
    model = metadata.get("verificationModel")
    if not isinstance(model, str) or not model:
        raise ValueError(
            f"verification problem {problem.id!r} metadata.verificationModel is required "
            "to build a package"
        )
    status = metadata.get("status", "candidate")
    if not isinstance(status, str) or not status:
        raise ValueError(f"verification problem {problem.id!r} metadata.status is invalid")
    return model, status


def build_package_manifest(
    problem: VerificationProblem,
    *,
    include_inspection: bool = False,
    include_adapter_stubs: bool = False,
) -> PackageManifest:
    """Build the manifest indexing a problem's package components."""

    model, status = _problem_model_and_status(problem)
    component_kinds = [COMPONENT_IR, COMPONENT_TRAJECTORY]
    if include_inspection:
        component_kinds.append(COMPONENT_INSPECTION)
    if include_adapter_stubs:
        component_kinds.append(COMPONENT_ADAPTER_STUBS)
    components = tuple(
        PackageComponent(
            kind=kind,
            path=_COMPONENT_FILENAMES[kind],
            description=_COMPONENT_DESCRIPTIONS[kind],
        )
        for kind in component_kinds
    )
    return PackageManifest(
        problem_id=problem.id,
        name=problem.name,
        model=model,
        status=status,
        counts=_problem_counts(problem),
        components=components,
        regime=_problem_regime(problem),
    )


def write_package(
    problem: VerificationProblem,
    trajectory: Mapping[str, Any],
    directory: str | Path,
    *,
    inspection: Mapping[str, Any] | None = None,
    include_adapter_stubs: bool = False,
) -> PackageManifest:
    """Write a self-contained verification package to ``directory``.

    Validates the problem and trajectory against the export contract before
    writing, so a package never persists internally inconsistent data. When
    ``include_adapter_stubs`` is set, also writes the non-discharging
    adapter-stub descriptors derived from the obligations. Returns the manifest.
    Output is deterministic and regenerable.
    """

    validate_viewer_verification_problems([problem])
    validate_viewer_verification_trajectory(trajectory, problem_id=problem.id)
    # The combined viewer payload re-checks every internal cross-link (trajectory
    # states map to variables, certificate series reference real obligations).
    ir_payload = problem.to_dict()
    validate_viewer_verification_problem_payload({**ir_payload, "trajectory": dict(trajectory)})

    manifest = build_package_manifest(
        problem,
        include_inspection=inspection is not None,
        include_adapter_stubs=include_adapter_stubs,
    )

    output_dir = Path(directory)
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / _COMPONENT_FILENAMES[COMPONENT_IR]).write_text(
        _dump_json(ir_payload), encoding="utf-8"
    )
    (output_dir / _COMPONENT_FILENAMES[COMPONENT_TRAJECTORY]).write_text(
        _dump_json(dict(trajectory)), encoding="utf-8"
    )
    if inspection is not None:
        (output_dir / _COMPONENT_FILENAMES[COMPONENT_INSPECTION]).write_text(
            _dump_json(dict(inspection)), encoding="utf-8"
        )
    if include_adapter_stubs:
        adapter_stubs = obligation_adapter_stubs(problem).to_dict()
        (output_dir / _COMPONENT_FILENAMES[COMPONENT_ADAPTER_STUBS]).write_text(
            _dump_json(adapter_stubs), encoding="utf-8"
        )
    (output_dir / PACKAGE_MANIFEST_FILENAME).write_text(
        _dump_json(manifest.to_dict()), encoding="utf-8"
    )
    return manifest


def read_package(directory: str | Path) -> VerificationPackage:
    """Read and validate a verification package from ``directory``.

    The inverse of :func:`write_package`: reconstructs an equal
    ``VerificationProblem`` and its trajectory, re-checking the manifest, the
    component files, and every internal cross-link. Missing or inconsistent
    packages raise ``ValueError``.
    """

    package_dir = Path(directory)
    manifest_path = package_dir / PACKAGE_MANIFEST_FILENAME
    if not manifest_path.is_file():
        raise ValueError(f"verification package missing {PACKAGE_MANIFEST_FILENAME} in {package_dir}")
    manifest = PackageManifest.from_dict(_read_json(manifest_path))

    ir_payload = _read_component(package_dir, manifest, COMPONENT_IR)
    problem = VerificationProblem.from_dict(ir_payload)
    if problem.id != manifest.problem_id:
        raise ValueError(
            f"verification package IR id {problem.id!r} does not match manifest "
            f"problemId {manifest.problem_id!r}"
        )
    expected_counts = _problem_counts(problem)
    if dict(manifest.counts) != expected_counts:
        raise ValueError(
            f"verification package {manifest.problem_id!r} manifest counts do not "
            "match the IR"
        )
    if manifest.regime is not None and manifest.regime != _problem_regime(problem):
        raise ValueError(
            f"verification package {manifest.problem_id!r} manifest regime does not "
            "match the IR"
        )

    trajectory = _read_component(package_dir, manifest, COMPONENT_TRAJECTORY)
    validate_viewer_verification_trajectory(trajectory, problem_id=problem.id)
    validate_viewer_verification_problems([problem])
    validate_viewer_verification_problem_payload({**ir_payload, "trajectory": trajectory})

    inspection: Mapping[str, Any] | None = None
    if manifest.component(COMPONENT_INSPECTION) is not None:
        inspection = _read_component(package_dir, manifest, COMPONENT_INSPECTION)

    adapter_stubs: Mapping[str, Any] | None = None
    if manifest.component(COMPONENT_ADAPTER_STUBS) is not None:
        adapter_stubs = _read_component(package_dir, manifest, COMPONENT_ADAPTER_STUBS)
        # Structural round-trip validation; reject stubs that drift from the IR.
        report = AdapterStubReport.from_dict(adapter_stubs)
        if report.problem_id != problem.id:
            raise ValueError(
                f"verification package adapter stubs problemId {report.problem_id!r} "
                f"does not match the IR id {problem.id!r}"
            )
        obligation_ids = {obligation.id for obligation in problem.obligations}
        unknown = {stub.obligation_id for stub in report.stubs} - obligation_ids
        if unknown:
            raise ValueError(
                f"verification package adapter stubs reference unknown obligations: "
                f"{sorted(unknown)}"
            )
        # The robustness descriptors must agree with the IR: a stub may flag an
        # obligation robust only where the IR derives it robust (a disturbance set
        # it quantifies over), and must record that exact disturbance set.
        robust_disturbances = robust_obligation_disturbances(problem)
        for stub in report.stubs:
            parameters, assumption_ids = robust_disturbances.get(
                stub.obligation_id, ((), ())
            )
            expected_robust = bool(parameters)
            if stub.robust != expected_robust:
                raise ValueError(
                    f"verification package adapter stub for {stub.obligation_id!r} "
                    f"robustness flag does not match the IR"
                )
            if stub.robust and (
                stub.disturbance_parameters != parameters
                or stub.disturbance_assumption_ids != assumption_ids
            ):
                raise ValueError(
                    f"verification package adapter stub for {stub.obligation_id!r} "
                    "disturbance set does not match the IR"
                )

    return VerificationPackage(
        manifest=manifest,
        problem=problem,
        trajectory=trajectory,
        inspection=inspection,
        adapter_stubs=adapter_stubs,
    )


def validate_drone_flagship_package_consistency(
    packages: Sequence[VerificationPackage | VerificationProblem],
) -> DroneFlagshipConsistencyReport:
    """Validate shared conventions across the generated drone packages.

    The flagship spans multiple verification packages, but they should all be
    projections of one drone parameterization: the same guard-band/geofence
    geometry, obstacle keep-out geometry, disturbance/velocity bounds, and
    assumption conventions where those facts are shared. This routine compares
    those facts from the IR itself and raises ``ValueError`` on drift. It is pure
    validation and claims no proof or certification.
    """

    if not packages:
        raise ValueError("drone flagship consistency validation needs packages")

    problems: list[VerificationProblem] = []
    manifests: list[PackageManifest | None] = []
    for item in packages:
        if isinstance(item, VerificationPackage):
            problems.append(item.problem)
            manifests.append(item.manifest)
        elif isinstance(item, VerificationProblem):
            problems.append(item)
            manifests.append(None)
        else:
            raise ValueError(
                "drone flagship consistency validation expects VerificationPackage "
                "or VerificationProblem entries"
            )

    problem_ids = tuple(problem.id for problem in problems)
    if len(problem_ids) != len(set(problem_ids)):
        raise ValueError("drone flagship consistency validation got duplicate packages")

    groups: dict[str, list[tuple[str, tuple[Any, ...]]]] = {}

    def add(group: str, problem: VerificationProblem, signature: tuple[Any, ...]) -> None:
        groups.setdefault(group, []).append((problem.id, signature))

    for problem, manifest in zip(problems, manifests, strict=True):
        model, status = _problem_model_and_status(problem)
        if not model.startswith("drone-"):
            raise ValueError(
                f"drone flagship consistency validation got non-drone package "
                f"{problem.id!r} with model {model!r}"
            )
        if manifest is not None:
            if manifest.problem_id != problem.id:
                raise ValueError(
                    f"drone package {problem.id!r} manifest problemId "
                    f"{manifest.problem_id!r} does not match the IR"
                )
            if manifest.model != model:
                raise ValueError(
                    f"drone package {problem.id!r} manifest model {manifest.model!r} "
                    f"does not match metadata.verificationModel {model!r}"
                )
            if manifest.status != status:
                raise ValueError(
                    f"drone package {problem.id!r} manifest status {manifest.status!r} "
                    f"does not match metadata.status {status!r}"
                )
        if status != "candidate":
            raise ValueError(
                f"drone package {problem.id!r} must keep candidate status, got {status!r}"
            )
        if {candidate.status for candidate in problem.candidates} - {"candidate"}:
            raise ValueError(
                f"drone package {problem.id!r} has a non-candidate certificate"
            )
        if {obligation.rigor for obligation in problem.obligations} - {
            "external-required"
        }:
            raise ValueError(
                f"drone package {problem.id!r} has a non-external-required obligation"
            )

        assumptions = {assumption.id: assumption for assumption in problem.assumptions}
        candidates = {candidate.id: candidate for candidate in problem.candidates}
        parameters = tuple(parameter.name for parameter in problem.parameters)
        variables = tuple(variable.name for variable in problem.variables)
        has_disturbance = any(
            "disturbance" in assumption.id for assumption in problem.assumptions
        )
        if variables == ("q1", "q2") and parameters == ("v1", "v2"):
            add(
                "nominal planar bounded-parameter declarations",
                problem,
                _parameter_signature(problem),
            )
        if len(parameters) == 1 and parameters[0] in {"w1", "w3"}:
            add(
                "disturbed axis wind-parameter declarations",
                problem,
                _parameter_signature(problem, canonical_names=True),
            )

        geofence = candidates.get("geofence-barrier")
        if geofence is not None and variables == ("q1", "v1"):
            add(
                "horizontal geofence barrier geometry",
                problem,
                _candidate_signature(geofence, variables),
            )
        if geofence is not None and variables == ("q3", "v3"):
            add(
                "vertical geofence barrier geometry",
                problem,
                _candidate_signature(geofence, variables),
            )
        obstacle = candidates.get("obstacle-keepout-barrier")
        if obstacle is not None:
            add(
                "planar obstacle keep-out geometry",
                problem,
                _candidate_signature(obstacle, variables),
            )
            for assumption_id, group in (
                (
                    "planar-speed-within-velocity-bound",
                    "planar velocity-bound assumption",
                ),
                (
                    "drone-maintains-obstacle-standoff",
                    "planar obstacle standoff geometry",
                ),
                (
                    "operating-region-within-guard-band-interior",
                    "planar guard-band interior geometry",
                ),
            ):
                add(
                    group,
                    problem,
                    _required_assumption_signature(problem, assumptions, assumption_id),
                )
            standoff = _required_assumption_signature(
                problem, assumptions, "standoff-exceeds-worst-case-drift"
            )
            add(
                (
                    "disturbed obstacle standoff drift bound"
                    if has_disturbance
                    else "nominal obstacle standoff drift bound"
                ),
                problem,
                standoff,
            )

        if assumptions.get("speed-within-half-guard-reach") is not None:
            add(
                "axis nominal half-guard speed bound",
                problem,
                _assumption_signature(assumptions["speed-within-half-guard-reach"]),
            )
        if assumptions.get("velocity-within-self-reproducing-bound") is not None:
            add(
                "axis nominal velocity bound",
                problem,
                _assumption_signature(
                    assumptions["velocity-within-self-reproducing-bound"]
                ),
            )
        if assumptions.get("timestep-small-vs-guard-band") is not None:
            timestep_small = assumptions["timestep-small-vs-guard-band"]
            add(
                "axis nominal guard-band braking bound",
                problem,
                _assumption_signature(timestep_small),
            )
            add(
                "shared guard-band scalar",
                problem,
                _assumption_rhs_signature(timestep_small),
            )

        if assumptions.get("guard-band-exceeds-worst-case-drift") is not None:
            guard_band = assumptions["guard-band-exceeds-worst-case-drift"]
            add(
                "shared guard-band scalar",
                problem,
                _assumption_rhs_signature(guard_band),
            )
        if assumptions.get("robust-braking-displacement-fits-guard-band") is not None:
            robust_braking = assumptions["robust-braking-displacement-fits-guard-band"]
            add(
                "disturbed axis robust braking bound",
                problem,
                _assumption_signature(robust_braking),
            )
            add(
                "shared guard-band scalar",
                problem,
                _assumption_rhs_signature(robust_braking),
            )

        if assumptions.get("disturbance-within-wind-bound") is not None:
            add(
                "disturbed axis wind-bound assumption",
                problem,
                _assumption_signature(assumptions["disturbance-within-wind-bound"]),
            )
        if assumptions.get("robust-speed-within-tightened-guard-reach") is not None:
            add(
                "disturbed axis tightened speed bound",
                problem,
                _assumption_signature(
                    assumptions["robust-speed-within-tightened-guard-reach"]
                ),
            )
        if assumptions.get("velocity-within-nominal-self-reproducing-bound") is not None:
            add(
                "disturbed axis nominal velocity precondition",
                problem,
                _assumption_signature(
                    assumptions["velocity-within-nominal-self-reproducing-bound"]
                ),
            )

        if (
            problem.dynamics is not None
            and variables == ("q1", "q2")
            and parameters == ("v1", "v2")
        ):
            add(
                "nominal planar coasting dynamics",
                problem,
                _dynamics_signature(problem.dynamics),
            )

    checked_groups: dict[str, tuple[str, ...]] = {}
    for group, entries in groups.items():
        if len(entries) < 2:
            continue
        first_problem_id, first_signature = entries[0]
        for problem_id, signature in entries[1:]:
            if signature != first_signature:
                raise ValueError(
                    "drone flagship consistency mismatch in "
                    f"{group!r}: package {problem_id!r} has signature "
                    f"{signature!r}, expected {first_signature!r} from "
                    f"{first_problem_id!r}"
                )
        checked_groups[group] = tuple(problem_id for problem_id, _ in entries)

    required = (
        "horizontal geofence barrier geometry",
        "vertical geofence barrier geometry",
        "planar obstacle keep-out geometry",
        "planar obstacle standoff geometry",
        "planar guard-band interior geometry",
        "planar velocity-bound assumption",
        "shared guard-band scalar",
    )
    missing = [group for group in required if group not in checked_groups]
    if missing:
        raise ValueError(
            "drone flagship consistency validation did not see enough packages "
            f"to compare required groups: {missing}"
        )

    return DroneFlagshipConsistencyReport(
        problem_ids=problem_ids,
        signature_groups=checked_groups,
    )


def _required_assumption_signature(
    problem: VerificationProblem,
    assumptions: Mapping[str, Any],
    assumption_id: str,
) -> tuple[Any, ...]:
    assumption = assumptions.get(assumption_id)
    if assumption is None:
        raise ValueError(
            f"drone package {problem.id!r} missing required assumption {assumption_id!r}"
        )
    return _assumption_signature(assumption)


def _assumption_signature(assumption: Any) -> tuple[Any, ...]:
    return (
        assumption.role,
        assumption.comparison,
        float(assumption.rhs),
        _canonical_expression(assumption.expression.source, assumption.variables),
    )


def _assumption_rhs_signature(assumption: Any) -> tuple[Any, ...]:
    return (assumption.comparison, float(assumption.rhs))


def _candidate_signature(candidate: Any, variables: Sequence[str]) -> tuple[Any, ...]:
    return (
        candidate.kind,
        candidate.status,
        _canonical_expression(candidate.expression.source, variables),
    )


def _dynamics_signature(dynamics: Any) -> tuple[Any, ...]:
    variables = (*dynamics.state, *(input_spec.name for input_spec in dynamics.inputs))
    return (
        dynamics.kind,
        tuple(dynamics.state),
        tuple(
            _canonical_expression(expression.source, variables)
            for expression in dynamics.rhs
        ),
    )


def _parameter_signature(
    problem: VerificationProblem,
    *,
    canonical_names: bool = False,
) -> tuple[Any, ...]:
    return tuple(
        (
            f"_p{index}" if canonical_names else parameter.name,
            parameter.value,
        )
        for index, parameter in enumerate(problem.parameters)
    )


def _canonical_expression(source: str, variables: Sequence[str]) -> str:
    expression = sp.sympify(source)
    replacements = {
        sp.Symbol(name, real=True): sp.Symbol(f"_x{index}", real=True)
        for index, name in enumerate(variables)
    }
    return sp.srepr(expression.xreplace(replacements))


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ValueError(f"verification package file {path} is not valid JSON: {error}") from error


def _read_component(
    package_dir: Path,
    manifest: PackageManifest,
    kind: str,
) -> dict[str, Any]:
    component = manifest.component(kind)
    if component is None:
        raise ValueError(f"verification package manifest does not index a {kind} component")
    component_path = package_dir / component.path
    if not component_path.is_file():
        raise ValueError(
            f"verification package {manifest.problem_id!r} missing {kind} file "
            f"{component.path}"
        )
    payload = _read_json(component_path)
    if not isinstance(payload, Mapping):
        raise ValueError(
            f"verification package {manifest.problem_id!r} {kind} file must be an object"
        )
    return payload
