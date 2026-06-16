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

from collections.abc import Mapping
from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

from engine.export.verification_contract import (
    validate_viewer_verification_problem_payload,
    validate_viewer_verification_problems,
    validate_viewer_verification_trajectory,
)
from engine.verification import VerificationProblem
from engine.verification.adapter_stubs import (
    AdapterStubReport,
    obligation_adapter_stubs,
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
class PackageManifest:
    """The index of one verification package's contents."""

    problem_id: str
    name: str
    model: str
    status: str
    counts: Mapping[str, int]
    components: tuple[PackageComponent, ...]
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
        return {
            "schemaVersion": self.schema_version,
            "problemId": self.problem_id,
            "name": self.name,
            "model": self.model,
            "status": self.status,
            "counts": {key: int(self.counts[key]) for key in _COUNT_KEYS},
            "components": [component.to_dict() for component in self.components],
        }

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
        return cls(
            problem_id=_require_string(data, "problemId", "package manifest"),
            name=_require_string(data, "name", "package manifest"),
            model=_require_string(data, "model", "package manifest"),
            status=_require_string(data, "status", "package manifest"),
            counts={key: _require_int(counts, key, "package manifest counts") for key in _COUNT_KEYS},
            components=tuple(PackageComponent.from_dict(item) for item in components),
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
class PackageIndexEntry:
    """One package's summary in the discovery index."""

    problem_id: str
    name: str
    model: str
    status: str
    manifest_path: str
    component_kinds: tuple[str, ...]
    counts: Mapping[str, int]

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
        return {
            "problemId": self.problem_id,
            "name": self.name,
            "model": self.model,
            "status": self.status,
            "manifestPath": self.manifest_path,
            "componentKinds": list(self.component_kinds),
            "counts": {key: int(self.counts[key]) for key in _COUNT_KEYS},
        }

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
        return cls(
            problem_id=_require_string(data, "problemId", "package index entry"),
            name=_require_string(data, "name", "package index entry"),
            model=_require_string(data, "model", "package index entry"),
            status=_require_string(data, "status", "package index entry"),
            manifest_path=_require_string(data, "manifestPath", "package index entry"),
            component_kinds=tuple(component_kinds),
            counts={key: _require_int(counts, key, "package index entry counts") for key in _COUNT_KEYS},
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

    return VerificationPackage(
        manifest=manifest,
        problem=problem,
        trajectory=trajectory,
        inspection=inspection,
        adapter_stubs=adapter_stubs,
    )


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
