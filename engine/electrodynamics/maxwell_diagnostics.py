"""Measured Maxwell source-constraint diagnostics for static EM fields."""

from __future__ import annotations

from typing import Sequence

import numpy as np
import sympy as sp

from engine.fields import VectorField, measured_divergence_grid


def _triplet(values: Sequence[object], name: str) -> tuple[sp.Expr, sp.Expr, sp.Expr]:
    components = tuple(sp.sympify(value) for value in values)
    if len(components) != 3:
        raise ValueError(f"{name} must have exactly three components")
    return components  # type: ignore[return-value]


def maxwell_source_constraint_diagnostics(
    *,
    electric: Sequence[object],
    magnetic: Sequence[object],
    axes: Sequence[Sequence[float]] | None = None,
    rho_over_epsilon0: object = 0,
) -> list[dict[str, object]]:
    """Return measured ``div B = 0`` and ``div E = rho/eps0`` diagnostics.

    The returned payloads are finite-difference evidence for exported field
    samples only. They do not prove Maxwell's equations or discharge the
    corresponding external obligations.
    """

    x, y, z = sp.symbols("x y z", real=True)
    grid_axes = (
        tuple(float(value) for value in axis)
        for axis in (
            axes
            if axes is not None
            else (
                np.linspace(-1.0, 1.0, 5),
                np.linspace(-1.0, 1.0, 5),
                np.linspace(-1.0, 1.0, 5),
            )
        )
    )
    axis_tuple = tuple(grid_axes)
    electric_field = VectorField((x, y, z), _triplet(electric, "electric"))
    magnetic_field = VectorField((x, y, z), _triplet(magnetic, "magnetic"))
    rho_expr = sp.sympify(rho_over_epsilon0)

    div_e = measured_divergence_grid(
        electric_field,
        axis_tuple,
        name="maxwell.divE",
    )
    div_b = measured_divergence_grid(
        magnetic_field,
        axis_tuple,
        name="maxwell.divB",
    )
    rho_value = float(sp.N(rho_expr))
    div_e_residual = div_e.values - rho_value

    return [
        {
            "kind": "maxwell-source-constraint",
            "name": "divB",
            "equation": "div B = 0",
            "operator": "divergence",
            "field": "magnetic",
            "diagnostic": div_b.to_dict(),
            "residualMaxAbs": float(np.max(np.abs(div_b.values))),
            "rigor": "measured",
            "evaluation": "measured-finite-difference-grid",
            "note": div_b.note,
        },
        {
            "kind": "maxwell-source-constraint",
            "name": "divE",
            "equation": "div E = rho/eps0",
            "operator": "divergence",
            "field": "electric",
            "diagnostic": div_e.to_dict(),
            "rhoOverEpsilon0": rho_value,
            "residualMaxAbs": float(np.max(np.abs(div_e_residual))),
            "rigor": "measured",
            "evaluation": "measured-finite-difference-grid",
            "note": div_e.note,
        },
    ]


__all__ = [
    "maxwell_source_constraint_diagnostics",
]
