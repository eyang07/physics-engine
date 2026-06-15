"""Measured verification diagnostics exported for viewer consumption."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any, Mapping, Sequence

import numpy as np
import sympy as sp

from engine.verification.ir import (
    CandidateSpec,
    ExpressionSpec,
    ObligationSpec,
    ProofStatusSpec,
    RegionGeometrySpec,
    VerificationProblem,
)

_MEASURED_NOTE = (
    "Measured sampled check only; a clean sample is evidence, not a proof "
    "or certificate."
)


@dataclass(frozen=True)
class CertificateTrajectoryDiagnostics:
    """Series payload and metadata for candidate values along one trajectory."""

    series: Mapping[str, tuple[float, ...]]
    metadata: tuple[dict[str, Any], ...]


def certificate_series_for_trajectory(
    problem: VerificationProblem,
    *,
    time: Sequence[float],
    states: np.ndarray,
    state_names: Sequence[str],
    variable_to_state_axis: Mapping[str, str],
) -> CertificateTrajectoryDiagnostics:
    """Evaluate candidate values and flow derivatives on a trajectory grid.

    The returned numeric series are aligned to ``time``. The flow derivative is
    evaluated from the verification problem dynamics at the trajectory sample
    points; this is measured diagnostic data, not proof discharge.
    """

    if problem.dynamics is None:
        raise ValueError("candidate trajectory series require problem dynamics")
    # The candidate value B(x(t)) is well-defined for any dynamics; only the
    # flow derivative dB/dt is a continuous-time notion, so discrete problems get
    # the value series alone.
    is_continuous = problem.dynamics.kind == "continuous"

    time_array = np.asarray(time, dtype=float)
    state_array = np.asarray(states, dtype=float)
    if state_array.shape[0] != time_array.shape[0]:
        raise ValueError("time and states must have matching sample counts")

    variable_names = tuple(variable.name for variable in problem.variables)
    problem_points = _trajectory_problem_points(
        state_array,
        state_names=tuple(state_names),
        variable_names=variable_names,
        variable_to_state_axis=variable_to_state_axis,
    )
    variables = _symbols_for_names(variable_names, _problem_expressions(problem))
    rhs = (
        tuple(_expression(expression) for expression in problem.dynamics.rhs)
        if is_continuous
        else ()
    )
    obligations_by_id = {obligation.id: obligation for obligation in problem.obligations}

    series: dict[str, tuple[float, ...]] = {}
    metadata: list[dict[str, Any]] = []
    for candidate in problem.candidates:
        candidate_expression = _expression(candidate.expression)
        value_series_name = _series_name(candidate.id, "value")
        series[value_series_name] = tuple(
            float(value)
            for value in _evaluate_expression(candidate_expression, variables, problem_points)
        )
        value_obligations = _matching_obligation_ids(
            candidate,
            obligations_by_id,
            candidate_expression,
        )
        metadata.append(
            _certificate_series_record(
                problem=problem,
                candidate=candidate,
                kind="candidate-value",
                label="B(x(t))",
                series_name=value_series_name,
                obligation_ids=value_obligations,
                obligations_by_id=obligations_by_id,
            )
        )

        if not is_continuous:
            continue

        flow_derivative = sp.simplify(
            sum(
                sp.diff(candidate_expression, variable) * component
                for variable, component in zip(variables, rhs, strict=True)
            )
        )
        derivative_series_name = _series_name(candidate.id, "flow_derivative")
        series[derivative_series_name] = tuple(
            float(value)
            for value in _evaluate_expression(flow_derivative, variables, problem_points)
        )
        derivative_obligations = _matching_obligation_ids(
            candidate,
            obligations_by_id,
            flow_derivative,
        )
        metadata.append(
            _certificate_series_record(
                problem=problem,
                candidate=candidate,
                kind="flow-derivative",
                label="dB/dt along verification dynamics",
                series_name=derivative_series_name,
                obligation_ids=derivative_obligations,
                obligations_by_id=obligations_by_id,
            )
        )

    return CertificateTrajectoryDiagnostics(series=series, metadata=tuple(metadata))


def sampled_region_proof_statuses(problem: VerificationProblem) -> tuple[ProofStatusSpec, ...]:
    """Sample obligation inequalities on exported region-geometry grids."""

    variables = tuple(variable.name for variable in problem.variables)
    regions_by_id = {region.id: region for region in problem.regions}
    geometry_by_region = {geometry.region_id: geometry for geometry in problem.region_geometry}
    candidate_by_obligation = _candidate_by_obligation(problem)
    statuses: list[ProofStatusSpec] = []
    expressions = _problem_expressions(problem)
    symbols = _symbols_for_names(variables, expressions)

    for obligation in problem.obligations:
        if obligation.region_id is None:
            continue
        region = regions_by_id[obligation.region_id]
        geometry = geometry_by_region.get(obligation.region_id)
        if geometry is None:
            continue
        points = _region_geometry_points(
            geometry,
            variables=variables,
            inside_values=np.asarray(geometry.values, dtype=float) <= float(region.level),
        )
        if points.shape[0] == 0:
            statuses.append(
                ProofStatusSpec(
                    id=f"{obligation.id}-region-grid",
                    obligation_id=obligation.id,
                    candidate_id=candidate_by_obligation.get(obligation.id),
                    region_id=obligation.region_id,
                    status="external-required",
                    rigor="external-required",
                    evaluation_kind="region-grid",
                    sample_count=0,
                    comparison=obligation.comparison,
                    rhs=float(obligation.rhs),
                    system=problem.system,
                    variables=variables,
                    state_axes=tuple(geometry.variable_to_state_axis[name] for name in variables),
                    variable_to_state_axis=dict(geometry.variable_to_state_axis),
                    source=f"regionGeometry:{geometry.region_id}",
                    note=(
                        "No grid samples fell inside the obligation region; the obligation "
                        "still requires external discharge."
                    ),
                )
            )
            continue
        values = _evaluate_expression(_expression(obligation.expression), symbols, points)
        status, worst_index = _measured_status(values, obligation.comparison, float(obligation.rhs))
        statuses.append(
            ProofStatusSpec(
                id=f"{obligation.id}-region-grid",
                obligation_id=obligation.id,
                candidate_id=candidate_by_obligation.get(obligation.id),
                region_id=obligation.region_id,
                status=status,
                evaluation_kind="region-grid",
                sample_count=int(points.shape[0]),
                comparison=obligation.comparison,
                rhs=float(obligation.rhs),
                system=problem.system,
                variables=variables,
                state_axes=tuple(geometry.variable_to_state_axis[name] for name in variables),
                variable_to_state_axis=dict(geometry.variable_to_state_axis),
                source=f"regionGeometry:{geometry.region_id}",
                worst_value=float(values[worst_index]),
                worst_point=tuple(float(value) for value in points[worst_index]),
                note=_MEASURED_NOTE,
            )
        )
    return tuple(statuses)


def _certificate_series_record(
    *,
    problem: VerificationProblem,
    candidate: CandidateSpec,
    kind: str,
    label: str,
    series_name: str,
    obligation_ids: tuple[str, ...],
    obligations_by_id: Mapping[str, ObligationSpec],
) -> dict[str, Any]:
    return {
        "problemId": problem.id,
        "candidateId": candidate.id,
        "kind": kind,
        "label": label,
        "series": series_name,
        "obligationIds": list(obligation_ids),
        "comparisonBaselines": [
            {
                "obligationId": obligation_id,
                "comparison": obligations_by_id[obligation_id].comparison,
                "rhs": float(obligations_by_id[obligation_id].rhs),
                **(
                    {"regionId": obligations_by_id[obligation_id].region_id}
                    if obligations_by_id[obligation_id].region_id is not None
                    else {}
                ),
            }
            for obligation_id in obligation_ids
        ],
        "rigor": "measured",
        "note": _MEASURED_NOTE,
    }


def _matching_obligation_ids(
    candidate: CandidateSpec,
    obligations_by_id: Mapping[str, ObligationSpec],
    expression: sp.Expr,
) -> tuple[str, ...]:
    matches: list[str] = []
    for obligation_id in candidate.obligation_ids:
        obligation = obligations_by_id[obligation_id]
        if sp.simplify(_expression(obligation.expression) - expression) == 0:
            matches.append(obligation_id)
    return tuple(matches)


def _trajectory_problem_points(
    states: np.ndarray,
    *,
    state_names: tuple[str, ...],
    variable_names: tuple[str, ...],
    variable_to_state_axis: Mapping[str, str],
) -> np.ndarray:
    state_index = {name: index for index, name in enumerate(state_names)}
    columns = []
    for variable in variable_names:
        if variable not in variable_to_state_axis:
            raise ValueError(f"missing state-axis mapping for variable {variable!r}")
        axis = variable_to_state_axis[variable]
        if axis not in state_index:
            raise ValueError(f"mapped state axis {axis!r} is not in trajectory state names")
        columns.append(states[:, state_index[axis]])
    return np.column_stack(columns)


def _region_geometry_points(
    geometry: RegionGeometrySpec,
    *,
    variables: tuple[str, ...],
    inside_values: np.ndarray,
) -> np.ndarray:
    missing = set(variables) - set(geometry.plane_variables)
    if missing:
        raise ValueError(
            "region-grid proof statuses require geometry for every problem variable: "
            f"{sorted(missing)}"
        )
    x_grid, y_grid = np.meshgrid(
        np.asarray(geometry.x_values, dtype=float),
        np.asarray(geometry.y_values, dtype=float),
        indexing="xy",
    )
    coordinates = {
        geometry.plane_variables[0]: x_grid[inside_values],
        geometry.plane_variables[1]: y_grid[inside_values],
    }
    return np.column_stack([coordinates[name] for name in variables])


def _measured_status(
    values: np.ndarray,
    comparison: str,
    rhs: float,
) -> tuple[str, int]:
    if comparison in ("<=", "<"):
        worst_index = int(np.argmax(values - rhs))
        satisfied = values[worst_index] <= rhs if comparison == "<=" else values[worst_index] < rhs
    elif comparison in (">=", ">"):
        worst_index = int(np.argmin(values - rhs))
        satisfied = values[worst_index] >= rhs if comparison == ">=" else values[worst_index] > rhs
    else:
        raise ValueError("comparison must be one of <=, <, >=, >")
    return ("measured-holds" if bool(satisfied) else "measured-violated"), worst_index


def _evaluate_expression(
    expression: sp.Expr,
    variables: tuple[sp.Symbol, ...],
    points: np.ndarray,
) -> np.ndarray:
    unresolved = expression.free_symbols - set(variables)
    if unresolved:
        names = ", ".join(sorted(symbol.name for symbol in unresolved))
        raise ValueError(f"unresolved symbols: {names}")
    compiled = sp.lambdify(variables, expression, modules="numpy")
    values = compiled(*(points[:, index] for index in range(points.shape[1])))
    result = np.asarray(values, dtype=float)
    if result.shape == ():
        return np.full(points.shape[0], float(result))
    return result.reshape(points.shape[0])


def _symbols_for_names(
    names: tuple[str, ...],
    expressions: Sequence[sp.Expr],
) -> tuple[sp.Symbol, ...]:
    symbols_by_name = {
        symbol.name: symbol
        for expression in expressions
        for symbol in expression.free_symbols
    }
    return tuple(symbols_by_name.get(name, sp.Symbol(name)) for name in names)


def _problem_expressions(problem: VerificationProblem) -> tuple[sp.Expr, ...]:
    expressions: list[sp.Expr] = []
    for region in problem.regions:
        expressions.append(_expression(region.expression))
    for obligation in problem.obligations:
        expressions.append(_expression(obligation.expression))
    for candidate in problem.candidates:
        expressions.append(_expression(candidate.expression))
    if problem.dynamics is not None:
        expressions.extend(_expression(expression) for expression in problem.dynamics.rhs)
    return tuple(expressions)


def _expression(spec: ExpressionSpec) -> sp.Expr:
    return sp.sympify(spec.source)


def _candidate_by_obligation(problem: VerificationProblem) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for candidate in problem.candidates:
        for obligation_id in candidate.obligation_ids:
            mapping[obligation_id] = candidate.id
    return mapping


def _series_name(candidate_id: str, suffix: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", candidate_id).strip("_").lower()
    return f"certificate_{slug}_{suffix}"
