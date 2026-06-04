from __future__ import annotations

import sympy as sp

from engine.mechanics import LagrangianSystem
from engine.mechanics.coordinates import CoordinateChart


def build_uniform_magnetic_field_system(
    mass: sp.Expr | float | None = None,
    charge: sp.Expr | float | None = None,
    magnetic_field_z: sp.Expr | float | None = None,
) -> LagrangianSystem:
    """Charged particle in a uniform magnetic field B = B_z k.

    We use the symmetric vector potential
    A = 1/2 B x r = (-B_z y / 2, B_z x / 2, 0)
    and scalar potential phi = 0, so
    L = 1/2 m |v|^2 + q A(r) . v.
    """

    chart = CoordinateChart.from_names("x y z")
    x, y, _z = chart.coordinates
    x_dot, y_dot, z_dot = chart.velocities

    m = sp.Symbol("m", positive=True) if mass is None else mass
    q = sp.Symbol("q", real=True) if charge is None else charge
    b_z = sp.Symbol("B_z", real=True) if magnetic_field_z is None else magnetic_field_z

    kinetic_energy = sp.Rational(1, 2) * m * (x_dot**2 + y_dot**2 + z_dot**2)
    vector_potential_coupling = q * (
        (-b_z * y / 2) * x_dot + (b_z * x / 2) * y_dot
    )
    lagrangian = kinetic_energy + vector_potential_coupling

    return LagrangianSystem(
        coordinates=chart.coordinates,
        velocities=chart.velocities,
        lagrangian=lagrangian,
        time=chart.time,
    )


system = build_uniform_magnetic_field_system()

