"""Stub external-verification adapter that writes inspection artifacts.

The adapter consumes the verification-problem IR and writes the canonical
problem JSON plus a human-readable inspection report. It never attempts,
records, or claims proof discharge; every obligation it touches remains
``rigor="external-required"``.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from engine.verification.ir import (
    AssumptionSpec,
    CandidateSpec,
    DynamicsSpec,
    ObligationSpec,
    RegionSpec,
    VerificationProblem,
)

ADAPTER_NAME = "inspection-stub"
REPORT_STATUS = "exported-for-inspection"

ARTIFACT_PROBLEM_JSON = "verification-problem-json"
ARTIFACT_REPORT_MARKDOWN = "inspection-report-markdown"

_NOTE = (
    "Inspection artifacts only: no obligation has been attempted or "
    "discharged; external sound discharge is still required."
)


@dataclass(frozen=True)
class InspectionArtifact:
    """One file written by the stub adapter."""

    kind: str
    path: Path

    def __post_init__(self) -> None:
        if self.kind not in (ARTIFACT_PROBLEM_JSON, ARTIFACT_REPORT_MARKDOWN):
            raise ValueError(f"unknown inspection artifact kind: {self.kind!r}")

    def to_dict(self) -> dict[str, str]:
        return {"kind": self.kind, "path": str(self.path)}


@dataclass(frozen=True)
class InspectionAdapterReport:
    """Record of one stub adapter run; never a proof result."""

    adapter: str
    problem_id: str
    schema_version: str
    obligation_ids: tuple[str, ...]
    artifacts: tuple[InspectionArtifact, ...]
    status: str = REPORT_STATUS
    note: str = _NOTE

    def __post_init__(self) -> None:
        if self.adapter != ADAPTER_NAME:
            raise ValueError(f"adapter must be {ADAPTER_NAME!r}")
        if self.status != REPORT_STATUS:
            raise ValueError("the stub adapter can only export for inspection")
        if not self.obligation_ids:
            raise ValueError("adapter report must list obligation ids")
        if not self.artifacts:
            raise ValueError("adapter report must list written artifacts")

    def to_dict(self) -> dict[str, Any]:
        return {
            "adapter": self.adapter,
            "problemId": self.problem_id,
            "schemaVersion": self.schema_version,
            "status": self.status,
            "note": self.note,
            "obligationIds": list(self.obligation_ids),
            "artifacts": [artifact.to_dict() for artifact in self.artifacts],
        }


def _dynamics_lines(dynamics: DynamicsSpec | None) -> list[str]:
    lines = ["## Dynamics", ""]
    if dynamics is None:
        lines.extend(["- not encoded in this problem", ""])
        return lines
    if dynamics.kind == "continuous":
        lines.append(f"- kind: continuous (time variable `{dynamics.time_variable}`)")
        for name, rhs in zip(dynamics.state, dynamics.rhs, strict=True):
            lines.append(f"- `{name}' = {rhs.display}`")
    else:
        lines.append(f"- kind: discrete (step variable `{dynamics.time_variable}`)")
        for name, update in zip(dynamics.state, dynamics.rhs, strict=True):
            lines.append(f"- `{name}_next = {update.display}`")
    if dynamics.inputs:
        for input_spec in dynamics.inputs:
            lower = "-inf" if input_spec.lower is None else input_spec.lower
            upper = "inf" if input_spec.upper is None else input_spec.upper
            lines.append(
                f"- {input_spec.role} `{input_spec.name}` in [{lower}, {upper}]"
            )
    else:
        lines.append("- inputs: none (closed loop)")
    lines.append("")
    return lines


def _candidate_lines(candidate: CandidateSpec) -> list[str]:
    lines = [
        f"### `{candidate.id}` — kind: {candidate.kind}",
        "",
        f"- status: {candidate.status} (not accepted by any external sound method)",
        f"- function: `{candidate.expression.display}`",
    ]
    if candidate.equilibrium is not None:
        lines.append(f"- equilibrium: {list(candidate.equilibrium)}")
    if candidate.region_id is not None:
        lines.append(f"- candidate region: `{candidate.region_id}`")
    obligations = ", ".join(f"`{obligation_id}`" for obligation_id in candidate.obligation_ids)
    lines.append(f"- proof obligations: {obligations}")
    lines.append("")
    return lines


def _region_lines(region: RegionSpec) -> list[str]:
    variables = ", ".join(region.variables)
    return [
        f"### `{region.id}` — role: {region.role}",
        "",
        f"- name: {region.name}",
        f"- set: `{region.expression.display} <= {region.level}` over ({variables})",
        "",
    ]


def _assumption_lines(assumption: AssumptionSpec) -> list[str]:
    lines = [
        f"### `{assumption.id}` — role: {assumption.role}",
        "",
        f"- name: {assumption.name}",
        f"- claim: `{assumption.expression.display} {assumption.comparison} {assumption.rhs}`",
    ]
    if assumption.variables:
        variables = ", ".join(f"`{name}`" for name in assumption.variables)
        lines.append(f"- variables: {variables}")
    if assumption.description:
        lines.append(f"- description: {assumption.description}")
    lines.append("")
    return lines


def _obligation_lines(obligation: ObligationSpec) -> list[str]:
    lines = [
        f"### `{obligation.id}` — {obligation.name}",
        "",
        f"- claim: `{obligation.expression.display} {obligation.comparison} {obligation.rhs}`",
        f"- region: `{obligation.region_id}`"
        if obligation.region_id is not None
        else "- region: entire state space",
    ]
    if obligation.excluded_points:
        points = "; ".join(str(list(point)) for point in obligation.excluded_points)
        lines.append(f"- excluded points: {points}")
    if obligation.assumption_ids:
        assumptions = ", ".join(
            f"`{assumption_id}`" for assumption_id in obligation.assumption_ids
        )
        lines.append(f"- assumptions: {assumptions}")
    else:
        lines.append("- assumptions: none")
    if obligation.description:
        lines.append(f"- description: {obligation.description}")
    lines.append(f"- rigor: {obligation.rigor} (awaiting external discharge)")
    lines.append("")
    return lines


def render_inspection_markdown(problem: VerificationProblem) -> str:
    """Render a deterministic human-readable report for one problem."""

    lines = [
        f"# Verification problem: {problem.name}",
        "",
        f"- id: `{problem.id}`",
        f"- source: `{problem.source}`",
        f"- schema: `{problem.schema_version}`",
        f"- adapter: `{ADAPTER_NAME}`",
        "",
        "Status: every obligation below awaits external sound discharge. This",
        "report is for inspection only and records no proof results.",
        "",
        "## Variables",
        "",
    ]
    for variable in problem.variables:
        lines.append(f"- `{variable.name}` (latex: `{variable.latex}`)")
    lines.extend(["", "## Parameters", ""])
    if problem.parameters:
        for parameter in problem.parameters:
            value = "symbolic (no value bound)" if parameter.value is None else parameter.value
            lines.append(f"- `{parameter.name}` = {value}")
    else:
        lines.append("- none")
    lines.append("")
    lines.extend(_dynamics_lines(problem.dynamics))
    lines.extend(["## Regions", ""])
    if problem.regions:
        for region in problem.regions:
            lines.extend(_region_lines(region))
    else:
        lines.extend(["- none", ""])
    lines.extend(["## Assumptions", ""])
    if problem.assumptions:
        for assumption in problem.assumptions:
            lines.extend(_assumption_lines(assumption))
    else:
        lines.extend(["- none", ""])
    lines.extend(["## Candidate certificates", ""])
    if problem.candidates:
        for candidate in problem.candidates:
            lines.extend(_candidate_lines(candidate))
    else:
        lines.extend(["- none", ""])
    lines.extend(["## Obligations", ""])
    for obligation in problem.obligations:
        lines.extend(_obligation_lines(obligation))
    if problem.metadata is not None:
        lines.extend(["## Metadata", ""])
        for key in sorted(problem.metadata):
            lines.append(f"- {key}: {problem.metadata[key]}")
        lines.append("")
    return "\n".join(lines)


def write_inspection_artifacts(
    problem: VerificationProblem,
    directory: str | Path,
) -> InspectionAdapterReport:
    """Write the canonical problem JSON and inspection report for a problem."""

    output_dir = Path(directory)
    output_dir.mkdir(parents=True, exist_ok=True)

    problem_path = output_dir / f"{problem.id}.verification-problem.json"
    problem.write_json(problem_path)
    report_path = output_dir / f"{problem.id}.inspection.md"
    report_path.write_text(render_inspection_markdown(problem), encoding="utf-8")

    return InspectionAdapterReport(
        adapter=ADAPTER_NAME,
        problem_id=problem.id,
        schema_version=problem.schema_version,
        obligation_ids=tuple(obligation.id for obligation in problem.obligations),
        artifacts=(
            InspectionArtifact(kind=ARTIFACT_PROBLEM_JSON, path=problem_path),
            InspectionArtifact(kind=ARTIFACT_REPORT_MARKDOWN, path=report_path),
        ),
    )
