from __future__ import annotations

import sympy as sp

from engine.dynamics import FirstOrderSystem
from engine.mechanics.coordinates import CoordinateChart


def build_system(
    sigma: sp.Expr | float | None = None,
    rho: sp.Expr | float | None = None,
    beta: sp.Expr | float | None = None,
) -> FirstOrderSystem:
    chart = CoordinateChart.from_names("x y z")
    x, y, z = chart.coordinates

    sigma_value = sp.Symbol("sigma", positive=True) if sigma is None else sigma
    rho_value = sp.Symbol("rho", positive=True) if rho is None else rho
    beta_value = sp.Symbol("beta", positive=True) if beta is None else beta

    return FirstOrderSystem(
        state=chart.coordinates,
        rhs=(
            sigma_value * (y - x),
            x * (rho_value - z) - y,
            x * y - beta_value * z,
        ),
        parameters=tuple(
            symbol
            for symbol in (sigma_value, rho_value, beta_value)
            if isinstance(symbol, sp.Symbol)
        ),
        time=chart.time,
    )


system = build_system()
