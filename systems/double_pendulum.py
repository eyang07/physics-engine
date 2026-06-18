from __future__ import annotations

import sympy as sp

from engine.mechanics import LagrangianSystem
from engine.mechanics.coordinates import CoordinateChart


def build_system(
    mass1: sp.Expr | float | None = None,
    mass2: sp.Expr | float | None = None,
    length1: sp.Expr | float | None = None,
    length2: sp.Expr | float | None = None,
    gravity: sp.Expr | float | None = None,
) -> LagrangianSystem:
    """Build the full nonlinear planar double pendulum.

    ``theta1`` and ``theta2`` are measured from the downward vertical for the
    upper and lower links respectively. The potential is zero at the hanging
    equilibrium.
    """

    chart = CoordinateChart.from_names("theta1 theta2")
    theta1, theta2 = chart.coordinates
    theta1_dot, theta2_dot = chart.velocities

    m1 = sp.Symbol("m1", positive=True) if mass1 is None else mass1
    m2 = sp.Symbol("m2", positive=True) if mass2 is None else mass2
    ell1 = sp.Symbol("ell1", positive=True) if length1 is None else length1
    ell2 = sp.Symbol("ell2", positive=True) if length2 is None else length2
    g = sp.Symbol("g", positive=True) if gravity is None else gravity

    angle_delta = theta1 - theta2
    kinetic_energy = (
        sp.Rational(1, 2) * (m1 + m2) * ell1**2 * theta1_dot**2
        + sp.Rational(1, 2) * m2 * ell2**2 * theta2_dot**2
        + m2 * ell1 * ell2 * theta1_dot * theta2_dot * sp.cos(angle_delta)
    )
    potential_energy = (
        (m1 + m2) * g * ell1 * (1 - sp.cos(theta1))
        + m2 * g * ell2 * (1 - sp.cos(theta2))
    )
    lagrangian = kinetic_energy - potential_energy

    return LagrangianSystem(
        coordinates=chart.coordinates,
        velocities=chart.velocities,
        lagrangian=lagrangian,
        time=chart.time,
    )


system = build_system()
