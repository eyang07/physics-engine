from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

import numpy as np
import sympy as sp

from engine.mechanics.coordinates import momentum_symbol
from engine.mechanics.lagrangian import LagrangianSystem
from engine.mechanics.poisson import poisson_bracket, time_evolution
from engine.mechanics.symplectic import hamiltonian_vector_field, liouville_divergence


@dataclass(frozen=True)
class HamiltonianSystem:
    """A finite-dimensional Hamiltonian system on a cotangent chart T*Q."""

    coordinates: tuple[sp.Symbol, ...]
    momenta: tuple[sp.Symbol, ...]
    hamiltonian: sp.Expr
    time: sp.Symbol = sp.Symbol("t", real=True)

    def __post_init__(self) -> None:
        if len(self.coordinates) != len(self.momenta):
            raise ValueError("coordinates and momenta must have the same length")

    @property
    def q(self) -> tuple[sp.Symbol, ...]:
        return self.coordinates

    @property
    def p(self) -> tuple[sp.Symbol, ...]:
        return self.momenta

    @property
    def state_symbols(self) -> tuple[sp.Symbol, ...]:
        return self.q + self.p

    def hamilton_equations(self) -> tuple[sp.Expr, ...]:
        """Return [dq_i/dt, dp_i/dt] from Hamilton's equations."""

        return tuple(hamiltonian_vector_field(self.hamiltonian, self.q, self.p))

    def poisson_bracket(self, f: sp.Expr, g: sp.Expr) -> sp.Expr:
        return poisson_bracket(f, g, self.q, self.p)

    def time_evolution(self, observable: sp.Expr) -> sp.Expr:
        return time_evolution(
            observable,
            self.hamiltonian,
            self.q,
            self.p,
            time=self.time,
        )

    def liouville_divergence(self) -> sp.Expr:
        return liouville_divergence(self.hamiltonian, self.q, self.p)

    def hamilton_equation_equalities(self) -> tuple[sp.Eq, ...]:
        qdot = tuple(sp.Symbol(f"{q.name}_dot", real=True) for q in self.q)
        pdot = tuple(sp.Symbol(f"{p.name}_dot", real=True) for p in self.p)
        return tuple(
            sp.Eq(symbol, expression)
            for symbol, expression in zip(qdot + pdot, self.hamilton_equations(), strict=True)
        )

    def numerical_rhs(
        self,
        substitutions: Mapping[sp.Symbol, float] | None = None,
    ):
        """Build f(t, y) for y = [q_0, ..., q_n, p_0, ..., p_n]."""

        substitutions = substitutions or {}
        expressions = [expr.subs(substitutions) for expr in self.hamilton_equations()]
        free_symbols = set().union(*(expr.free_symbols for expr in expressions))
        allowed = {self.time, *self.q, *self.p}
        unresolved = free_symbols - allowed
        if unresolved:
            names = ", ".join(sorted(symbol.name for symbol in unresolved))
            raise ValueError(f"unresolved symbols in numerical RHS: {names}")

        args = (self.time, *self.q, *self.p)
        compiled = sp.lambdify(args, expressions, modules="numpy")

        def rhs(t: float, state: Sequence[float]) -> np.ndarray:
            values = compiled(t, *state)
            return np.asarray(values, dtype=float)

        return rhs


@dataclass(frozen=True)
class LegendreTransform:
    """The fiber derivative FL: TQ -> T*Q for a regular Lagrangian."""

    momentum_definitions: Mapping[sp.Symbol, sp.Expr]
    momentum_to_velocity: Mapping[sp.Symbol, sp.Expr]
    hamiltonian_system: HamiltonianSystem


def legendre_transform(
    lagrangian_system: LagrangianSystem,
    *,
    momenta: Sequence[sp.Symbol] | None = None,
) -> LegendreTransform:
    """Convert a regular Lagrangian system into a Hamiltonian system.

    The transform solves p_i = partial L / partial qdot_i for qdot_i, then
    substitutes those velocities into H = sum_i p_i qdot_i - L.
    """

    q = lagrangian_system.q
    qdot = lagrangian_system.qdot
    p = tuple(momenta or tuple(momentum_symbol(q_i) for q_i in q))

    momentum_definitions = dict(zip(p, lagrangian_system.generalized_momenta(), strict=True))
    equations = [
        sp.Eq(p_i, momentum_expr)
        for p_i, momentum_expr in momentum_definitions.items()
    ]
    solutions = sp.solve(equations, qdot, dict=True, simplify=True)
    if len(solutions) != 1:
        raise ValueError(
            "Legendre transform requires a unique velocity solution; "
            f"found {len(solutions)}"
        )

    momentum_to_velocity = {
        velocity: sp.simplify(solution)
        for velocity, solution in solutions[0].items()
    }
    if set(momentum_to_velocity) != set(qdot):
        missing = set(qdot) - set(momentum_to_velocity)
        names = ", ".join(sorted(symbol.name for symbol in missing))
        raise ValueError(f"Legendre transform did not solve for velocities: {names}")

    hamiltonian = sum(
        p_i * v_i for p_i, v_i in zip(p, qdot, strict=True)
    ) - lagrangian_system.lagrangian
    hamiltonian = sp.simplify(hamiltonian.subs(momentum_to_velocity))

    return LegendreTransform(
        momentum_definitions=momentum_definitions,
        momentum_to_velocity=momentum_to_velocity,
        hamiltonian_system=HamiltonianSystem(
            coordinates=q,
            momenta=p,
            hamiltonian=hamiltonian,
            time=lagrangian_system.time,
        ),
    )
