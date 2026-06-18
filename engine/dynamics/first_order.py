from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

import numpy as np
import sympy as sp


@dataclass(frozen=True)
class FirstOrderSystem:
    """A finite-dimensional first-order system dx/dt = f(t, x; params)."""

    state: tuple[sp.Symbol, ...]
    rhs: tuple[sp.Expr, ...]
    parameters: tuple[sp.Symbol, ...] = ()
    time: sp.Symbol = sp.Symbol("t", real=True)
    simplify_derivatives: bool = True

    def __post_init__(self) -> None:
        if len(self.state) != len(self.rhs):
            raise ValueError("state and rhs must have the same length")

    @property
    def state_symbols(self) -> tuple[sp.Symbol, ...]:
        return self.state

    def jacobian(self) -> sp.Matrix:
        jacobian = sp.Matrix(self.rhs).jacobian(self.state)
        return sp.simplify(jacobian) if self.simplify_derivatives else jacobian

    def divergence(self) -> sp.Expr:
        divergence = sum(
            sp.diff(component, symbol)
            for component, symbol in zip(self.rhs, self.state, strict=True)
        )
        return sp.simplify(divergence) if self.simplify_derivatives else divergence

    def fixed_points(
        self,
        substitutions: Mapping[sp.Symbol, float] | None = None,
    ) -> list[dict[sp.Symbol, sp.Expr]]:
        expressions = [expr.subs(substitutions or {}) for expr in self.rhs]
        return sp.solve(expressions, self.state, dict=True)

    def linearization(
        self,
        point: Mapping[sp.Symbol, sp.Expr | float],
        substitutions: Mapping[sp.Symbol, float] | None = None,
    ) -> sp.Matrix:
        return sp.simplify(self.jacobian().subs(substitutions or {}).subs(point))

    def eigenvalues_at(
        self,
        point: Mapping[sp.Symbol, sp.Expr | float],
        substitutions: Mapping[sp.Symbol, float] | None = None,
    ) -> dict[sp.Expr, int]:
        return self.linearization(point, substitutions).eigenvals()

    def numerical_rhs(
        self,
        substitutions: Mapping[sp.Symbol, float] | None = None,
    ):
        substitutions = substitutions or {}
        expressions = [expr.subs(substitutions) for expr in self.rhs]
        free_symbols = set().union(*(expr.free_symbols for expr in expressions))
        allowed = {self.time, *self.state}
        unresolved = free_symbols - allowed
        if unresolved:
            names = ", ".join(sorted(symbol.name for symbol in unresolved))
            raise ValueError(f"unresolved symbols in numerical RHS: {names}")

        args = (self.time, *self.state)
        compiled = sp.lambdify(args, expressions, modules="numpy")

        def rhs(t: float, state: Sequence[float]) -> np.ndarray:
            values = compiled(t, *state)
            return np.asarray(values, dtype=float)

        return rhs
