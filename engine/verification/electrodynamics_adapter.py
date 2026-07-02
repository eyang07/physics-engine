"""Verification-IR glue for covariant electromagnetic invariants."""

from __future__ import annotations

from dataclasses import replace
from typing import Any, Mapping, Sequence

import numpy as np
import sympy as sp

from engine.dynamics import FirstOrderSystem
from engine.verification.ir import (
    ObligationSpec,
    ParameterSpec,
    VariableSpec,
    VerificationProblem,
    problem_from_parts,
)
from engine.verification.measured import trajectory_obligation_proof_status
from engine.verification.sympy_codec import expression_spec
from engine.verification.system_codec import dynamics_spec_from_system

_SOURCE = "engine.verification.electrodynamics_adapter"
_DESCRIPTION = (
    "Measured deviation of a static electromagnetic invariant from its initial "
    "value along one rollout; exact conservation still requires external sound "
    "discharge."
)


def em_invariant_obligations(
    invariant_values: Mapping[str, float],
    *,
    tolerance: float,
) -> tuple[ObligationSpec, ...]:
    """Return external-required obligations for constant EM invariant residuals."""

    if tolerance <= 0.0:
        raise ValueError("tolerance must be positive")
    obligations: list[ObligationSpec] = []
    for name, value in invariant_values.items():
        residual = sp.Abs(sp.Float(float(value)) - sp.Float(float(value)))
        obligations.append(
            ObligationSpec(
                id=f"{name}-invariant",
                name=f"{name} electromagnetic invariant",
                expression=expression_spec(residual),
                comparison="<=",
                rhs=float(tolerance),
                description=_DESCRIPTION,
            )
        )
    return tuple(obligations)


def em_invariant_verification_problem(
    *,
    id: str,
    name: str,
    system_id: str,
    system: FirstOrderSystem,
    invariant_values: Mapping[str, float],
    time: Sequence[float],
    states: np.ndarray,
    tolerance: float = 1e-9,
    metadata: Mapping[str, Any] | None = None,
) -> VerificationProblem:
    """Build and measure EM-invariant obligations for a covariant EM rollout."""

    state_array = np.asarray(states, dtype=float)
    state_names = tuple(symbol.name for symbol in system.state)
    obligations = em_invariant_obligations(
        invariant_values,
        tolerance=tolerance,
    )
    variables = tuple(
        VariableSpec(name=symbol.name, latex=sp.latex(symbol)) for symbol in system.state
    )
    parameters = tuple(
        ParameterSpec(name=symbol.name, latex=sp.latex(symbol)) for symbol in system.parameters
    )
    problem = problem_from_parts(
        id=id,
        name=name,
        source=_SOURCE,
        system=system_id,
        variables=variables,
        parameters=parameters,
        regions=(),
        obligations=obligations,
        dynamics=dynamics_spec_from_system(system),
        metadata=metadata,
    )
    variable_to_state_axis = {name: name for name in state_names}
    proof_statuses = tuple(
        trajectory_obligation_proof_status(
            problem,
            obligation.id,
            time,
            state_array,
            state_names=state_names,
            variable_to_state_axis=variable_to_state_axis,
            source=f"{system_id}-rollout",
        )
        for obligation in obligations
    )
    return replace(problem, proof_statuses=proof_statuses)


__all__ = [
    "em_invariant_obligations",
    "em_invariant_verification_problem",
]
