from __future__ import annotations

import sympy as sp

from engine.mechanics import LagrangianSystem
from engine.mechanics.coordinates import CoordinateChart


def build_system(
    transverse_moment: sp.Expr | float | None = None,
    axial_moment: sp.Expr | float | None = None,
    mass: sp.Expr | float | None = None,
    gravity: sp.Expr | float | None = None,
    pivot_distance: sp.Expr | float | None = None,
) -> LagrangianSystem:
    """The heavy symmetric top in z-x-z Euler angles.

    ``theta`` is the nutation angle measured from the upward vertical, ``phi``
    the precession about the vertical, and ``psi`` the spin about the symmetry
    axis. With transverse moment ``I1`` (= I2), axial moment ``I3``, weight
    ``M g`` and pivot-to-centre-of-mass distance ``ell``,

        L = 1/2 I1 (theta_dot^2 + phi_dot^2 sin(theta)^2)
            + 1/2 I3 (psi_dot + phi_dot cos(theta))^2
            - M g ell cos(theta).

    ``phi`` and ``psi`` are cyclic, so their conjugate momenta are conserved.
    """

    chart = CoordinateChart.from_names("theta phi psi")
    theta, phi, psi = chart.coordinates
    theta_dot, phi_dot, psi_dot = chart.velocities

    i1 = sp.Symbol("I1", positive=True) if transverse_moment is None else transverse_moment
    i3 = sp.Symbol("I3", positive=True) if axial_moment is None else axial_moment
    m = sp.Symbol("M", positive=True) if mass is None else mass
    g = sp.Symbol("g", positive=True) if gravity is None else gravity
    ell = sp.Symbol("ell", positive=True) if pivot_distance is None else pivot_distance

    spin = psi_dot + phi_dot * sp.cos(theta)
    kinetic_energy = (
        sp.Rational(1, 2) * i1 * (theta_dot**2 + phi_dot**2 * sp.sin(theta) ** 2)
        + sp.Rational(1, 2) * i3 * spin**2
    )
    potential_energy = m * g * ell * sp.cos(theta)
    lagrangian = kinetic_energy - potential_energy

    return LagrangianSystem(
        coordinates=chart.coordinates,
        velocities=chart.velocities,
        lagrangian=lagrangian,
        time=chart.time,
    )


def effective_potential(system: LagrangianSystem) -> sp.Expr:
    """Return V_eff(theta) after fixing the cyclic momenta p_phi and p_psi.

    The reduced radial-like energy balance reads
    ``1/2 I1 theta_dot^2 + V_eff(theta) = E`` with conserved constants
    ``p_phi`` (precession) and ``p_psi`` (spin) carried as free symbols.
    """

    theta = next(q for q in system.q if q.name == "theta")
    symbols = {symbol.name: symbol for symbol in system.lagrangian.free_symbols}
    i1 = symbols["I1"]
    m = symbols["M"]
    g = symbols["g"]
    ell = symbols["ell"]
    p_phi = sp.Symbol("p_phi")
    p_psi = sp.Symbol("p_psi")
    return (
        (p_phi - p_psi * sp.cos(theta)) ** 2 / (2 * i1 * sp.sin(theta) ** 2)
        + m * g * ell * sp.cos(theta)
    )


system = build_system()
