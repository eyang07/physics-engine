"""Validation for the self-contained viewer verification contract.

The verification world is independent of the Systems manifest: a problem carries
its own variables, region geometry, and proof statuses on its own phase plane.
This module checks those internal cross-links before the viewer data is written;
it does not consult any manifest system.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from engine.verification import VerificationProblem


def validate_viewer_verification_problems(
    problems: Sequence[VerificationProblem],
) -> None:
    """Validate each verification problem's internal viewer contract."""

    problems_by_id = {problem.id: problem for problem in problems}
    if len(problems_by_id) != len(problems):
        raise ValueError("verification problem ids must be unique")

    for problem in problems:
        _validate_region_geometry(problem)
        _validate_proof_statuses(problem)


def validate_viewer_verification_index(
    payload: Mapping[str, Any],
    *,
    version: int,
) -> None:
    """Validate the viewer Verification catalog index shape."""

    if payload.get("version") != version:
        raise ValueError("viewer verification index version is invalid")
    problems = payload.get("problems")
    if not isinstance(problems, list):
        raise ValueError("viewer verification index problems must be a list")

    seen_ids: set[str] = set()
    for index, entry in enumerate(problems):
        if not isinstance(entry, Mapping):
            raise ValueError(f"viewer verification index problem {index} must be an object")
        problem_id = entry.get("id")
        if not isinstance(problem_id, str) or not problem_id:
            raise ValueError(f"viewer verification index problem {index} id is invalid")
        if problem_id in seen_ids:
            raise ValueError(f"duplicate viewer verification problem id: {problem_id}")
        seen_ids.add(problem_id)

        for key in ("name", "model", "status", "schemaVersion"):
            if not isinstance(entry.get(key), str) or not entry[key]:
                raise ValueError(
                    f"viewer verification index problem {problem_id} {key} is invalid"
                )

        data_path = entry.get("dataPath")
        if (
            not isinstance(data_path, str)
            or not data_path.startswith("/data/verification/")
            or not data_path.endswith(".json")
        ):
            raise ValueError(
                f"viewer verification index problem {problem_id} dataPath is invalid"
            )

        counts = entry.get("counts")
        if not isinstance(counts, Mapping):
            raise ValueError(
                f"viewer verification index problem {problem_id} counts are invalid"
            )
        expected_count_keys = {"regions", "obligations", "candidates"}
        if set(counts) != expected_count_keys:
            raise ValueError(
                f"viewer verification index problem {problem_id} counts are malformed"
            )
        for key in expected_count_keys:
            value = counts[key]
            if not isinstance(value, int) or value < 0:
                raise ValueError(
                    f"viewer verification index problem {problem_id} count {key} is invalid"
                )


def validate_viewer_verification_export(
    index_payload: Mapping[str, Any],
    problem_payloads_by_data_path: Mapping[str, Mapping[str, Any]],
    *,
    version: int,
) -> None:
    """Validate the viewer verification index against referenced problem files."""

    validate_viewer_verification_index(index_payload, version=version)
    problems = index_payload["problems"]
    for entry in problems:
        problem_id = entry["id"]
        data_path = entry["dataPath"]
        problem_payload = problem_payloads_by_data_path.get(data_path)
        if not isinstance(problem_payload, Mapping):
            raise ValueError(
                f"viewer verification index problem {problem_id} references "
                f"missing problem file {data_path}"
            )

        for key in ("id", "name", "schemaVersion"):
            if problem_payload.get(key) != entry[key]:
                raise ValueError(
                    f"viewer verification problem {problem_id} {key} does not "
                    "match index"
                )

        expected_counts = {
            "regions": _payload_list_count(problem_payload, "regions", problem_id),
            "obligations": _payload_list_count(
                problem_payload,
                "obligations",
                problem_id,
            ),
            "candidates": _payload_list_count(problem_payload, "candidates", problem_id),
        }
        if entry["counts"] != expected_counts:
            raise ValueError(
                f"viewer verification problem {problem_id} counts do not match payload"
            )

        trajectory = problem_payload.get("trajectory")
        if not isinstance(trajectory, Mapping):
            raise ValueError(
                f"viewer verification problem {problem_id} trajectory is invalid"
            )
        validate_viewer_verification_trajectory(trajectory, problem_id=problem_id)


