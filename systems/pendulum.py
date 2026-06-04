from __future__ import annotations

import sympy as sp

from engine.mechanics import LagrangianSystem
from engine.mechanics.coordinates import CoordinateChart


def build_system(
    mass: sp.Expr | float | None = None,
    length: sp.Expr | float | None = None,
    gravity: sp.Expr | float | None = None,
) -> LagrangianSystem:
    chart = CoordinateChart.from_names("theta")
    (theta,) = chart.coordinates
    (theta_dot,) = chart.velocities

    m = sp.Symbol("m", positive=True) if mass is None else mass
    ell = sp.Symbol("ell", positive=True) if length is None else length
    g = sp.Symbol("g", positive=True) if gravity is None else gravity

    kinetic_energy = sp.Rational(1, 2) * m * ell**2 * theta_dot**2
    potential_energy = m * g * ell * (1 - sp.cos(theta))
    lagrangian = kinetic_energy - potential_energy

    return LagrangianSystem(
        coordinates=chart.coordinates,
        velocities=chart.velocities,
        lagrangian=lagrangian,
        time=chart.time,
    )


system = build_system()

