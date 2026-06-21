"""Measured vector-calculus diagnostics for sampled fields.

The symbolic :mod:`engine.fields` objects remain the source of mathematical
truth. This module deliberately emits finite-difference and quadrature
diagnostics labeled as measured evidence: useful numerical checks of exported
field data, never proofs of Gauss/Stokes identities.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

import numpy as np
import sympy as sp

from engine.fields.fields import VectorField

MEASURED_FIELD_NOTE = (
    "Measured finite-sample vector-calculus diagnostic; agreement is numerical "
    "evidence only, not a symbolic identity, proof, or certificate."
)


def _axis_arrays(
    axes: Sequence[Sequence[float]],
    *,
    dimension: int,
    minimum_count: int,
) -> tuple[np.ndarray, ...]:
    if len(axes) != dimension:
        raise ValueError("one axis is required per coordinate")
    arrays = tuple(np.asarray(axis, dtype=float) for axis in axes)
    for index, axis in enumerate(arrays):
        if axis.ndim != 1:
            raise ValueError(f"axis {index} must be one-dimensional")
        if len(axis) < minimum_count:
            raise ValueError(f"axis {index} needs at least {minimum_count} samples")
        if not np.all(np.isfinite(axis)):
            raise ValueError(f"axis {index} must contain only finite values")
        if np.any(np.diff(axis) <= 0.0):
            raise ValueError(f"axis {index} must be strictly increasing")
    return arrays


def _parameter_args(
    parameters: Sequence[sp.Symbol],
    parameter_values: Mapping[str, float] | None,
) -> list[float]:
    values = parameter_values or {}
    missing = {parameter.name for parameter in parameters} - set(values)
    if missing:
        raise ValueError(f"missing parameter values: {', '.join(sorted(missing))}")
    return [float(values[parameter.name]) for parameter in parameters]


def _field_values_at(
    field: VectorField,
    points: Sequence[Sequence[float]],
    parameter_values: Mapping[str, float] | None = None,
) -> np.ndarray:
    point_array = np.asarray(points, dtype=float)
    if point_array.ndim != 2 or point_array.shape[1] != field.dimension:
        raise ValueError(f"points must have shape (sample, {field.dimension})")
    if not np.all(np.isfinite(point_array)):
        raise ValueError("points must contain only finite values")

    args = [point_array[:, axis] for axis in range(field.dimension)]
    args.extend(_parameter_args(field.parameters, parameter_values))
    values = [
        np.asarray(
            sp.lambdify((*field.coordinates, *field.parameters), component, modules="numpy")(
                *args
            ),
            dtype=float,
        )
        for component in field.components
    ]
    columns = [
        np.broadcast_to(component_values, (point_array.shape[0],)).astype(float)
        for component_values in values
    ]
    result = np.stack(columns, axis=1)
    if not np.all(np.isfinite(result)):
        raise ValueError("field evaluation produced non-finite values")
    return result


@dataclass(frozen=True)
class MeasuredFieldGrid:
    """Finite-difference scalar/vector grid diagnostic."""

    name: str
    operator: str
    coordinates: tuple[str, ...]
    axes: tuple[tuple[float, ...], ...]
    values: np.ndarray
    rigor: str = "measured"
    evaluation: str = "measured-finite-difference-grid"
    note: str = MEASURED_FIELD_NOTE

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("diagnostic name must be non-empty")
        if not self.operator:
            raise ValueError("diagnostic operator must be non-empty")
        if self.rigor != "measured":
            raise ValueError("field diagnostics must use rigor='measured'")
        values = np.asarray(self.values, dtype=float)
        if values.size == 0 or not np.all(np.isfinite(values)):
            raise ValueError("diagnostic values must be finite and non-empty")
        object.__setattr__(self, "values", values)
        object.__setattr__(
            self,
            "axes",
            tuple(tuple(float(value) for value in axis) for axis in self.axes),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "kind": "field-diagnostic-grid",
            "name": self.name,
            "operator": self.operator,
            "coordinates": list(self.coordinates),
            "axes": [list(axis) for axis in self.axes],
            "shape": list(self.values.shape),
            "values": self.values.tolist(),
            "evaluation": self.evaluation,
            "rigor": self.rigor,
            "note": self.note,
        }


@dataclass(frozen=True)
class MeasuredFieldIntegral:
    """Measured quadrature integral over a line or surface."""

    name: str
    quantity: str
    value: float
    sample_count: int
    rigor: str = "measured"
    evaluation: str = "measured-quadrature"
    note: str = MEASURED_FIELD_NOTE

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("integral name must be non-empty")
        if not self.quantity:
            raise ValueError("integral quantity must be non-empty")
        if self.rigor != "measured":
            raise ValueError("field integrals must use rigor='measured'")
        if self.sample_count <= 0:
            raise ValueError("sample_count must be positive")
        if not np.isfinite(self.value):
            raise ValueError("integral value must be finite")
        object.__setattr__(self, "value", float(self.value))

    def to_dict(self) -> dict[str, object]:
        return {
            "kind": "field-integral",
            "name": self.name,
            "quantity": self.quantity,
            "value": self.value,
            "sampleCount": self.sample_count,
            "evaluation": self.evaluation,
            "rigor": self.rigor,
            "note": self.note,
        }


@dataclass(frozen=True)
class MeasuredFieldLawCheck:
    """Measured comparison of two numerical vector-calculus integrals."""

    name: str
    law: str
    left: MeasuredFieldIntegral
    right: MeasuredFieldIntegral
    tolerance: float | None = None
    rigor: str = "measured"
    note: str = MEASURED_FIELD_NOTE

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("law-check name must be non-empty")
        if self.law not in {"gauss", "stokes"}:
            raise ValueError("law must be 'gauss' or 'stokes'")
        if self.rigor != "measured":
            raise ValueError("field law checks must use rigor='measured'")
        if self.left.rigor != "measured" or self.right.rigor != "measured":
            raise ValueError("law-check inputs must be measured")
        if self.tolerance is not None and self.tolerance <= 0.0:
            raise ValueError("tolerance must be positive")

    @property
    def residual(self) -> float:
        return float(self.left.value - self.right.value)

    @property
    def abs_residual(self) -> float:
        return abs(self.residual)

    @property
    def passed(self) -> bool | None:
        if self.tolerance is None:
            return None
        return self.abs_residual <= self.tolerance

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "kind": "field-law-check",
            "name": self.name,
            "law": self.law,
            "left": self.left.to_dict(),
            "right": self.right.to_dict(),
            "residual": self.residual,
            "absResidual": self.abs_residual,
            "rigor": self.rigor,
            "note": self.note,
        }
        if self.tolerance is not None:
            payload["tolerance"] = self.tolerance
            payload["passed"] = self.passed
        return payload


def measured_divergence_grid(
    field: VectorField,
    axes: Sequence[Sequence[float]],
    *,
    name: str = "divergence",
    parameter_values: Mapping[str, float] | None = None,
    edge_order: int = 2,
) -> MeasuredFieldGrid:
    """Return a measured finite-difference divergence grid."""

    axis_arrays = _axis_arrays(axes, dimension=field.dimension, minimum_count=edge_order + 1)
    samples = field.sample(axis_arrays, parameter_values)
    divergence = np.zeros(samples.shape[:-1], dtype=float)
    for component_index in range(field.dimension):
        gradient = np.gradient(
            samples[..., component_index],
            *axis_arrays,
            edge_order=edge_order,
        )
        divergence += np.asarray(gradient[component_index], dtype=float)
    return MeasuredFieldGrid(
        name=name,
        operator="divergence",
        coordinates=tuple(symbol.name for symbol in field.coordinates),
        axes=tuple(tuple(float(value) for value in axis) for axis in axis_arrays),
        values=divergence,
    )


def measured_curl_grid(
    field: VectorField,
    axes: Sequence[Sequence[float]],
    *,
    name: str = "curl",
    parameter_values: Mapping[str, float] | None = None,
    edge_order: int = 2,
) -> MeasuredFieldGrid:
    """Return a measured finite-difference curl grid.

    Planar fields return the scalar out-of-plane curl ``dF_y/dx - dF_x/dy``.
    Three-dimensional fields return vector curl values on the grid.
    """

    if field.dimension not in {2, 3}:
        raise ValueError("curl diagnostics require a two- or three-dimensional field")
    axis_arrays = _axis_arrays(axes, dimension=field.dimension, minimum_count=edge_order + 1)
    samples = field.sample(axis_arrays, parameter_values)
    component_gradients = [
        np.gradient(samples[..., component_index], *axis_arrays, edge_order=edge_order)
        for component_index in range(field.dimension)
    ]

    if field.dimension == 2:
        curl_z = np.asarray(component_gradients[1][0] - component_gradients[0][1], dtype=float)
        return MeasuredFieldGrid(
            name=name,
            operator="curl-z",
            coordinates=tuple(symbol.name for symbol in field.coordinates),
            axes=tuple(tuple(float(value) for value in axis) for axis in axis_arrays),
            values=curl_z,
        )

    curl_values = np.stack(
        [
            component_gradients[2][1] - component_gradients[1][2],
            component_gradients[0][2] - component_gradients[2][0],
            component_gradients[1][0] - component_gradients[0][1],
        ],
        axis=-1,
    )
    return MeasuredFieldGrid(
        name=name,
        operator="curl",
        coordinates=tuple(symbol.name for symbol in field.coordinates),
        axes=tuple(tuple(float(value) for value in axis) for axis in axis_arrays),
        values=curl_values,
    )


def surface_flux(
    field: VectorField,
    points: Sequence[Sequence[float]],
    normals: Sequence[Sequence[float]],
    weights: Sequence[float],
    *,
    name: str = "surfaceFlux",
    parameter_values: Mapping[str, float] | None = None,
) -> MeasuredFieldIntegral:
    """Return measured surface flux ``int F . n dS`` from quadrature samples."""

    point_array = np.asarray(points, dtype=float)
    normal_array = np.asarray(normals, dtype=float)
    weight_array = np.asarray(weights, dtype=float)
    if point_array.ndim != 2 or point_array.shape[1] != field.dimension:
        raise ValueError(f"points must have shape (sample, {field.dimension})")
    if normal_array.shape != point_array.shape:
        raise ValueError("normals must match point shape")
    if weight_array.shape != (point_array.shape[0],):
        raise ValueError("weights must have one value per point")
    if not np.all(np.isfinite(normal_array)) or not np.all(np.isfinite(weight_array)):
        raise ValueError("normals and weights must contain only finite values")

    values = _field_values_at(field, point_array, parameter_values)
    flux = float(np.sum(np.einsum("ij,ij->i", values, normal_array) * weight_array))
    return MeasuredFieldIntegral(
        name=name,
        quantity="surface-flux",
        value=flux,
        sample_count=point_array.shape[0],
    )


def line_circulation(
    field: VectorField,
    points: Sequence[Sequence[float]],
    *,
    name: str = "lineCirculation",
    parameter_values: Mapping[str, float] | None = None,
) -> MeasuredFieldIntegral:
    """Return measured line circulation ``int F . dr`` along polyline points."""

    point_array = np.asarray(points, dtype=float)
    if point_array.ndim != 2 or point_array.shape[1] != field.dimension:
        raise ValueError(f"points must have shape (sample, {field.dimension})")
    if point_array.shape[0] < 2:
        raise ValueError("line circulation requires at least two points")
    if not np.all(np.isfinite(point_array)):
        raise ValueError("points must contain only finite values")
    segments = point_array[1:] - point_array[:-1]
    midpoints = 0.5 * (point_array[1:] + point_array[:-1])
    values = _field_values_at(field, midpoints, parameter_values)
    circulation = float(np.sum(np.einsum("ij,ij->i", values, segments)))
    return MeasuredFieldIntegral(
        name=name,
        quantity="line-circulation",
        value=circulation,
        sample_count=segments.shape[0],
    )


def sphere_surface_quadrature(
    *,
    radius: float,
    theta_count: int,
    phi_count: int,
    center: Sequence[float] = (0.0, 0.0, 0.0),
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return midpoint quadrature points, outward normals, and weights on a sphere."""

    if radius <= 0.0:
        raise ValueError("radius must be positive")
    if theta_count <= 0 or phi_count <= 0:
        raise ValueError("theta_count and phi_count must be positive")
    center_array = np.asarray(center, dtype=float)
    if center_array.shape != (3,):
        raise ValueError("center must be a three-dimensional point")

    dtheta = np.pi / theta_count
    dphi = 2.0 * np.pi / phi_count
    theta = (np.arange(theta_count, dtype=float) + 0.5) * dtheta
    phi = (np.arange(phi_count, dtype=float) + 0.5) * dphi
    theta_grid, phi_grid = np.meshgrid(theta, phi, indexing="ij")
    sin_theta = np.sin(theta_grid)
    normals = np.stack(
        [
            sin_theta * np.cos(phi_grid),
            sin_theta * np.sin(phi_grid),
            np.cos(theta_grid),
        ],
        axis=-1,
    ).reshape(-1, 3)
    points = center_array[None, :] + radius * normals
    weights = (radius**2 * sin_theta * dtheta * dphi).reshape(-1)
    return points, normals, weights


