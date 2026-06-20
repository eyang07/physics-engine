"""Symbolic scalar and vector fields over spatial coordinates.

A field pairs spatial coordinate symbols with a symbolic expression (or vector of
expressions) and optional parameters. Differential operators (gradient,
divergence, curl, Laplacian) are exact symbolic derivatives, and deterministic
grid sampling lambdifies the expression for export to the viewer. The fields are
the source of mathematical truth; sampling is a derived rendering aid.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

import numpy as np
import sympy as sp


def _normalize_coordinates(coordinates: Sequence[sp.Symbol]) -> tuple[sp.Symbol, ...]:
    coords = tuple(coordinates)
    if not coords:
        raise ValueError("a field needs at least one spatial coordinate")
    if any(not isinstance(c, sp.Symbol) for c in coords):
        raise ValueError("coordinates must be sympy Symbols")
    if len(set(coords)) != len(coords):
        raise ValueError("coordinates must be distinct")
    return coords


def _check_free_symbols(
    expressions: Sequence[sp.Expr],
    coordinates: tuple[sp.Symbol, ...],
    parameters: tuple[sp.Symbol, ...],
) -> None:
    allowed = set(coordinates) | set(parameters)
    free: set[sp.Symbol] = set()
    for expr in expressions:
        free |= expr.free_symbols
    unresolved = {symbol for symbol in free if symbol not in allowed}
    if unresolved:
        names = ", ".join(sorted(symbol.name for symbol in unresolved))
        raise ValueError(f"field expression has unresolved symbols: {names}")


def _sample_expression(
    expression: sp.Expr,
    coordinates: tuple[sp.Symbol, ...],
    parameters: tuple[sp.Symbol, ...],
    axes: Sequence[Sequence[float]],
    parameter_values: Mapping[str, float] | None,
) -> np.ndarray:
    axis_arrays = [np.asarray(axis, dtype=float) for axis in axes]
    if len(axis_arrays) != len(coordinates):
        raise ValueError("one axis is required per coordinate")
    values = parameter_values or {}
    missing = {p.name for p in parameters} - set(values)
    if missing:
        raise ValueError(f"missing parameter values: {', '.join(sorted(missing))}")

    mesh = np.meshgrid(*axis_arrays, indexing="ij")
    grid_shape = mesh[0].shape
    func = sp.lambdify((*coordinates, *parameters), expression, modules="numpy")
    parameter_args = [float(values[p.name]) for p in parameters]
    result = func(*mesh, *parameter_args)
    # A constant expression lambdifies to a scalar; broadcast to the grid shape.
    return np.broadcast_to(np.asarray(result, dtype=float), grid_shape).copy()


@dataclass(frozen=True)
class ScalarField:
    """A scalar field ``f(x; params)`` over spatial coordinates."""

    coordinates: tuple[sp.Symbol, ...]
    expression: sp.Expr
    parameters: tuple[sp.Symbol, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "coordinates", _normalize_coordinates(self.coordinates))
        object.__setattr__(self, "expression", sp.sympify(self.expression))
        object.__setattr__(self, "parameters", tuple(self.parameters))
        _check_free_symbols((self.expression,), self.coordinates, self.parameters)

    @property
    def dimension(self) -> int:
        return len(self.coordinates)

    def gradient(self) -> "VectorField":
        components = tuple(sp.diff(self.expression, c) for c in self.coordinates)
        return VectorField(self.coordinates, components, self.parameters)

    def laplacian(self) -> "ScalarField":
        expression = sp.expand(
            sum((sp.diff(self.expression, c, 2) for c in self.coordinates), sp.Integer(0))
        )
        return ScalarField(self.coordinates, expression, self.parameters)

    def sample(
        self,
        axes: Sequence[Sequence[float]],
        parameter_values: Mapping[str, float] | None = None,
    ) -> np.ndarray:
        """Sample the field on the tensor grid spanned by ``axes`` (indexing='ij')."""

        return _sample_expression(
            self.expression, self.coordinates, self.parameters, axes, parameter_values
        )


@dataclass(frozen=True)
class VectorField:
    """A vector field with one component expression per spatial coordinate."""

    coordinates: tuple[sp.Symbol, ...]
    components: tuple[sp.Expr, ...]
    parameters: tuple[sp.Symbol, ...] = ()

    def __post_init__(self) -> None:
        coordinates = _normalize_coordinates(self.coordinates)
        components = tuple(sp.sympify(component) for component in self.components)
        if len(components) != len(coordinates):
            raise ValueError("a vector field needs one component per coordinate")
        object.__setattr__(self, "coordinates", coordinates)
        object.__setattr__(self, "components", components)
        object.__setattr__(self, "parameters", tuple(self.parameters))
        _check_free_symbols(components, coordinates, self.parameters)

    @property
    def dimension(self) -> int:
        return len(self.coordinates)

    def divergence(self) -> ScalarField:
        expression = sp.expand(
            sum(
                (sp.diff(component, coordinate)
                 for component, coordinate in zip(self.components, self.coordinates)),
                sp.Integer(0),
            )
        )
        return ScalarField(self.coordinates, expression, self.parameters)

    def curl(self) -> "VectorField":
        if self.dimension != 3:
            raise ValueError("curl is only defined for three-dimensional fields")
        x, y, z = self.coordinates
        vx, vy, vz = self.components
        components = (
            sp.diff(vz, y) - sp.diff(vy, z),
            sp.diff(vx, z) - sp.diff(vz, x),
            sp.diff(vy, x) - sp.diff(vx, y),
        )
        return VectorField(self.coordinates, components, self.parameters)

    def sample(
        self,
        axes: Sequence[Sequence[float]],
        parameter_values: Mapping[str, float] | None = None,
    ) -> np.ndarray:
        """Sample the field, returning shape ``(*grid_shape, dimension)``."""

        sampled = [
            _sample_expression(component, self.coordinates, self.parameters, axes, parameter_values)
            for component in self.components
        ]
        return np.stack(sampled, axis=-1)


def gradient(field: ScalarField) -> VectorField:
    return field.gradient()


def divergence(field: VectorField) -> ScalarField:
    return field.divergence()


def curl(field: VectorField) -> VectorField:
    return field.curl()


def laplacian(field: ScalarField) -> ScalarField:
    return field.laplacian()
