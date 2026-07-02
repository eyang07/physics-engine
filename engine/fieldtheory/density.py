"""Symbolic Lagrangian field densities.

This module only represents field-density structure. It computes exact symbolic
Euler-Lagrange expressions for one scalar field and does not provide a PDE
integrator or sampled time evolution.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import sympy as sp
from sympy.core.function import AppliedUndef


def _normalize_coordinates(coordinates: Sequence[sp.Symbol]) -> tuple[sp.Symbol, ...]:
    coords = tuple(coordinates)
    if not coords:
        raise ValueError("a field density needs at least one coordinate")
    if any(not isinstance(c, sp.Symbol) for c in coords):
        raise ValueError("coordinates must be sympy Symbols")
    if len(set(coords)) != len(coords):
        raise ValueError("coordinates must be distinct")
    return coords


def _normalize_parameters(
    parameters: Sequence[sp.Symbol],
    coordinates: tuple[sp.Symbol, ...],
) -> tuple[sp.Symbol, ...]:
    params = tuple(parameters)
    if any(not isinstance(p, sp.Symbol) for p in params):
        raise ValueError("parameters must be sympy Symbols")
    if len(set(params)) != len(params):
        raise ValueError("parameters must be distinct")
    overlap = set(params) & set(coordinates)
    if overlap:
        names = ", ".join(sorted(symbol.name for symbol in overlap))
        raise ValueError(f"parameters must not overlap coordinates: {names}")
    return params


def _normalize_field(field: sp.Expr, coordinates: tuple[sp.Symbol, ...]) -> AppliedUndef:
    scalar_field = sp.sympify(field)
    if not isinstance(scalar_field, AppliedUndef):
        raise ValueError("field must be an applied scalar function, e.g. phi(t, x)")
    if tuple(scalar_field.args) != coordinates:
        raise ValueError("field arguments must match coordinates")
    return scalar_field


def _check_density_symbols(
    density: sp.Expr,
    field: AppliedUndef,
    coordinates: tuple[sp.Symbol, ...],
    parameters: tuple[sp.Symbol, ...],
) -> None:
    allowed = set(coordinates) | set(parameters)
    unresolved = {symbol for symbol in density.free_symbols if symbol not in allowed}
    if unresolved:
        names = ", ".join(sorted(symbol.name for symbol in unresolved))
        raise ValueError(f"field density has unresolved symbols: {names}")

    extra_fields = density.atoms(AppliedUndef) - {field}
    if extra_fields:
        names = ", ".join(sorted(str(node) for node in extra_fields))
        raise ValueError(f"field density supports exactly one scalar field: {names}")


@dataclass(frozen=True)
class LagrangianFieldDensity:
    """A scalar field density ``L(phi, d_mu phi, x; params)``.

    The Euler-Lagrange convention matches ``LagrangianSystem``:
    ``sum_mu d_mu(dL/d(d_mu phi)) - dL/dphi``.
    """

    coordinates: tuple[sp.Symbol, ...]
    field: sp.Expr
    density: sp.Expr
    parameters: tuple[sp.Symbol, ...] = ()

    def __post_init__(self) -> None:
        coordinates = _normalize_coordinates(self.coordinates)
        parameters = _normalize_parameters(self.parameters, coordinates)
        field = _normalize_field(self.field, coordinates)
        density = sp.sympify(self.density)
        _check_density_symbols(density, field, coordinates, parameters)

        object.__setattr__(self, "coordinates", coordinates)
        object.__setattr__(self, "parameters", parameters)
        object.__setattr__(self, "field", field)
        object.__setattr__(self, "density", density)

    @property
    def dimension(self) -> int:
        return len(self.coordinates)

    @property
    def field_derivatives(self) -> tuple[sp.Derivative, ...]:
        return tuple(sp.diff(self.field, coordinate) for coordinate in self.coordinates)

    def canonical_momenta(self) -> tuple[sp.Expr, ...]:
        """Return ``dL/d(d_mu phi)`` in coordinate order."""

        return tuple(sp.diff(self.density, derivative) for derivative in self.field_derivatives)

    def euler_lagrange_expression(self) -> sp.Expr:
        """Return ``sum_mu d_mu(dL/d(d_mu phi)) - dL/dphi``."""

        divergence = sum(
            (
                sp.diff(momentum, coordinate)
                for momentum, coordinate in zip(
                    self.canonical_momenta(),
                    self.coordinates,
                    strict=True,
                )
            ),
            sp.Integer(0),
        )
        return sp.simplify(divergence - sp.diff(self.density, self.field))

    def euler_lagrange_equation(self) -> sp.Eq:
        return sp.Eq(self.euler_lagrange_expression(), 0)
