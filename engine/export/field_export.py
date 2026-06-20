"""Deterministic export payloads for scalar/vector fields and field lines.

These builders turn a symbolic :mod:`engine.fields` field into JSON-ready
rendering data: scalar-field grids (heatmap/contour), vector-field grids
(glyph/quiver), and field-line polylines. The values are exact samples of the
symbolic field — deterministic given the same axes and parameters — not measured
numerical evidence. The viewer draws the exported grids and lines directly; it
never evaluates the field itself.
"""

from __future__ import annotations

from typing import Mapping, Sequence

import numpy as np

from engine.fields import ScalarField, VectorField

SCALAR_FIELD_HINT = "scalar-field"
VECTOR_FIELD_HINT = "vector-field"
FIELD_LINES_HINT = "field-lines"


def _axes_payload(axes: Sequence[Sequence[float]]) -> list[list[float]]:
    return [np.asarray(axis, dtype=float).tolist() for axis in axes]


def scalar_field_grid(
    field: ScalarField,
    axes: Sequence[Sequence[float]],
    *,
    name: str,
    parameter_values: Mapping[str, float] | None = None,
) -> dict[str, object]:
    """Return a deterministic scalar-field grid export payload."""

    values = field.sample(axes, parameter_values)
    return {
        "kind": SCALAR_FIELD_HINT,
        "rendererHint": SCALAR_FIELD_HINT,
        "name": name,
        "coordinates": [symbol.name for symbol in field.coordinates],
        "axes": _axes_payload(axes),
        "shape": list(values.shape),
        "values": values.tolist(),
        "evaluation": "symbolic-exact",
    }


def vector_field_grid(
    field: VectorField,
    axes: Sequence[Sequence[float]],
    *,
    name: str,
    parameter_values: Mapping[str, float] | None = None,
) -> dict[str, object]:
    """Return a deterministic vector-field grid export payload.

    Carries the per-node components plus their magnitude so a renderer can scale
    and colour glyphs without re-evaluating the field.
    """

    components = field.sample(axes, parameter_values)
    magnitude = np.linalg.norm(components, axis=-1)
    grid_shape = magnitude.shape
    return {
        "kind": VECTOR_FIELD_HINT,
        "rendererHint": VECTOR_FIELD_HINT,
        "name": name,
        "coordinates": [symbol.name for symbol in field.coordinates],
        "axes": _axes_payload(axes),
        "shape": list(grid_shape),
        "dimension": field.dimension,
        "components": components.tolist(),
        "magnitude": magnitude.tolist(),
        "evaluation": "symbolic-exact",
    }


def field_lines(
    polylines: Sequence[Sequence[Sequence[float]]],
    *,
    name: str,
    dimension: int,
    seeds: Sequence[Sequence[float]] | None = None,
) -> dict[str, object]:
    """Return a field-line / streamline polyline export payload.

    Each polyline is a sequence of ``dimension``-vectors. The integration that
    produces physically meaningful lines is BE-092; this is the container they
    are exported in.
    """

    if dimension < 1:
        raise ValueError("dimension must be positive")
    lines: list[list[list[float]]] = []
    for index, polyline in enumerate(polylines):
        points = np.asarray(polyline, dtype=float)
        if points.ndim != 2 or points.shape[1] != dimension:
            raise ValueError(f"polyline {index} must have shape (point, {dimension})")
        lines.append(points.tolist())

    payload: dict[str, object] = {
        "kind": FIELD_LINES_HINT,
        "rendererHint": FIELD_LINES_HINT,
        "name": name,
        "dimension": dimension,
        "count": len(lines),
        "lines": lines,
    }
    if seeds is not None:
        seed_points = np.asarray(seeds, dtype=float)
        if seed_points.ndim != 2 or seed_points.shape[1] != dimension:
            raise ValueError(f"seeds must have shape (seed, {dimension})")
        payload["seeds"] = seed_points.tolist()
    return payload
