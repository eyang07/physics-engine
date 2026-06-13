"""Sampled geometry helpers for verification-region visualization."""

from __future__ import annotations

from typing import Mapping

import numpy as np
import sympy as sp

from engine.verification.ir import RegionGeometrySpec, RegionSpec

Point = tuple[float, float]
Segment = tuple[Point, Point]


def scalar_field_region_geometry(
    region: RegionSpec,
    *,
    projection: str,
    plane_variables: tuple[str, str],
    variable_to_state_axis: Mapping[str, str],
    x_range: tuple[float, float],
    y_range: tuple[float, float],
    samples: tuple[int, int] = (81, 81),
) -> RegionGeometrySpec:
    """Evaluate one region expression over a deterministic 2-D grid.

    The result is measured visualization geometry only. The original symbolic
    region remains the verification claim; this helper only prevents the viewer
    from re-evaluating symbolic inequalities.
    """

    x_count, y_count = samples
    if x_count < 2 or y_count < 2:
        raise ValueError("region geometry samples must be at least 2 by 2")
    if plane_variables[0] == plane_variables[1]:
        raise ValueError("region geometry plane variables must be distinct")
    if set(plane_variables) - set(region.variables):
        raise ValueError("region geometry plane variables must belong to the region")

    expression = sp.sympify(region.expression.source)
    symbols_by_name = {symbol.name: symbol for symbol in expression.free_symbols}
    x_symbol = symbols_by_name.get(plane_variables[0], sp.Symbol(plane_variables[0]))
    y_symbol = symbols_by_name.get(plane_variables[1], sp.Symbol(plane_variables[1]))
    extra_symbols = expression.free_symbols - {x_symbol, y_symbol}
    if extra_symbols:
        names = ", ".join(sorted(symbol.name for symbol in extra_symbols))
        raise ValueError(f"region geometry expression has unresolved symbols: {names}")

    x_values = np.linspace(float(x_range[0]), float(x_range[1]), x_count)
    y_values = np.linspace(float(y_range[0]), float(y_range[1]), y_count)
    x_grid, y_grid = np.meshgrid(x_values, y_values, indexing="xy")
    evaluator = sp.lambdify((x_symbol, y_symbol), expression, modules="numpy")
    values = np.asarray(evaluator(x_grid, y_grid), dtype=float)
    if values.shape == ():
        values = np.full((y_count, x_count), float(values))
    if values.shape != (y_count, x_count):
        values = np.broadcast_to(values, (y_count, x_count)).astype(float)
    boundary_polylines = _boundary_polylines(x_values, y_values, values, float(region.level))

    return RegionGeometrySpec(
        region_id=region.id,
        role=region.role,
        projection=projection,
        plane_variables=plane_variables,
        state_axes=tuple(variable_to_state_axis[name] for name in plane_variables),
        variable_to_state_axis=dict(variable_to_state_axis),
        x_values=tuple(float(value) for value in x_values),
        y_values=tuple(float(value) for value in y_values),
        values=tuple(
            tuple(float(value) for value in row)
            for row in values
        ),
        level=float(region.level),
        convention=region.convention,
        boundary_polylines=boundary_polylines,
    )


def scalar_field_region_geometries(
    regions: tuple[RegionSpec, ...],
    *,
    projection: str,
    plane_variables: tuple[str, str],
    variable_to_state_axis: Mapping[str, str],
    x_range: tuple[float, float],
    y_range: tuple[float, float],
    samples: tuple[int, int] = (81, 81),
) -> tuple[RegionGeometrySpec, ...]:
    """Evaluate every region over the same projection grid."""

    return tuple(
        scalar_field_region_geometry(
            region,
            projection=projection,
            plane_variables=plane_variables,
            variable_to_state_axis=variable_to_state_axis,
            x_range=x_range,
            y_range=y_range,
            samples=samples,
        )
        for region in regions
    )


