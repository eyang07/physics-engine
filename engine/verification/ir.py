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

SCHEMA_VERSION = "verification-problem/v3"

_ORDER_COMPARISONS = ("<=", "<", ">=", ">")
_ASSUMPTION_COMPARISONS = (*_ORDER_COMPARISONS, "=", "!=")
_PROOF_STATUSES = ("external-required", "measured-holds", "measured-violated")


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
class InputSpec:
    """A control or disturbance channel, optionally interval-bounded."""

    name: str
    latex: str
    role: str
    lower: float | None = None
    upper: float | None = None

    def __post_init__(self) -> None:
        if self.role not in ("control", "disturbance"):
            raise ValueError("input role must be 'control' or 'disturbance'")
        if self.lower is not None and self.upper is not None and self.lower > self.upper:
            raise ValueError("input lower bound must not exceed the upper bound")

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "name": self.name,
            "latex": self.latex,
            "role": self.role,
        }
        if self.lower is not None:
            payload["lower"] = self.lower
        if self.upper is not None:
            payload["upper"] = self.upper
        return payload


@dataclass(frozen=True)
class DynamicsSpec:
    """The model the obligations were derived along.

    ``state`` lists variable names in order. For ``kind="continuous"``,
    ``rhs[i]`` is the time derivative of ``state[i]`` and ``time_variable``
    is the time symbol. For ``kind="discrete"``, ``rhs[i]`` is the update
    expression for ``state[i]`` and ``time_variable`` is the step symbol.
    Inputs are open control/disturbance channels; a closed-loop system has
    none.
    """

    kind: str
    time_variable: str
    state: tuple[str, ...]
    rhs: tuple[ExpressionSpec, ...]
    inputs: tuple[InputSpec, ...] = ()

    def __post_init__(self) -> None:
        if self.kind not in ("continuous", "discrete"):
            raise ValueError("v2 dynamics must have kind 'continuous' or 'discrete'")
        if not self.state:
            raise ValueError("dynamics state must be non-empty")
        if len(self.state) != len(self.rhs):
            raise ValueError("dynamics state and expressions must have the same length")
        names = [self.time_variable, *self.state, *(spec.name for spec in self.inputs)]
        if len(names) != len(set(names)):
            raise ValueError(
                "dynamics independent variable, state, and input names must be disjoint"
            )

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "kind": self.kind,
            "state": list(self.state),
            "inputs": [input_spec.to_dict() for input_spec in self.inputs],
        }
        if self.kind == "continuous":
            payload["timeVariable"] = self.time_variable
            payload["rhs"] = [expression.to_dict() for expression in self.rhs]
        else:
            payload["stepVariable"] = self.time_variable
            payload["update"] = [expression.to_dict() for expression in self.rhs]
        return payload


