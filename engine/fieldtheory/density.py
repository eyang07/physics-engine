"""Symbolic Lagrangian field densities.

This module only represents field-density structure. It computes exact symbolic
Euler-Lagrange expressions for one scalar field and does not provide a PDE
integrator or sampled time evolution.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

import numpy as np
import sympy as sp
from sympy.core.function import AppliedUndef

from engine.fields import MeasuredFieldGrid, VectorField, measured_divergence_grid
from engine.relativity.minkowski import minkowski_eta


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


def _normalize_metric(metric: sp.Matrix | Sequence[Sequence[object]], dimension: int) -> sp.Matrix:
    matrix = sp.Matrix(metric)
    if matrix.shape != (dimension, dimension):
        raise ValueError(f"metric must have shape ({dimension}, {dimension})")
    if matrix != matrix.T:
        raise ValueError("metric must be symmetric")
    if matrix.det() == 0:
        raise ValueError("metric must be invertible")
    return matrix


def _default_metric(dimension: int) -> sp.Matrix:
    if dimension < 2:
        return sp.diag(-1)
    return minkowski_eta(dimension)


def _substitute_field_configuration(
    expression: sp.Expr,
    *,
    field: AppliedUndef,
    coordinates: tuple[sp.Symbol, ...],
    parameters: tuple[sp.Symbol, ...],
    configuration: sp.Expr,
) -> sp.Expr:
    config = sp.sympify(configuration)
    allowed = set(coordinates) | set(parameters)
    unresolved = {symbol for symbol in config.free_symbols if symbol not in allowed}
    if unresolved:
        names = ", ".join(sorted(symbol.name for symbol in unresolved))
        raise ValueError(f"field configuration has unresolved symbols: {names}")
    extra_fields = config.atoms(AppliedUndef)
    if extra_fields:
        names = ", ".join(sorted(str(node) for node in extra_fields))
        raise ValueError(f"field configuration must be an explicit expression: {names}")

    replacements: dict[sp.Expr, sp.Expr] = {field: config}
    for derivative in expression.atoms(sp.Derivative):
        if derivative.expr != field:
            continue
        value = config
        for variable, count in derivative.variable_count:
            value = sp.diff(value, variable, count)
        replacements[derivative] = value
    return sp.simplify(expression.xreplace(replacements))


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

    def stress_energy_tensor(
        self,
        metric: sp.Matrix | Sequence[Sequence[object]] | None = None,
    ) -> sp.Matrix:
        """Return symmetric covariant ``T_mu_nu`` for a scalar field density.

        The default flat metric follows the repository's mostly-plus convention
        ``diag(-1, +1, ...)``. The density is interpreted in the standard scalar
        form ``L = -1/2 g^mu_nu d_mu phi d_nu phi - V(phi)``.
        """

        metric_matrix = (
            _default_metric(self.dimension)
            if metric is None
            else _normalize_metric(metric, self.dimension)
        )
        derivatives = self.field_derivatives
        return sp.simplify(
            sp.Matrix(
                [
                    [
                        derivatives[mu] * derivatives[nu]
                        + metric_matrix[mu, nu] * self.density
                        for nu in range(self.dimension)
                    ]
                    for mu in range(self.dimension)
                ]
            )
        )

    def mixed_stress_energy_tensor(
        self,
        metric: sp.Matrix | Sequence[Sequence[object]] | None = None,
    ) -> sp.Matrix:
        """Return ``T^mu_nu`` by raising the first index of ``T_mu_nu``."""

        metric_matrix = (
            _default_metric(self.dimension)
            if metric is None
            else _normalize_metric(metric, self.dimension)
        )
        return sp.simplify(metric_matrix.inv() * self.stress_energy_tensor(metric_matrix))

    def stress_energy_divergence(
        self,
        metric: sp.Matrix | Sequence[Sequence[object]] | None = None,
    ) -> tuple[sp.Expr, ...]:
        """Return exact symbolic ``d_mu T^mu_nu`` in coordinate order."""

        mixed = self.mixed_stress_energy_tensor(metric)
        return tuple(
            sp.simplify(
                sum(
                    (
                        sp.diff(mixed[mu, nu], self.coordinates[mu])
                        for mu in range(self.dimension)
                    ),
                    sp.Integer(0),
                )
            )
            for nu in range(self.dimension)
        )

    def measured_stress_energy_conservation_residual(
        self,
        configuration: sp.Expr,
        axes: Sequence[Sequence[float]],
        *,
        parameter_values: Mapping[str, float] | None = None,
        metric: sp.Matrix | Sequence[Sequence[object]] | None = None,
        name: str = "stress-energy.conservation",
        edge_order: int = 2,
    ) -> MeasuredFieldGrid:
        """Sample finite-difference ``d_mu T^mu_nu`` for a field configuration.

        The returned grid is measured evidence only. It evaluates ``T^mu_nu`` on
        the supplied configuration, then reuses the existing field divergence
        diagnostic for each fixed ``nu`` column.
        """

        mixed = self.mixed_stress_energy_tensor(metric)
        substituted = sp.Matrix(
            [
                [
                    _substitute_field_configuration(
                        mixed[mu, nu],
                        field=self.field,
                        coordinates=self.coordinates,
                        parameters=self.parameters,
                        configuration=configuration,
                    )
                    for nu in range(self.dimension)
                ]
                for mu in range(self.dimension)
            ]
        )

        column_residuals: list[np.ndarray] = []
        first_grid: MeasuredFieldGrid | None = None
        for nu in range(self.dimension):
            column_field = VectorField(
                self.coordinates,
                tuple(substituted[mu, nu] for mu in range(self.dimension)),
                self.parameters,
            )
            grid = measured_divergence_grid(
                column_field,
                axes,
                name=f"{name}.{nu}",
                parameter_values=parameter_values,
                edge_order=edge_order,
            )
            first_grid = grid if first_grid is None else first_grid
            column_residuals.append(grid.values)

        if first_grid is None:
            raise ValueError("stress-energy residual needs at least one component")
        return MeasuredFieldGrid(
            name=name,
            operator="stress-energy-divergence",
            coordinates=first_grid.coordinates,
            axes=first_grid.axes,
            values=np.stack(column_residuals, axis=-1),
        )


def stress_energy_tensor(
    density: LagrangianFieldDensity,
    metric: sp.Matrix | Sequence[Sequence[object]] | None = None,
) -> sp.Matrix:
    return density.stress_energy_tensor(metric)


def measured_stress_energy_conservation_residual(
    density: LagrangianFieldDensity,
    configuration: sp.Expr,
    axes: Sequence[Sequence[float]],
    *,
    parameter_values: Mapping[str, float] | None = None,
    metric: sp.Matrix | Sequence[Sequence[object]] | None = None,
    name: str = "stress-energy.conservation",
    edge_order: int = 2,
) -> MeasuredFieldGrid:
    return density.measured_stress_energy_conservation_residual(
        configuration,
        axes,
        parameter_values=parameter_values,
        metric=metric,
        name=name,
        edge_order=edge_order,
    )
