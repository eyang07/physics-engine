"""Validation for manifest-to-verification viewer contracts."""

from __future__ import annotations

from typing import Sequence

from engine.export.manifest import SystemSpec
from engine.verification import VerificationProblem


def validate_viewer_verification_contract(
    systems: Sequence[SystemSpec],
    problems: Sequence[VerificationProblem],
) -> None:
    """Validate cross-links before writing viewer verification artifacts."""

    systems_by_id = {system.id: system for system in systems}
    if len(systems_by_id) != len(systems):
        raise ValueError("manifest system ids must be unique")

    problems_by_id = {problem.id: problem for problem in problems}
    if len(problems_by_id) != len(problems):
        raise ValueError("verification problem ids must be unique")

    for system in systems:
        for problem_id in system.verification_problems:
            if problem_id not in problems_by_id:
                raise ValueError(
                    f"manifest system {system.id!r} links unknown verification problem "
                    f"{problem_id!r}"
                )

    for problem in problems:
        if problem.system is None:
            raise ValueError(
                f"verification problem {problem.id!r} must name a manifest system"
            )
        if problem.system not in systems_by_id:
            raise ValueError(
                f"verification problem {problem.id!r} links unknown manifest system "
                f"{problem.system!r}"
            )

        system = systems_by_id[problem.system]
        if problem.id not in system.verification_problems:
            raise ValueError(
                f"verification problem {problem.id!r} is not linked back from "
                f"manifest system {system.id!r}"
            )

        _validate_region_geometry(system, problem)
        _validate_proof_statuses(system, problem)


def _validate_region_geometry(
    system: SystemSpec,
    problem: VerificationProblem,
) -> None:
    state_names = {state.name for state in system.state}
    problem_variable_names = {variable.name for variable in problem.variables}
    region_ids = {region.id for region in problem.regions}
    geometry_region_ids = {geometry.region_id for geometry in problem.region_geometry}

    if problem.regions and geometry_region_ids != region_ids:
        raise ValueError(
            f"verification problem {problem.id!r} region geometry must cover every region"
        )

    for geometry in problem.region_geometry:
        if geometry.projection not in system.projections:
            raise ValueError(
                f"region geometry {geometry.region_id!r} uses unknown projection "
                f"{geometry.projection!r} for manifest system {system.id!r}"
            )
        projection_axes = tuple(system.projections[geometry.projection])
        if tuple(geometry.state_axes) != projection_axes:
            raise ValueError(
                f"region geometry {geometry.region_id!r} state axes must match "
                f"manifest projection {geometry.projection!r}"
            )
        unknown_axes = set(geometry.state_axes) - state_names
        if unknown_axes:
            raise ValueError(
                f"region geometry {geometry.region_id!r} maps to unknown state axes: "
                f"{sorted(unknown_axes)}"
            )
        unknown_variables = set(geometry.plane_variables) - problem_variable_names
        if unknown_variables:
            raise ValueError(
                f"region geometry {geometry.region_id!r} uses unknown problem variables: "
                f"{sorted(unknown_variables)}"
            )


def _validate_proof_statuses(
    system: SystemSpec,
    problem: VerificationProblem,
) -> None:
    state_names = {state.name for state in system.state}
    problem_variable_names = {variable.name for variable in problem.variables}

    for status in problem.proof_statuses:
        if status.system is not None and status.system != system.id:
            raise ValueError(
                f"proof status {status.id!r} names system {status.system!r}, "
                f"expected {system.id!r}"
            )
        unknown_variables = set(status.variables) - problem_variable_names
        if unknown_variables:
            raise ValueError(
                f"proof status {status.id!r} uses unknown problem variables: "
                f"{sorted(unknown_variables)}"
            )
        unknown_axes = set(status.state_axes) - state_names
        if unknown_axes:
            raise ValueError(
                f"proof status {status.id!r} maps to unknown state axes: "
                f"{sorted(unknown_axes)}"
            )
