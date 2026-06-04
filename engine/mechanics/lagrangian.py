from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

import numpy as np
import sympy as sp

from engine.mechanics.coordinates import acceleration_symbol, velocity_symbol


def total_time_derivative(
    expr: sp.Expr,
    coordinates: Sequence[sp.Symbol],
    velocities: Sequence[sp.Symbol],
    time: sp.Symbol,
    accelerations: Sequence[sp.Symbol] | None = None,
) -> sp.Expr:
    """Compute D_t(expr) using q, qdot, and qddot as independent symbols."""

    result = sp.diff(expr, time)
    for q, v in zip(coordinates, velocities, strict=True):
        result += sp.diff(expr, q) * v

    if accelerations is not None:
        for v, a in zip(velocities, accelerations, strict=True):
            result += sp.diff(expr, v) * a

    return sp.simplify(result)


@dataclass(frozen=True)
class LagrangianSystem:
    """A finite-dimensional system defined by a Lagrangian L(q, qdot, t)."""

    coordinates: tuple[sp.Symbol, ...]
    lagrangian: sp.Expr
    time: sp.Symbol = sp.Symbol("t", real=True)
    velocities: tuple[sp.Symbol, ...] | None = None

    def __post_init__(self) -> None:
        if self.velocities is not None and len(self.velocities) != len(self.coordinates):
            raise ValueError("coordinates and velocities must have the same length")

    @property
    def q(self) -> tuple[sp.Symbol, ...]:
        return self.coordinates

    @property
    def qdot(self) -> tuple[sp.Symbol, ...]:
        if self.velocities is None:
            return tuple(velocity_symbol(q) for q in self.coordinates)
        return self.velocities

    @property
    def qddot(self) -> tuple[sp.Symbol, ...]:
        return tuple(acceleration_symbol(q) for q in self.coordinates)

    def generalized_momenta(self) -> tuple[sp.Expr, ...]:
        return tuple(sp.diff(self.lagrangian, v) for v in self.qdot)

    def euler_lagrange_expressions(self) -> tuple[sp.Expr, ...]:
        """Return D_t(dL/dqdot_i) - dL/dq_i for each coordinate."""

        momenta = self.generalized_momenta()
        return tuple(
            sp.simplify(
                total_time_derivative(
                    p,
                    self.q,
                    self.qdot,
                    self.time,
                    self.qddot,
                )
                - sp.diff(self.lagrangian, q)
            )
            for q, p in zip(self.q, momenta, strict=True)
        )

    def euler_lagrange_equations(self) -> tuple[sp.Eq, ...]:
        return tuple(sp.Eq(expr, 0) for expr in self.euler_lagrange_expressions())

    def mass_matrix_and_forcing(self) -> tuple[sp.Matrix, sp.Matrix]:
        """Return M and f such that M(q, qdot, t) qddot = f(q, qdot, t)."""

        expressions = sp.Matrix(self.euler_lagrange_expressions())
        accelerations = self.qddot
        mass_matrix = expressions.jacobian(accelerations)
        without_acceleration = expressions.subs({a: 0 for a in accelerations})
        forcing = -without_acceleration
        return sp.simplify(mass_matrix), sp.simplify(forcing)

    def acceleration_expressions(self) -> tuple[sp.Expr, ...]:
        mass_matrix, forcing = self.mass_matrix_and_forcing()
        accelerations = mass_matrix.LUsolve(forcing)
        return tuple(sp.simplify(expr) for expr in accelerations)

    def first_order_expressions(self) -> tuple[sp.Expr, ...]:
        """Return [qdot, qddot(q, qdot, t)] for numerical integration."""

        return self.qdot + self.acceleration_expressions()

    def energy(self) -> sp.Expr:
        """Return the Lagrangian energy E = sum qdot_i dL/dqdot_i - L."""

        return sp.simplify(
            sum(v * p for v, p in zip(self.qdot, self.generalized_momenta(), strict=True))
            - self.lagrangian
        )

    def numerical_rhs(
        self,
        substitutions: Mapping[sp.Symbol, float] | None = None,
    ):
        """Build f(t, y) for y = [q_0, ..., q_n, qdot_0, ..., qdot_n]."""

        substitutions = substitutions or {}
        expressions = [expr.subs(substitutions) for expr in self.first_order_expressions()]
        free_symbols = set().union(*(expr.free_symbols for expr in expressions))
        allowed = {self.time, *self.q, *self.qdot}
        unresolved = free_symbols - allowed
        if unresolved:
            names = ", ".join(sorted(symbol.name for symbol in unresolved))
            raise ValueError(f"unresolved symbols in numerical RHS: {names}")

        args = (self.time, *self.q, *self.qdot)
        compiled = sp.lambdify(args, expressions, modules="numpy")

        def rhs(t: float, state: Sequence[float]) -> np.ndarray:
            values = compiled(t, *state)
            return np.asarray(values, dtype=float)

        return rhs