def _boundary_polylines(
    x_values: np.ndarray,
    y_values: np.ndarray,
    values: np.ndarray,
    level: float,
) -> tuple[tuple[Point, ...], ...]:
    segments: list[Segment] = []
    for y_index in range(len(y_values) - 1):
        for x_index in range(len(x_values) - 1):
            segments.extend(
                _cell_segments(
                    x0=float(x_values[x_index]),
                    x1=float(x_values[x_index + 1]),
                    y0=float(y_values[y_index]),
                    y1=float(y_values[y_index + 1]),
                    v00=float(values[y_index, x_index]),
                    v10=float(values[y_index, x_index + 1]),
                    v11=float(values[y_index + 1, x_index + 1]),
                    v01=float(values[y_index + 1, x_index]),
                    level=level,
                )
            )
    return _join_segments(segments)


def _cell_segments(
    *,
    x0: float,
    x1: float,
    y0: float,
    y1: float,
    v00: float,
    v10: float,
    v11: float,
    v01: float,
    level: float,
) -> tuple[Segment, ...]:
    corners = (
        ((x0, y0), v00),
        ((x1, y0), v10),
        ((x1, y1), v11),
        ((x0, y1), v01),
    )
    edges = ((0, 1), (1, 2), (2, 3), (3, 0))
    intersections: list[Point] = []
    for start_index, end_index in edges:
        point = _edge_intersection(
            corners[start_index][0],
            corners[start_index][1],
            corners[end_index][0],
            corners[end_index][1],
            level,
        )
        if point is not None and not any(_same_point(point, existing) for existing in intersections):
            intersections.append(point)

    if len(intersections) < 2:
        return ()
    if len(intersections) == 2:
        return ((intersections[0], intersections[1]),)

    # Ambiguous saddle cells produce four intersections. Pair nearest neighbors
    # deterministically; the grid is only render metadata, not topology proof.
    ordered = sorted(intersections)
    first = ordered.pop(0)
    nearest_index = min(
        range(len(ordered)),
        key=lambda index: _squared_distance(first, ordered[index]),
    )
    second = ordered.pop(nearest_index)
    return ((first, second), (ordered[0], ordered[1]))


def _edge_intersection(
    p0: Point,
    v0: float,
    p1: Point,
    v1: float,
    level: float,
) -> Point | None:
    d0 = v0 - level
    d1 = v1 - level
    if d0 == 0.0 and d1 == 0.0:
        return None
    if d0 == 0.0:
        return p0
    if d1 == 0.0:
        return p1
    if d0 * d1 > 0.0:
        return None
    fraction = d0 / (d0 - d1)
    return (
        p0[0] + fraction * (p1[0] - p0[0]),
        p0[1] + fraction * (p1[1] - p0[1]),
    )


def _join_segments(segments: list[Segment]) -> tuple[tuple[Point, ...], ...]:
    unused = list(segments)
    polylines: list[tuple[Point, ...]] = []
    while unused:
        start, end = unused.pop(0)
        points = [start, end]
        changed = True
        while changed:
            changed = False
            for index, segment in enumerate(unused):
                a, b = segment
                if _same_point(points[-1], a):
                    points.append(b)
                elif _same_point(points[-1], b):
                    points.append(a)
                elif _same_point(points[0], b):
                    points.insert(0, a)
                elif _same_point(points[0], a):
                    points.insert(0, b)
                else:
                    continue
                unused.pop(index)
                changed = True
                break
        polylines.append(tuple(_deduplicate_adjacent(points)))
    return tuple(
        polyline
        for polyline in polylines
        if len(polyline) >= 2
    )


def _deduplicate_adjacent(points: list[Point]) -> list[Point]:
    deduplicated: list[Point] = []
    for point in points:
        if not deduplicated or not _same_point(point, deduplicated[-1]):
            deduplicated.append(point)
    return deduplicated


def _same_point(a: Point, b: Point) -> bool:
    return round(a[0], 12) == round(b[0], 12) and round(a[1], 12) == round(b[1], 12)


def _squared_distance(a: Point, b: Point) -> float:
    return (a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2
