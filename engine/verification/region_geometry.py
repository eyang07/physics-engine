"""Sampled geometry helpers for verification-region visualization."""

from __future__ import annotations

from typing import Mapping

import numpy as np
import sympy as sp

from engine.verification.ir import RegionGeometrySpec, RegionSpec


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
