from __future__ import annotations

import sympy as sp

from engine.mechanics import LagrangianSystem
from engine.mechanics.coordinates import CoordinateChart


def build_system(
    mass: sp.Expr | float | None = None,
    radius: sp.Expr | float | None = None,
) -> LagrangianSystem:
    """Geodesic motion on a sphere in intrinsic spherical coordinates.

    The metric is
    ds^2 = R^2 dtheta^2 + R^2 sin(theta)^2 dphi^2,
    so the free-particle Lagrangian is L = 1/2 m g_ij qdot^i qdot^j.
    """

    chart = CoordinateChart.from_names("theta phi")
    theta, _phi = chart.coordinates
    theta_dot, phi_dot = chart.velocities

    m = sp.Symbol("m", positive=True) if mass is None else mass
    radius_value = sp.Symbol("R", positive=True) if radius is None else radius

    lagrangian = (
        sp.Rational(1, 2)
        * m
        * radius_value**2
        * (theta_dot**2 + sp.sin(theta) ** 2 * phi_dot**2)
    )

    return LagrangianSystem(
        coordinates=chart.coordinates,
        velocities=chart.velocities,
        lagrangian=lagrangian,
        time=chart.time,
    )


system = build_system()