def gauss_flux_check(
    field: VectorField,
    points: Sequence[Sequence[float]],
    normals: Sequence[Sequence[float]],
    weights: Sequence[float],
    *,
    enclosed_charge: float,
    epsilon0: float = 1.0,
    tolerance: float | None = None,
    name: str = "gaussFlux",
    parameter_values: Mapping[str, float] | None = None,
) -> MeasuredFieldLawCheck:
    """Compare measured surface flux against ``Q_enclosed / epsilon0``."""

    if epsilon0 == 0.0:
        raise ValueError("epsilon0 must be non-zero")
    left = surface_flux(
        field,
        points,
        normals,
        weights,
        name=f"{name}.surfaceFlux",
        parameter_values=parameter_values,
    )
    right = MeasuredFieldIntegral(
        name=f"{name}.enclosedChargeOverEpsilon0",
        quantity="enclosed-charge-over-epsilon0",
        value=float(enclosed_charge) / float(epsilon0),
        sample_count=1,
        evaluation="measured-reference",
    )
    return MeasuredFieldLawCheck(
        name=name,
        law="gauss",
        left=left,
        right=right,
        tolerance=tolerance,
    )


def planar_stokes_check(
    field: VectorField,
    axes: Sequence[Sequence[float]],
    *,
    name: str = "stokesCirculation",
    parameter_values: Mapping[str, float] | None = None,
    tolerance: float | None = None,
    edge_order: int = 2,
) -> MeasuredFieldLawCheck:
    """Compare boundary circulation with measured curl flux over a rectangular grid."""

    if field.dimension != 2:
        raise ValueError("planar Stokes diagnostics require a two-dimensional field")
    x_axis, y_axis = _axis_arrays(axes, dimension=2, minimum_count=edge_order + 1)
    bottom = np.column_stack([x_axis, np.full_like(x_axis, y_axis[0])])
    right = np.column_stack([np.full_like(y_axis[1:], x_axis[-1]), y_axis[1:]])
    top = np.column_stack([x_axis[-2::-1], np.full_like(x_axis[-2::-1], y_axis[-1])])
    left = np.column_stack(
        [np.full_like(y_axis[-2:0:-1], x_axis[0]), y_axis[-2:0:-1]]
    )
    path = np.vstack([bottom, right, top, left, bottom[:1]])
    circulation = line_circulation(
        field,
        path,
        name=f"{name}.boundaryCirculation",
        parameter_values=parameter_values,
    )
    curl = measured_curl_grid(
        field,
        (x_axis, y_axis),
        name=f"{name}.curl",
        parameter_values=parameter_values,
        edge_order=edge_order,
    )
    flux_value = float(np.trapz(np.trapz(curl.values, y_axis, axis=1), x_axis, axis=0))
    curl_flux = MeasuredFieldIntegral(
        name=f"{name}.curlFlux",
        quantity="curl-flux",
        value=flux_value,
        sample_count=int(np.prod(curl.values.shape)),
        evaluation="measured-finite-difference-grid-quadrature",
    )
    return MeasuredFieldLawCheck(
        name=name,
        law="stokes",
        left=circulation,
        right=curl_flux,
        tolerance=tolerance,
    )


__all__ = [
    "MEASURED_FIELD_NOTE",
    "MeasuredFieldGrid",
    "MeasuredFieldIntegral",
    "MeasuredFieldLawCheck",
    "gauss_flux_check",
    "line_circulation",
    "measured_curl_grid",
    "measured_divergence_grid",
    "planar_stokes_check",
    "sphere_surface_quadrature",
    "surface_flux",
]
