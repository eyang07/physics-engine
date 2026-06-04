from __future__ import annotations

import sympy as sp

from engine.mechanics import LagrangianSystem
from engine.mechanics.coordinates import CoordinateChart


def build_system(
    mass: sp.Expr | float | None = None,
    spring_constant: sp.Expr | float | None = None,
) -> LagrangianSystem:
    """One-dimensional ideal mass-spring oscillator."""

    chart = CoordinateChart.from_names("x")
    (x,) = chart.coordinates
    (x_dot,) = chart.velocities

    m = sp.Symbol("m", positive=True) if mass is None else mass
    k = sp.Symbol("k", positive=True) if spring_constant is None else spring_constant

    kinetic_energy = sp.Rational(1, 2) * m * x_dot**2
    potential_energy = sp.Rational(1, 2) * k * x**2
    return LagrangianSystem(
        coordinates=chart.coordinates,
        velocities=chart.velocities,
        lagrangian=kinetic_energy - potential_energy,
        time=chart.time,
    )


system = build_system()

