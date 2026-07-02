"""Verification-IR glue for relativistic mass-shell/four-momentum claims.

Wires the mass-shell identity and four-momentum conservation for a
proper-time-parameterized relativistic worldline into the backend-agnostic
verification-problem IR (:mod:`engine.verification.ir`). Both claims are
built as :class:`~engine.verification.ir.ObligationSpec` records — always
``rigor="external-required"`` — and paired with **measured**
:class:`~engine.verification.ir.ProofStatusSpec` records sampled from an
actual rollout via :func:`engine.verification.measured.trajectory_obligation_proof_status`.
Nothing here attempts, records, or claims proof discharge; a clean measured
status is sampled evidence that a stated numerical tolerance held along one
rollout, never a proof of the underlying exact identity.
"""

from __future__ import annotations

from dataclasses import replace
from typing import Any, Mapping, Sequence

import numpy as np
import sympy as sp

from engine.dynamics.first_order import FirstOrderSystem
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

_SOURCE = "engine.verification.relativity_adapter"
_MASS_SHELL_DESCRIPTION = (
    "Measured deviation of the relativistic mass-shell identity from zero "
    "along the rollout; external sound discharge is still required for the "
    "exact identity."
)
_MOMENTUM_DESCRIPTION = (
    "Measured deviation of four-momentum component {name} from its initial "
    "(conserved) value along the rollout; external sound discharge is still "
    "required for exact conservation."
)


def mass_shell_conservation_obligation(
    mass_shell_expression: sp.Expr,
    *,
    tolerance: float,
    id: str = "mass-shell-conservation",
    name: str = "Mass-shell conservation",
) -> ObligationSpec:
    """Bound ``|mass_shell_expression|`` by a stated numerical ``tolerance``.

    ``mass_shell_expression`` should vanish identically for the exact
    dynamics (e.g. ``p^mu p_mu + m^2 c^2`` or the equivalent four-velocity
    norm form); the obligation is the measurable claim that a rollout stays
    within ``tolerance`` of that identity, not the identity itself.
    """

    if tolerance <= 0:
        raise ValueError("tolerance must be positive")
    residual = sp.Abs(sp.sympify(mass_shell_expression))
    return ObligationSpec(
        id=id,
        name=name,
        expression=expression_spec(residual),
        comparison="<=",
        rhs=float(tolerance),
        description=_MASS_SHELL_DESCRIPTION,
    )


def four_momentum_conservation_obligations(
    momentum_symbols: Sequence[sp.Symbol],
    initial_momentum: Sequence[float],
    *,
    tolerance: float,
) -> tuple[ObligationSpec, ...]:
    """Bound each ``momentum_symbols[i]`` near its ``initial_momentum[i]``.

    For a free worldline each four-momentum component is exactly constant;
    the obligation is the measurable claim that a rollout's component stays
    within ``tolerance`` of its initial value.
    """

    if len(momentum_symbols) != len(initial_momentum):
        raise ValueError("momentum_symbols and initial_momentum must have the same length")
    if not momentum_symbols:
        raise ValueError("at least one momentum symbol is required")
    if tolerance <= 0:
        raise ValueError("tolerance must be positive")

    obligations = []
    for symbol, initial_value in zip(momentum_symbols, initial_momentum, strict=True):
        residual = sp.Abs(symbol - sp.Float(float(initial_value)))
        obligations.append(
            ObligationSpec(
                id=f"four-momentum-{symbol.name}-conservation",
                name=f"Four-momentum component {symbol.name} conservation",
                expression=expression_spec(residual),
                comparison="<=",
                rhs=float(tolerance),
                description=_MOMENTUM_DESCRIPTION.format(name=symbol.name),
            )
        )
    return tuple(obligations)


def worldline_conservation_verification_problem(
    *,
    id: str,
    name: str,
    system_id: str,
    system: FirstOrderSystem,
    mass_shell_expression: sp.Expr,
    momentum_symbols: Sequence[sp.Symbol],
    time: Sequence[float],
    states: np.ndarray,
    tolerance: float = 1e-6,
    metadata: Mapping[str, Any] | None = None,
) -> VerificationProblem:
    """Build and measure a mass-shell/four-momentum verification problem.

    ``momentum_symbols`` must be a subset of ``system.state``; their initial
    values are read from ``states[0]``. The returned problem carries both the
    ``external-required`` obligations and their measured proof statuses
    sampled from ``(time, states)`` -- it never marks a claim certified.
    """

    state_array = np.asarray(states, dtype=float)
    state_names = tuple(symbol.name for symbol in system.state)
    momentum_indices = [system.state.index(symbol) for symbol in momentum_symbols]
    initial_momentum = [float(state_array[0, index]) for index in momentum_indices]

    obligations = (
        mass_shell_conservation_obligation(mass_shell_expression, tolerance=tolerance),
        *four_momentum_conservation_obligations(
            momentum_symbols, initial_momentum, tolerance=tolerance
        ),
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
    "four_momentum_conservation_obligations",
    "mass_shell_conservation_obligation",
    "worldline_conservation_verification_problem",
]
