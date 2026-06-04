from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import sympy as sp

from engine.mechanics.lagrangian import LagrangianSystem, total_time_derivative


@dataclass(frozen=True)
class HolonomicConstraint:
    """A constraint phi(q, t) = 0."""

    expression: sp.Expr

    def velocity_level(
        self,
        coordinates: Sequence[sp.Symbol],
        velocities: Sequence[sp.Symbol],
        time: sp.Symbol,
    ) -> sp.Expr:
        return total_time_derivative(self.expression, coordinates, velocities, time)

    def acceleration_level(
        self,
        coordinates: Sequence[sp.Symbol],
        velocities: Sequence[sp.Symbol],
        accelerations: Sequence[sp.Symbol],
        time: sp.Symbol,
    ) -> sp.Expr:
        velocity_constraint = self.velocity_level(coordinates, velocities, time)
        return total_time_derivative(
            velocity_constraint,
            coordinates,
            velocities,
            time,
            accelerations,
        )


@dataclass(frozen=True)
class ConstrainedEquations:
    equations: tuple[sp.Eq, ...]
    multipliers: tuple[sp.Symbol, ...]
    acceleration_constraints: tuple[sp.Eq, ...]


def constrained_euler_lagrange_equations(
    system: LagrangianSystem,
    constraints: Sequence[HolonomicConstraint],
    *,
    multiplier_prefix: str = "lambda",
) -> ConstrainedEquations:
    """Return Lagrange multiplier equations for holonomic constraints.

    The sign convention is
    D_t(dL/dqdot_i) - dL/dq_i - sum_a lambda_a dphi_a/dq_i = 0.
    """

    multipliers = tuple(
        sp.Symbol(f"{multiplier_prefix}_{index}", real=True)
        for index, _constraint in enumerate(constraints)
    )

    expressions = []
    for q, expression in zip(system.q, system.euler_lagrange_expressions(), strict=True):
        constraint_force = sum(
            lam * sp.diff(constraint.expression, q)
            for lam, constraint in zip(multipliers, constraints, strict=True)
        )
        expressions.append(sp.simplify(expression - constraint_force))

    acceleration_constraints = tuple(
        sp.Eq(
            sp.simplify(
                constraint.acceleration_level(
                    system.q,
                    system.qdot,
                    system.qddot,
                    system.time,
                )
            ),
            0,
        )
        for constraint in constraints
    )

    return ConstrainedEquations(
        equations=tuple(sp.Eq(expr, 0) for expr in expressions),
        multipliers=multipliers,
        acceleration_constraints=acceleration_constraints,
    )

