from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import sympy as sp


def time_symbol(name: str = "t") -> sp.Symbol:
    return sp.Symbol(name, real=True)


def coordinate_symbols(names: str | Iterable[str]) -> tuple[sp.Symbol, ...]:
    if isinstance(names, str):
        names = names.replace(",", " ").split()
    return tuple(sp.Symbol(name, real=True) for name in names)


def velocity_symbol(coordinate: sp.Symbol) -> sp.Symbol:
    return sp.Symbol(f"{coordinate.name}_dot", real=True)


def acceleration_symbol(coordinate: sp.Symbol) -> sp.Symbol:
    return sp.Symbol(f"{coordinate.name}_ddot", real=True)


def momentum_symbol(coordinate: sp.Symbol) -> sp.Symbol:
    return sp.Symbol(f"p_{coordinate.name}", real=True)


@dataclass(frozen=True)
class CoordinateChart:
    """A local coordinate chart with independent velocity symbols.

    The engine represents q, qdot, and qddot as independent symbolic variables.
    This keeps derivations inspectable before any numerical function is built.
    """

    coordinates: tuple[sp.Symbol, ...]
    time: sp.Symbol = sp.Symbol("t", real=True)

    @classmethod
    def from_names(
        cls, names: str | Iterable[str], time: str | sp.Symbol = "t"
    ) -> "CoordinateChart":
        t = sp.Symbol(time, real=True) if isinstance(time, str) else time
        return cls(coordinate_symbols(names), t)

    @property
    def velocities(self) -> tuple[sp.Symbol, ...]:
        return tuple(velocity_symbol(q) for q in self.coordinates)

    @property
    def accelerations(self) -> tuple[sp.Symbol, ...]:
        return tuple(acceleration_symbol(q) for q in self.coordinates)

    @property
    def state_symbols(self) -> tuple[sp.Symbol, ...]:
        return self.coordinates + self.velocities

    def tangent_bundle(self) -> "TangentBundleChart":
        return TangentBundleChart(
            base=self,
            velocities=self.velocities,
            accelerations=self.accelerations,
        )

    def cotangent_bundle(self) -> "CotangentBundleChart":
        return CotangentBundleChart(
            base=self,
            momenta=tuple(momentum_symbol(q) for q in self.coordinates),
        )


@dataclass(frozen=True)
class TangentBundleChart:
    """The induced chart (q, qdot) on the tangent bundle TQ."""

    base: CoordinateChart
    velocities: tuple[sp.Symbol, ...]
    accelerations: tuple[sp.Symbol, ...]

    def __post_init__(self) -> None:
        if len(self.velocities) != len(self.base.coordinates):
            raise ValueError("velocities must match base coordinates")
        if len(self.accelerations) != len(self.base.coordinates):
            raise ValueError("accelerations must match base coordinates")

    @property
    def coordinates(self) -> tuple[sp.Symbol, ...]:
        return self.base.coordinates

    @property
    def time(self) -> sp.Symbol:
        return self.base.time

    @property
    def state_symbols(self) -> tuple[sp.Symbol, ...]:
        return self.coordinates + self.velocities


@dataclass(frozen=True)
class CotangentBundleChart:
    """The induced chart (q, p) on the cotangent bundle T*Q."""

    base: CoordinateChart
    momenta: tuple[sp.Symbol, ...]

    def __post_init__(self) -> None:
        if len(self.momenta) != len(self.base.coordinates):
            raise ValueError("momenta must match base coordinates")

    @property
    def coordinates(self) -> tuple[sp.Symbol, ...]:
        return self.base.coordinates

    @property
    def time(self) -> sp.Symbol:
        return self.base.time

    @property
    def state_symbols(self) -> tuple[sp.Symbol, ...]:
        return self.coordinates + self.momenta
