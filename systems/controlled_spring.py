from __future__ import annotations

import sympy as sp

from engine.dynamics import Box, ControlledFirstOrderSystem


def energy_expression(
    x: sp.Symbol,
    v: sp.Symbol,
    *,
    mass: sp.Expr | float,
    stiffness: sp.Expr | float,
) -> sp.Expr:
    """Mechanical energy E = m v^2 / 2 + k x^2 / 2."""

    return mass * v**2 / 2 + stiffness * x**2 / 2


def build_system(
    mass: sp.Expr | float | None = None,
    stiffness: sp.Expr | float | None = None,
    damping: sp.Expr | float | None = None,
    force_bound: float | None = None,
) -> ControlledFirstOrderSystem:
    """Force-actuated damped spring-mass system (backend-only).

    State (x, v), control u (applied force):
    x' = v
    v' = -(k/m) x - (c/m) v + u/m
    """

    x, v = sp.symbols("x v", real=True)
    u = sp.Symbol("u", real=True)

    m_value = sp.Symbol("m", positive=True) if mass is None else mass
    k_value = sp.Symbol("k", positive=True) if stiffness is None else stiffness
    c_value = sp.Symbol("c", nonnegative=True) if damping is None else damping

    rhs = (
        v,
        -(k_value / m_value) * x - (c_value / m_value) * v + u / m_value,
    )

    return ControlledFirstOrderSystem(
        state=(x, v),
        controls=(u,),
        rhs=rhs,
        parameters=tuple(
            symbol
            for symbol in (m_value, k_value, c_value)
            if isinstance(symbol, sp.Symbol)
        ),
        control_bounds=None
        if force_bound is None
        else Box(lower=(-force_bound,), upper=(force_bound,)),
    )


system = build_system()
