from __future__ import annotations

import sympy as sp

from engine.mechanics import LagrangianSystem
from engine.mechanics.coordinates import CoordinateChart


def build_system(
    mass: sp.Expr | float | None = None,
    radius: sp.Expr | float | None = None,
    gravity: sp.Expr | float | None = None,
    angular_speed: sp.Expr | float | None = None,
) -> LagrangianSystem:
    """A bead constrained to a vertical hoop rotating about the vertical axis.

    The coordinate theta is measured from the downward vertical direction.
    After substituting the prescribed azimuth phi = Omega t, the reduced
    Lagrangian is autonomous:

    L = 1/2 m R^2 theta_dot^2
        + 1/2 m R^2 Omega^2 sin(theta)^2
        + m g R cos(theta).
    """

    chart = CoordinateChart.from_names("theta")
    (theta,) = chart.coordinates
    (theta_dot,) = chart.velocities

    m = sp.Symbol("m", positive=True) if mass is None else mass
    radius_value = sp.Symbol("R", positive=True) if radius is None else radius
    g = sp.Symbol("g", positive=True) if gravity is None else gravity
    omega = sp.Symbol("Omega", real=True) if angular_speed is None else angular_speed

    lagrangian = (
        sp.Rational(1, 2) * m * radius_value**2 * theta_dot**2
        + sp.Rational(1, 2) * m * radius_value**2 * omega**2 * sp.sin(theta) ** 2
        + m * g * radius_value * sp.cos(theta)
    )

    return LagrangianSystem(
        coordinates=chart.coordinates,
        velocities=chart.velocities,
        lagrangian=lagrangian,
        time=chart.time,
    )


system = build_system()