def validate_viewer_verification_trajectory(
    payload: Mapping[str, Any],
    *,
    problem_id: str = "verification problem",
) -> None:
    """Validate the embedded viewer trajectory and certificate-series links."""

    time = payload.get("time")
    if not isinstance(time, list) or not time:
        raise ValueError(f"{problem_id} trajectory time must be a non-empty list")
    if any(not _is_number(value) for value in time):
        raise ValueError(f"{problem_id} trajectory time values must be numeric")

    state_names = payload.get("stateNames")
    if (
        not isinstance(state_names, list)
        or not state_names
        or any(not isinstance(name, str) or not name for name in state_names)
    ):
        raise ValueError(f"{problem_id} trajectory stateNames are invalid")

    states = payload.get("states")
    if not isinstance(states, list) or len(states) != len(time):
        raise ValueError(
            f"{problem_id} trajectory time and states must have matching lengths"
        )
    for index, row in enumerate(states):
        if not isinstance(row, list) or len(row) != len(state_names):
            raise ValueError(
                f"{problem_id} trajectory state row {index} must match stateNames"
            )
        if any(not _is_number(value) for value in row):
            raise ValueError(
                f"{problem_id} trajectory state row {index} values must be numeric"
            )

    series = payload.get("series")
    if not isinstance(series, Mapping):
        raise ValueError(f"{problem_id} trajectory series must be an object")
    for series_name, values in series.items():
        if not isinstance(series_name, str) or not series_name:
            raise ValueError(f"{problem_id} trajectory series names are invalid")
        if not isinstance(values, list) or len(values) != len(time):
            raise ValueError(
                f"{problem_id} trajectory series {series_name!r} must match time length"
            )
        if any(not _is_number(value) for value in values):
            raise ValueError(
                f"{problem_id} trajectory series {series_name!r} values must be numeric"
            )

    certificate_series = payload.get("certificateSeries")
    if not isinstance(certificate_series, list):
        raise ValueError(f"{problem_id} trajectory certificateSeries must be a list")
    for index, record in enumerate(certificate_series):
        if not isinstance(record, Mapping):
            raise ValueError(
                f"{problem_id} trajectory certificateSeries {index} must be an object"
            )
        series_name = record.get("series")
        if not isinstance(series_name, str) or not series_name:
            raise ValueError(
                f"{problem_id} trajectory certificateSeries {index} series is invalid"
            )
        if series_name not in series:
            raise ValueError(
                f"{problem_id} trajectory certificateSeries {index} references "
                f"missing series {series_name!r}"
            )


def _is_number(value: Any) -> bool:
    return isinstance(value, int | float) and not isinstance(value, bool)


def _payload_list_count(
    payload: Mapping[str, Any],
    key: str,
    problem_id: str,
) -> int:
    values = payload.get(key)
    if not isinstance(values, list):
        raise ValueError(f"viewer verification problem {problem_id} {key} is invalid")
    return len(values)


def _validate_region_geometry(problem: VerificationProblem) -> None:
    problem_variable_names = {variable.name for variable in problem.variables}
    region_ids = {region.id for region in problem.regions}
    geometry_region_ids = {geometry.region_id for geometry in problem.region_geometry}

    if problem.regions and geometry_region_ids != region_ids:
        raise ValueError(
            f"verification problem {problem.id!r} region geometry must cover every region"
        )

    for geometry in problem.region_geometry:
        unknown_variables = set(geometry.plane_variables) - problem_variable_names
        if unknown_variables:
            raise ValueError(
                f"region geometry {geometry.region_id!r} uses unknown problem variables: "
                f"{sorted(unknown_variables)}"
            )
        missing = set(geometry.plane_variables) - set(geometry.variable_to_state_axis)
        if missing:
            raise ValueError(
                f"region geometry {geometry.region_id!r} missing variable-to-state-axis "
                f"mappings: {sorted(missing)}"
            )
        expected_axes = tuple(
            geometry.variable_to_state_axis[name] for name in geometry.plane_variables
        )
        if tuple(geometry.state_axes) != expected_axes:
            raise ValueError(
                f"region geometry {geometry.region_id!r} state axes must match its "
                f"variable-to-state-axis mapping"
            )


def _validate_proof_statuses(problem: VerificationProblem) -> None:
    problem_variable_names = {variable.name for variable in problem.variables}

    for status in problem.proof_statuses:
        unknown_variables = set(status.variables) - problem_variable_names
        if unknown_variables:
            raise ValueError(
                f"proof status {status.id!r} uses unknown problem variables: "
                f"{sorted(unknown_variables)}"
            )
