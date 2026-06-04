from __future__ import annotations

import sympy as sp

from engine.mechanics import LagrangianSystem
from engine.mechanics.coordinates import CoordinateChart


def build_system(
    mass: sp.Expr | float | None = None,
    gravitational_parameter: sp.Expr | float | None = None,
) -> LagrangianSystem:
    """Planar Kepler problem in polar coordinates.

    The potential is V(r) = -mu m / r, so L = T + mu m / r.
    """

    chart = CoordinateChart.from_names("r phi")
    r, _phi = chart.coordinates
    r_dot, phi_dot = chart.velocities

    m = sp.Symbol("m", positive=True) if mass is None else mass
    mu = sp.Symbol("mu", positive=True) if gravitational_parameter is None else gravitational_parameter

    kinetic_energy = sp.Rational(1, 2) * m * (r_dot**2 + r**2 * phi_dot**2)
    return LagrangianSystem(
        coordinates=chart.coordinates,
        velocities=chart.velocities,
        lagrangian=kinetic_energy + mu * m / r,
        time=chart.time,
    )


system = build_system()

