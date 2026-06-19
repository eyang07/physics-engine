from __future__ import annotations

import sympy as sp

from engine.mechanics import LagrangianSystem
from engine.mechanics.coordinates import CoordinateChart


def build_chain_system(
    count: int = 4,
    *,
    mass: sp.Expr | float | None = None,
    spring_constant: sp.Expr | float | None = None,
) -> LagrangianSystem:
    """Build a fixed-end chain of ``count`` identical coupled oscillators."""

    if not isinstance(count, int) or count < 1:
        raise ValueError("count must be a positive integer")

    chart = CoordinateChart.from_names(" ".join(f"x{index}" for index in range(1, count + 1)))
    m = sp.Symbol("m", positive=True) if mass is None else mass
    k = sp.Symbol("k", positive=True) if spring_constant is None else spring_constant

    kinetic = sp.Rational(1, 2) * m * sum(velocity**2 for velocity in chart.velocities)
    potential = sp.Rational(1, 2) * k * chart.coordinates[0] ** 2
    for left, right in zip(chart.coordinates, chart.coordinates[1:], strict=False):
        potential += sp.Rational(1, 2) * k * (right - left) ** 2
    potential += sp.Rational(1, 2) * k * chart.coordinates[-1] ** 2

    return LagrangianSystem(
        coordinates=chart.coordinates,
        velocities=chart.velocities,
        lagrangian=kinetic - potential,
        time=chart.time,
    )


def build_system(
    mass: sp.Expr | float | None = None,
    spring_constant: sp.Expr | float | None = None,
) -> LagrangianSystem:
    return build_chain_system(
        count=4,
        mass=mass,
        spring_constant=spring_constant,
    )


system = build_system()
