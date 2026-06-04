from __future__ import annotations

import sympy as sp

from engine.mechanics import LagrangianSystem
from engine.mechanics.coordinates import CoordinateChart


def build_system(
    mass: sp.Expr | float | None = None,
    gravity: sp.Expr | float | None = None,
) -> LagrangianSystem:
    """Projectile motion in a uniform gravitational field.

    Coordinates are (x, z), with z vertical and potential energy V = m g z.
    """

    chart = CoordinateChart.from_names("x z")
    _x, z = chart.coordinates
    x_dot, z_dot = chart.velocities

    m = sp.Symbol("m", positive=True) if mass is None else mass
    g = sp.Symbol("g", positive=True) if gravity is None else gravity

    kinetic_energy = sp.Rational(1, 2) * m * (x_dot**2 + z_dot**2)
    potential_energy = m * g * z
    return LagrangianSystem(
        coordinates=chart.coordinates,
        velocities=chart.velocities,
        lagrangian=kinetic_energy - potential_energy,
        time=chart.time,
    )


system = build_system()

