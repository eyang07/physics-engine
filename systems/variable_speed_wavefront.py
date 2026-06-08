from __future__ import annotations

import sympy as sp

from engine.dynamics import CotangentHamiltonianSystem
from engine.mechanics.coordinates import CoordinateChart


def wave_speed(
    x: sp.Expr,
    y: sp.Expr,
    *,
    base_speed: sp.Expr | float,
    lens_strength: sp.Expr | float,
    lens_width: sp.Expr | float,
) -> sp.Expr:
    radius_squared = x**2 + y**2
    lens = lens_strength * sp.exp(-radius_squared / (2 * lens_width**2))
    return sp.simplify(base_speed * (1 - lens))


def build_system(
    base_speed: sp.Expr | float | None = None,
    lens_strength: sp.Expr | float | None = None,
    lens_width: sp.Expr | float | None = None,
) -> CotangentHamiltonianSystem:
    chart = CoordinateChart.from_names("x y")
    x, y = chart.coordinates
    xi, eta = sp.symbols("xi eta", real=True)

    c0_value = sp.Symbol("c0", positive=True) if base_speed is None else base_speed
    alpha_value = sp.Symbol("alpha", nonnegative=True) if lens_strength is None else lens_strength
    sigma_value = sp.Symbol("sigma", positive=True) if lens_width is None else lens_width

    speed = wave_speed(
        x,
        y,
        base_speed=c0_value,
        lens_strength=alpha_value,
        lens_width=sigma_value,
    )
    symbol = sp.simplify(speed**2 * (xi**2 + eta**2) / 2)

    return CotangentHamiltonianSystem(
        coordinates=chart.coordinates,
        momenta=(xi, eta),
        symbol=symbol,
        parameters=tuple(
            symbol
            for symbol in (c0_value, alpha_value, sigma_value)
            if isinstance(symbol, sp.Symbol)
        ),
        time=chart.time,
    )


system = build_system()
