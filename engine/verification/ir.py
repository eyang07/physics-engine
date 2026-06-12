"""Serializable verification-problem intermediate representation.

The IR describes obligations that an external sound method may try to
discharge. It does not store proof results and it never marks a claim
certified.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

SCHEMA_VERSION = "verification-problem/v0"


@dataclass(frozen=True)
class ExpressionSpec:
    """A symbolic expression encoded for transport, not execution."""

    format: str
    source: str
    display: str
    latex: str

    def to_dict(self) -> dict[str, str]:
        return {
            "format": self.format,
            "source": self.source,
            "display": self.display,
            "latex": self.latex,
        }


@dataclass(frozen=True)
class VariableSpec:
    name: str
    latex: str

    def to_dict(self) -> dict[str, str]:
        return {"name": self.name, "latex": self.latex}


@dataclass(frozen=True)
class ParameterSpec:
    name: str
    latex: str
    value: float | None = None

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {"name": self.name, "latex": self.latex}
        if self.value is not None:
            payload["value"] = self.value
        return payload


@dataclass(frozen=True)
class RegionSpec:
    """A named region in the verification problem."""

    id: str
    name: str
    kind: str
    role: str
    variables: tuple[str, ...]
    expression: ExpressionSpec
    level: float
    convention: str = "expression <= level"

    def __post_init__(self) -> None:
        if self.kind != "sublevel":
            raise ValueError("v0 regions must have kind='sublevel'")
        if self.convention != "expression <= level":
            raise ValueError("v0 regions must use the sublevel convention")
        if not self.variables:
            raise ValueError("region variables must be non-empty")

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "kind": self.kind,
            "role": self.role,
            "variables": list(self.variables),
            "expression": self.expression.to_dict(),
            "level": self.level,
            "convention": self.convention,
        }


@dataclass(frozen=True)
class ObligationSpec:
    """A single claim, in canonical form ``expression comparison rhs``."""

    id: str
    name: str
    expression: ExpressionSpec
    comparison: str
    rhs: float = 0.0
    region_id: str | None = None
    excluded_points: tuple[tuple[float, ...], ...] = ()
    description: str = ""
    rigor: str = "external-required"

    def __post_init__(self) -> None:
        if self.comparison not in ("<=", "<", ">=", ">"):
            raise ValueError("comparison must be one of <=, <, >=, >")
        if self.rigor != "external-required":
            raise ValueError("verification obligations must require external discharge")
        lengths = {len(point) for point in self.excluded_points}
        if len(lengths) > 1:
            raise ValueError("excluded points must share the same dimension")

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "id": self.id,
            "name": self.name,
            "expression": self.expression.to_dict(),
            "comparison": self.comparison,
            "rhs": self.rhs,
            "excludedPoints": [list(point) for point in self.excluded_points],
            "description": self.description,
            "rigor": self.rigor,
        }
        if self.region_id is not None:
            payload["regionId"] = self.region_id
        return payload


@dataclass(frozen=True)
class VerificationProblem:
    """A portable verification problem for inspection or external adapters."""

    id: str
    name: str
    source: str
    variables: tuple[VariableSpec, ...]
    parameters: tuple[ParameterSpec, ...]
    regions: tuple[RegionSpec, ...]
    obligations: tuple[ObligationSpec, ...]
    metadata: Mapping[str, Any] | None = None
    schema_version: str = SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != SCHEMA_VERSION:
            raise ValueError(f"schema_version must be {SCHEMA_VERSION!r}")
        if not self.variables:
            raise ValueError("verification problem must have variables")
        if not self.obligations:
            raise ValueError("verification problem must have obligations")

        region_ids = [region.id for region in self.regions]
        if len(set(region_ids)) != len(region_ids):
            raise ValueError("region ids must be unique")
        obligation_ids = [obligation.id for obligation in self.obligations]
        if len(set(obligation_ids)) != len(obligation_ids):
            raise ValueError("obligation ids must be unique")

        known_regions = set(region_ids)
        for obligation in self.obligations:
            if obligation.region_id is not None and obligation.region_id not in known_regions:
                raise ValueError(f"unknown obligation region id: {obligation.region_id}")
            for point in obligation.excluded_points:
                if len(point) != len(self.variables):
                    raise ValueError("excluded points must match the variable dimension")

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schemaVersion": self.schema_version,
            "id": self.id,
            "name": self.name,
            "source": self.source,
            "variables": [variable.to_dict() for variable in self.variables],
            "parameters": [parameter.to_dict() for parameter in self.parameters],
            "regions": [region.to_dict() for region in self.regions],
            "obligations": [obligation.to_dict() for obligation in self.obligations],
        }
        if self.metadata is not None:
            payload["metadata"] = dict(self.metadata)
        return payload

    def write_json(self, path: str | Path) -> None:
        output_path = Path(path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")


def problem_from_parts(
    *,
    id: str,
    name: str,
    source: str,
    variables: Sequence[VariableSpec],
    parameters: Sequence[ParameterSpec],
    regions: Sequence[RegionSpec],
    obligations: Sequence[ObligationSpec],
    metadata: Mapping[str, Any] | None = None,
) -> VerificationProblem:
    return VerificationProblem(
        id=id,
        name=name,
        source=source,
        variables=tuple(variables),
        parameters=tuple(parameters),
        regions=tuple(regions),
        obligations=tuple(obligations),
        metadata=metadata,
    )
