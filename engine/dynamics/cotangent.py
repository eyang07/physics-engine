from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

import sympy as sp

from engine.dynamics.first_order import FirstOrderSystem


@dataclass(frozen=True)
class CotangentHamiltonianSystem:
    """Hamiltonian flow on a cotangent chart.

    This is the natural backend shape for geometric-optics rays,
    bicharacteristics of principal symbols, and fixed-background geodesic
    reductions. For a symbol ``p(q, xi)``, the flow is
    ``q_dot = d p / d xi`` and ``xi_dot = -d p / d q``.
    """

    coordinates: tuple[sp.Symbol, ...]
    momenta: tuple[sp.Symbol, ...]
    symbol: sp.Expr
    parameters: tuple[sp.Symbol, ...] = ()
    time: sp.Symbol = sp.Symbol("s", real=True)

    def __post_init__(self) -> None:
        if len(self.coordinates) != len(self.momenta):
            raise ValueError("coordinates and momenta must have the same length")

    @property
    def state_symbols(self) -> tuple[sp.Symbol, ...]:
        return (*self.coordinates, *self.momenta)

    def rhs(self) -> tuple[sp.Expr, ...]:
        coordinate_rhs = tuple(sp.diff(self.symbol, momentum) for momentum in self.momenta)
        momentum_rhs = tuple(-sp.diff(self.symbol, coordinate) for coordinate in self.coordinates)
        return tuple(sp.simplify(component) for component in (*coordinate_rhs, *momentum_rhs))

    def first_order_system(self) -> FirstOrderSystem:
        return FirstOrderSystem(
            state=self.state_symbols,
            rhs=self.rhs(),
            parameters=self.parameters,
            time=self.time,
        )

    def numerical_rhs(
        self,
        substitutions: Mapping[sp.Symbol, float] | None = None,
    ):
        return self.first_order_system().numerical_rhs(substitutions)


__all__ = ["CotangentHamiltonianSystem"]
