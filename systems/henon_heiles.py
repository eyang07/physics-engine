from __future__ import annotations

import sympy as sp

from engine.mechanics import LagrangianSystem
from engine.mechanics.coordinates import CoordinateChart


def build_system(
    mass: sp.Expr | float | None = None,
    stiffness: sp.Expr | float | None = None,
    coupling: sp.Expr | float | None = None,
) -> LagrangianSystem:
    """The two-degree Hénon-Heiles Hamiltonian system."""

    chart = CoordinateChart.from_names("x y")
    x, y = chart.coordinates
    x_dot, y_dot = chart.velocities

    m = sp.Symbol("m", positive=True) if mass is None else mass
    k = sp.Symbol("k", positive=True) if stiffness is None else stiffness
    lam = sp.Symbol("lambda", real=True) if coupling is None else coupling

    kinetic_energy = sp.Rational(1, 2) * m * (x_dot**2 + y_dot**2)
    potential_energy = sp.Rational(1, 2) * k * (x**2 + y**2) + lam * (
        x**2 * y - sp.Rational(1, 3) * y**3
    )
    return LagrangianSystem(
        coordinates=chart.coordinates,
        velocities=chart.velocities,
        lagrangian=kinetic_energy - potential_energy,
        time=chart.time,
    )


system = build_system()