@dataclass(frozen=True)
class CandidateSpec:
    """A candidate certificate; a proposal until externally accepted."""

    id: str
    name: str
    kind: str
    expression: ExpressionSpec
    obligation_ids: tuple[str, ...]
    equilibrium: tuple[float, ...] | None = None
    region_id: str | None = None
    status: str = "candidate"

    def __post_init__(self) -> None:
        if self.kind not in ("lyapunov", "barrier"):
            raise ValueError("candidate kind must be 'lyapunov' or 'barrier'")
        if self.status != "candidate":
            raise ValueError("candidates must keep status='candidate'")
        if not self.obligation_ids:
            raise ValueError("candidate must reference its proof obligations")

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "id": self.id,
            "name": self.name,
            "kind": self.kind,
            "status": self.status,
            "expression": self.expression.to_dict(),
            "obligationIds": list(self.obligation_ids),
        }
        if self.equilibrium is not None:
            payload["equilibrium"] = list(self.equilibrium)
        if self.region_id is not None:
            payload["regionId"] = self.region_id
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
class RegionGeometrySpec:
    """A sampled 2-D rendering aid for one symbolic region.

    The scalar field is measured geometry for visualization only. It does not
    prove containment, exclusion, or invariance.
    """

    region_id: str
    role: str
    projection: str
    plane_variables: tuple[str, str]
    state_axes: tuple[str, str]
    variable_to_state_axis: Mapping[str, str]
    x_values: tuple[float, ...]
    y_values: tuple[float, ...]
    values: tuple[tuple[float, ...], ...]
    level: float
    convention: str
    boundary_polylines: tuple[tuple[tuple[float, float], ...], ...] = ()
    kind: str = "scalar-field-grid"
    rigor: str = "measured"
    note: str = (
        "Sampled scalar field of the symbolic region definition for rendering; "
        "not a proof or certificate."
    )

    def __post_init__(self) -> None:
        if self.kind != "scalar-field-grid":
            raise ValueError("region geometry kind must be 'scalar-field-grid'")
        if self.rigor != "measured":
            raise ValueError("region geometry must keep rigor='measured'")
        if len(self.plane_variables) != 2:
            raise ValueError("region geometry must name exactly two plane variables")
        if self.plane_variables[0] == self.plane_variables[1]:
            raise ValueError("region geometry plane variables must be distinct")
        if len(self.state_axes) != 2:
            raise ValueError("region geometry must name exactly two state axes")
        missing = set(self.plane_variables) - set(self.variable_to_state_axis)
        if missing:
            raise ValueError(
                f"region geometry missing variable-to-state-axis mappings: {sorted(missing)}"
            )
        expected_axes = tuple(self.variable_to_state_axis[name] for name in self.plane_variables)
        if expected_axes != self.state_axes:
            raise ValueError("region geometry state axes must match the variable mapping")
        if not self.x_values or not self.y_values:
            raise ValueError("region geometry grid axes must be non-empty")
        if len(self.values) != len(self.y_values):
            raise ValueError("region geometry row count must match y_values")
        row_widths = {len(row) for row in self.values}
        if row_widths != {len(self.x_values)}:
            raise ValueError("region geometry column count must match x_values")
        for polyline in self.boundary_polylines:
            if len(polyline) < 2:
                raise ValueError("region geometry boundary polylines need at least two points")
            for point in polyline:
                if len(point) != 2:
                    raise ValueError("region geometry boundary points must be 2-D")

    def to_dict(self) -> dict[str, Any]:
        return {
            "regionId": self.region_id,
            "role": self.role,
            "kind": self.kind,
            "projection": self.projection,
            "plane": {
                "variables": list(self.plane_variables),
                "stateAxes": list(self.state_axes),
                "variableToStateAxis": dict(self.variable_to_state_axis),
            },
            "grid": {
                "x": list(self.x_values),
                "y": list(self.y_values),
                "values": [list(row) for row in self.values],
            },
            "boundaryPolylines": [
                [list(point) for point in polyline]
                for polyline in self.boundary_polylines
            ],
            "level": self.level,
            "convention": self.convention,
            "rigor": self.rigor,
            "note": self.note,
        }


@dataclass(frozen=True)
class AssumptionSpec:
    """A precondition an external verifier may assume while discharging claims."""

    id: str
    name: str
    expression: ExpressionSpec
    comparison: str
    rhs: float = 0.0
    variables: tuple[str, ...] = ()
    role: str = "domain"
    description: str = ""

    def __post_init__(self) -> None:
        if self.comparison not in _ASSUMPTION_COMPARISONS:
            raise ValueError(
                "assumption comparison must be one of "
                + ", ".join(_ASSUMPTION_COMPARISONS)
            )
        if self.role not in ("domain", "parameter-domain", "regularity", "model"):
            raise ValueError(
                "assumption role must be one of domain, parameter-domain, "
                "regularity, or model"
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "role": self.role,
            "expression": self.expression.to_dict(),
            "comparison": self.comparison,
            "rhs": self.rhs,
            "variables": list(self.variables),
            "description": self.description,
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
    assumption_ids: tuple[str, ...] = ()
    description: str = ""
    rigor: str = "external-required"

    def __post_init__(self) -> None:
        if self.comparison not in _ORDER_COMPARISONS:
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
            "assumptionIds": list(self.assumption_ids),
            "description": self.description,
            "rigor": self.rigor,
        }
        if self.region_id is not None:
            payload["regionId"] = self.region_id
        return payload


