"""Electromagnetic four-potential and exterior derivative."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import sympy as sp


def _normalize_coordinates(coordinates: Sequence[sp.Symbol]) -> tuple[sp.Symbol, ...]:
    coords = tuple(coordinates)
    if len(coords) < 2:
        raise ValueError("a four-potential needs at least two spacetime coordinates")
    if any(not isinstance(coordinate, sp.Symbol) for coordinate in coords):
        raise ValueError("coordinates must be sympy Symbols")
    if len(set(coords)) != len(coords):
        raise ValueError("coordinates must be distinct")
    return coords


def _normalize_components(
    components: Sequence[object],
    dimension: int,
) -> tuple[sp.Expr, ...]:
    values = tuple(sp.sympify(component) for component in components)
    if len(values) != dimension:
        raise ValueError("a four-potential needs one component per coordinate")
    return values


def _check_free_symbols(
    expressions: Sequence[sp.Expr],
    coordinates: tuple[sp.Symbol, ...],
    parameters: tuple[sp.Symbol, ...],
) -> None:
    allowed = set(coordinates) | set(parameters)
    free: set[sp.Symbol] = set()
    for expression in expressions:
        free |= expression.free_symbols
    unresolved = free - allowed
    if unresolved:
        names = ", ".join(sorted(symbol.name for symbol in unresolved))
        raise ValueError(f"four-potential expression has unresolved symbols: {names}")


@dataclass(frozen=True)
class FourPotential:
    """Covariant electromagnetic potential ``A_mu(x)``.

    The field strength is the exterior derivative
    ``F_mu_nu = partial_mu A_nu - partial_nu A_mu``. Gauge transforms use
    ``A_mu -> A_mu + partial_mu chi`` and therefore leave ``F`` unchanged by
    equality of mixed partial derivatives.
    """

    coordinates: tuple[sp.Symbol, ...]
    components: tuple[sp.Expr, ...]
    parameters: tuple[sp.Symbol, ...] = ()

    def __post_init__(self) -> None:
        coordinates = _normalize_coordinates(self.coordinates)
        parameters = tuple(self.parameters)
        components = _normalize_components(self.components, len(coordinates))
        if any(not isinstance(parameter, sp.Symbol) for parameter in parameters):
            raise ValueError("parameters must be sympy Symbols")
        _check_free_symbols(components, coordinates, parameters)

        object.__setattr__(self, "coordinates", coordinates)
        object.__setattr__(self, "components", components)
        object.__setattr__(self, "parameters", parameters)

    @property
    def dimension(self) -> int:
        return len(self.coordinates)

    def field_strength(self) -> sp.Matrix:
        """Return the covariant Faraday tensor ``F_mu_nu = dA``."""

        return sp.Matrix(
            self.dimension,
            self.dimension,
            lambda mu, nu: sp.simplify(
                sp.diff(self.components[nu], self.coordinates[mu])
                - sp.diff(self.components[mu], self.coordinates[nu])
            ),
        )

    def gauge_transform(self, chi: object) -> "FourPotential":
        """Return ``A_mu + partial_mu chi`` for symbolic gauge function ``chi``."""

        gauge = sp.sympify(chi)
        _check_free_symbols((gauge,), self.coordinates, self.parameters)
        return FourPotential(
            coordinates=self.coordinates,
            components=tuple(
                sp.simplify(component + sp.diff(gauge, coordinate))
                for component, coordinate in zip(self.components, self.coordinates)
            ),
            parameters=self.parameters,
        )

    def homogeneous_maxwell_residuals(self) -> tuple[sp.Expr, ...]:
        """Return cyclic residuals ``partial_[lambda F_mu nu]`` for all triples."""

        field = self.field_strength()
        residuals: list[sp.Expr] = []
        for lambda_index in range(self.dimension):
            for mu in range(lambda_index + 1, self.dimension):
                for nu in range(mu + 1, self.dimension):
                    residuals.append(
                        sp.simplify(
                            sp.diff(field[mu, nu], self.coordinates[lambda_index])
                            + sp.diff(field[nu, lambda_index], self.coordinates[mu])
                            + sp.diff(field[lambda_index, mu], self.coordinates[nu])
                        )
                    )
        return tuple(residuals)


def four_potential(
    coordinates: Sequence[sp.Symbol],
    components: Sequence[object],
    parameters: Sequence[sp.Symbol] = (),
) -> FourPotential:
    """Build a :class:`FourPotential` from covariant components."""

    return FourPotential(
        coordinates=tuple(coordinates),
        components=tuple(sp.sympify(component) for component in components),
        parameters=tuple(parameters),
    )


__all__ = [
    "FourPotential",
    "four_potential",
]
