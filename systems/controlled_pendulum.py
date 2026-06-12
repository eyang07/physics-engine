from __future__ import annotations

import sympy as sp

from engine.dynamics import Box, ControlledFirstOrderSystem


def energy_expression(
    theta: sp.Symbol,
    omega: sp.Symbol,
    *,
    mass: sp.Expr | float,
    length: sp.Expr | float,
    gravity: sp.Expr | float,
) -> sp.Expr:
    """Mechanical energy E = m l^2 w^2 / 2 - m g l cos(theta)."""

    return mass * length**2 * omega**2 / 2 - mass * gravity * length * sp.cos(theta)


def build_system(
    mass: sp.Expr | float | None = None,
    length: sp.Expr | float | None = None,
    gravity: sp.Expr | float | None = None,
    damping: sp.Expr | float | None = None,
    torque_bound: float | None = None,
) -> ControlledFirstOrderSystem:
    """Torque-actuated damped pendulum (backend-only; not in the gallery).

    State (theta, omega), control u (torque at the pivot):
    theta' = omega
    omega' = -(g/l) sin(theta) - b omega / (m l^2) + u / (m l^2)
    """

    theta, omega = sp.symbols("theta omega", real=True)
    u = sp.Symbol("u", real=True)

    m_value = sp.Symbol("m", positive=True) if mass is None else mass
    l_value = sp.Symbol("l", positive=True) if length is None else length
    g_value = sp.Symbol("g", positive=True) if gravity is None else gravity
    b_value = sp.Symbol("b", nonnegative=True) if damping is None else damping

    rhs = (
        omega,
        -(g_value / l_value) * sp.sin(theta)
        - b_value * omega / (m_value * l_value**2)
        + u / (m_value * l_value**2),
    )

    return ControlledFirstOrderSystem(
        state=(theta, omega),
        controls=(u,),
        rhs=rhs,
        parameters=tuple(
            symbol
            for symbol in (m_value, l_value, g_value, b_value)
            if isinstance(symbol, sp.Symbol)
        ),
        control_bounds=None
        if torque_bound is None
        else Box(lower=(-torque_bound,), upper=(torque_bound,)),
    )


system = build_system()