@dataclass(frozen=True)
class ProofStatusSpec:
    """A measured status record for one obligation evaluation surface.

    This is sampled evidence only. It records where a backend evaluation was
    performed and whether the sampled values satisfied the obligation
    comparison there; it never certifies or proves the obligation.
    """

    id: str
    obligation_id: str
    status: str
    evaluation_kind: str
    sample_count: int
    comparison: str
    rhs: float = 0.0
    candidate_id: str | None = None
    region_id: str | None = None
    system: str | None = None
    variables: tuple[str, ...] = ()
    state_axes: tuple[str, ...] = ()
    variable_to_state_axis: Mapping[str, str] | None = None
    source: str = ""
    worst_value: float | None = None
    worst_point: tuple[float, ...] | None = None
    worst_time: float | None = None
    rigor: str = "measured"
    external_status: str = "external-required"
    note: str = (
        "Measured sampled check only; a clean sample is evidence, not a proof "
        "or certificate."
    )

    def __post_init__(self) -> None:
        if self.status not in _PROOF_STATUSES:
            raise ValueError("proof status must be external-required or measured")
        if self.external_status != "external-required":
            raise ValueError("proof status external_status must stay external-required")
        if self.comparison not in _ORDER_COMPARISONS:
            raise ValueError("proof status comparison must be one of <=, <, >=, >")
        if self.status == "external-required":
            if self.rigor != "external-required":
                raise ValueError("external-required proof status must use matching rigor")
        elif self.rigor != "measured":
            raise ValueError("measured proof status must use rigor='measured'")
        if self.sample_count < 0:
            raise ValueError("proof status sample count must be nonnegative")
        if self.status != "external-required" and self.sample_count == 0:
            raise ValueError("measured proof status needs at least one sample")
        if self.worst_point is not None and self.variables:
            if len(self.worst_point) != len(self.variables):
                raise ValueError("proof status worst point must match variables")
        if self.variable_to_state_axis is not None:
            missing = set(self.variables) - set(self.variable_to_state_axis)
            if missing:
                raise ValueError(
                    "proof status missing variable-to-state-axis mappings: "
                    f"{sorted(missing)}"
                )
            expected_axes = tuple(self.variable_to_state_axis[name] for name in self.variables)
            if self.state_axes and expected_axes != self.state_axes:
                raise ValueError("proof status state axes must match variable mapping")

    def to_dict(self) -> dict[str, Any]:
        evaluation: dict[str, Any] = {
            "kind": self.evaluation_kind,
            "sampleCount": self.sample_count,
        }
        if self.system is not None:
            evaluation["system"] = self.system
        if self.source:
            evaluation["source"] = self.source
        if self.variables:
            evaluation["variables"] = list(self.variables)
        if self.state_axes:
            evaluation["stateAxes"] = list(self.state_axes)
        if self.variable_to_state_axis is not None:
            evaluation["variableToStateAxis"] = dict(self.variable_to_state_axis)

        payload: dict[str, Any] = {
            "id": self.id,
            "obligationId": self.obligation_id,
            "status": self.status,
            "rigor": self.rigor,
            "externalStatus": self.external_status,
            "evaluation": evaluation,
            "comparison": self.comparison,
            "rhs": self.rhs,
            "note": self.note,
        }
        if self.candidate_id is not None:
            payload["candidateId"] = self.candidate_id
        if self.region_id is not None:
            payload["regionId"] = self.region_id
        if self.worst_value is not None or self.worst_point is not None:
            worst: dict[str, Any] = {}
            if self.worst_value is not None:
                worst["value"] = self.worst_value
            if self.worst_point is not None:
                worst["point"] = list(self.worst_point)
            if self.worst_time is not None:
                worst["time"] = self.worst_time
            payload["worst"] = worst
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
    assumptions: tuple[AssumptionSpec, ...] = ()
    dynamics: DynamicsSpec | None = None
    open_loop_dynamics: DynamicsSpec | None = None
    candidates: tuple[CandidateSpec, ...] = ()
    system: str | None = None
    region_geometry: tuple[RegionGeometrySpec, ...] = ()
    proof_statuses: tuple[ProofStatusSpec, ...] = ()
    metadata: Mapping[str, Any] | None = None
    schema_version: str = SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != SCHEMA_VERSION:
            raise ValueError(f"schema_version must be {SCHEMA_VERSION!r}")
        if not self.variables:
            raise ValueError("verification problem must have variables")
        if not self.obligations:
            raise ValueError("verification problem must have obligations")
        if self.system is not None and not self.system:
            raise ValueError("verification problem system id must be non-empty")
        if self.metadata is not None:
            metadata_system = self.metadata.get("system")
            if (
                self.system is not None
                and metadata_system is not None
                and metadata_system != self.system
            ):
                raise ValueError("metadata system must match the verification system")

        variable_names = tuple(variable.name for variable in self.variables)
        if len(set(variable_names)) != len(variable_names):
            raise ValueError("variable names must be unique")
        parameter_names = tuple(parameter.name for parameter in self.parameters)
        if len(set(parameter_names)) != len(parameter_names):
            raise ValueError("parameter names must be unique")
        duplicate_names = set(variable_names) & set(parameter_names)
        if duplicate_names:
            raise ValueError(
                f"parameters must not shadow variables: {sorted(duplicate_names)}"
            )

        region_ids = [region.id for region in self.regions]
        if len(set(region_ids)) != len(region_ids):
            raise ValueError("region ids must be unique")
        obligation_ids = [obligation.id for obligation in self.obligations]
        if len(set(obligation_ids)) != len(obligation_ids):
            raise ValueError("obligation ids must be unique")
        assumption_ids = [assumption.id for assumption in self.assumptions]
        if len(set(assumption_ids)) != len(assumption_ids):
            raise ValueError("assumption ids must be unique")

        known_regions = set(region_ids)
        known_assumptions = set(assumption_ids)
        known_variables = set(variable_names)
        for region in self.regions:
            unknown_region_variables = set(region.variables) - known_variables
            if unknown_region_variables:
                raise ValueError(
                    f"unknown region variables: {sorted(unknown_region_variables)}"
                )
        for obligation in self.obligations:
            if obligation.region_id is not None and obligation.region_id not in known_regions:
                raise ValueError(f"unknown obligation region id: {obligation.region_id}")
            unknown_assumptions = set(obligation.assumption_ids) - known_assumptions
            if unknown_assumptions:
                raise ValueError(
                    f"unknown obligation assumption ids: {sorted(unknown_assumptions)}"
                )
            for point in obligation.excluded_points:
                if len(point) != len(self.variables):
                    raise ValueError("excluded points must match the variable dimension")

        if self.dynamics is not None and self.dynamics.state != variable_names:
            raise ValueError("dynamics state must match the problem variables in order")
        if (
            self.open_loop_dynamics is not None
            and self.open_loop_dynamics.state != variable_names
        ):
            raise ValueError(
                "open-loop dynamics state must match the problem variables in order"
            )
        dynamics_specs = tuple(
            spec for spec in (self.dynamics, self.open_loop_dynamics) if spec is not None
        )
        input_names = tuple(
            input_spec.name for spec in dynamics_specs for input_spec in spec.inputs
        )
        time_names = tuple(spec.time_variable for spec in dynamics_specs)
        known_names = {*variable_names, *parameter_names, *input_names, *time_names}
        for assumption in self.assumptions:
            unknown_variables = set(assumption.variables) - known_names
            if unknown_variables:
                raise ValueError(
                    f"unknown assumption variables: {sorted(unknown_variables)}"
                )

        known_obligations = set(obligation_ids)
        candidate_ids = [candidate.id for candidate in self.candidates]
        if len(set(candidate_ids)) != len(candidate_ids):
            raise ValueError("candidate ids must be unique")
        for candidate in self.candidates:
            if candidate.region_id is not None and candidate.region_id not in known_regions:
                raise ValueError(f"unknown candidate region id: {candidate.region_id}")
            unknown = set(candidate.obligation_ids) - known_obligations
            if unknown:
                raise ValueError(f"unknown candidate obligation ids: {sorted(unknown)}")
            if candidate.equilibrium is not None and len(candidate.equilibrium) != len(
                self.variables
            ):
                raise ValueError("candidate equilibrium must match the variable dimension")
        known_candidates = set(candidate_ids)
        region_roles = {region.id: region.role for region in self.regions}
        for geometry in self.region_geometry:
            if geometry.region_id not in known_regions:
                raise ValueError(f"unknown region geometry id: {geometry.region_id}")
            if geometry.role != region_roles[geometry.region_id]:
                raise ValueError("region geometry role must match the referenced region")
            unknown_variables = set(geometry.plane_variables) - known_variables
            if unknown_variables:
                raise ValueError(
                    f"unknown region geometry variables: {sorted(unknown_variables)}"
                )
        proof_status_ids = [status.id for status in self.proof_statuses]
        if len(set(proof_status_ids)) != len(proof_status_ids):
            raise ValueError("proof status ids must be unique")
        for status in self.proof_statuses:
            if status.obligation_id not in known_obligations:
                raise ValueError(f"unknown proof status obligation id: {status.obligation_id}")
            if status.candidate_id is not None and status.candidate_id not in known_candidates:
                raise ValueError(f"unknown proof status candidate id: {status.candidate_id}")
            if status.region_id is not None and status.region_id not in known_regions:
                raise ValueError(f"unknown proof status region id: {status.region_id}")
            unknown_variables = set(status.variables) - known_variables
            if unknown_variables:
                raise ValueError(
                    f"unknown proof status variables: {sorted(unknown_variables)}"
                )

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schemaVersion": self.schema_version,
            "id": self.id,
            "name": self.name,
            "source": self.source,
            "system": self.system,
            "variables": [variable.to_dict() for variable in self.variables],
            "parameters": [parameter.to_dict() for parameter in self.parameters],
            "regions": [region.to_dict() for region in self.regions],
            "assumptions": [assumption.to_dict() for assumption in self.assumptions],
            "obligations": [obligation.to_dict() for obligation in self.obligations],
            "candidates": [candidate.to_dict() for candidate in self.candidates],
            "regionGeometry": [geometry.to_dict() for geometry in self.region_geometry],
            "proofStatuses": [status.to_dict() for status in self.proof_statuses],
        }
        if self.dynamics is not None:
            payload["dynamics"] = self.dynamics.to_dict()
        if self.open_loop_dynamics is not None:
            payload["openLoopDynamics"] = self.open_loop_dynamics.to_dict()
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
    system: str | None = None,
    variables: Sequence[VariableSpec],
    parameters: Sequence[ParameterSpec],
    regions: Sequence[RegionSpec],
    obligations: Sequence[ObligationSpec],
    assumptions: Sequence[AssumptionSpec] = (),
    dynamics: DynamicsSpec | None = None,
    open_loop_dynamics: DynamicsSpec | None = None,
    candidates: Sequence[CandidateSpec] = (),
    region_geometry: Sequence[RegionGeometrySpec] = (),
    proof_statuses: Sequence[ProofStatusSpec] = (),
    metadata: Mapping[str, Any] | None = None,
) -> VerificationProblem:
    return VerificationProblem(
        id=id,
        name=name,
        source=source,
        system=system,
        variables=tuple(variables),
        parameters=tuple(parameters),
        regions=tuple(regions),
        obligations=tuple(obligations),
        assumptions=tuple(assumptions),
        dynamics=dynamics,
        open_loop_dynamics=open_loop_dynamics,
        candidates=tuple(candidates),
        region_geometry=tuple(region_geometry),
        proof_statuses=tuple(proof_statuses),
        metadata=metadata,
    )
