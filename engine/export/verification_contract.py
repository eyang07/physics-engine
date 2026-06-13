"""Validation for the self-contained viewer verification contract.

The verification world is independent of the Systems manifest: a problem carries
its own variables, region geometry, and proof statuses on its own phase plane.
This module checks those internal cross-links before the viewer data is written;
it does not consult any manifest system.
"""

from __future__ import annotations

from typing import Sequence

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
