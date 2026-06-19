from __future__ import annotations

import sympy as sp

from engine.dynamics import FirstOrderSystem
from engine.mechanics.coordinates import time_symbol


def build_system(
    moment_1: sp.Expr | float | None = None,
    moment_2: sp.Expr | float | None = None,
    moment_3: sp.Expr | float | None = None,
) -> FirstOrderSystem:
    """Torque-free rigid body in principal body axes."""

    omega_1, omega_2, omega_3 = sp.symbols("omega_1 omega_2 omega_3", real=True)
    i1 = sp.Symbol("I1", positive=True) if moment_1 is None else moment_1
    i2 = sp.Symbol("I2", positive=True) if moment_2 is None else moment_2
    i3 = sp.Symbol("I3", positive=True) if moment_3 is None else moment_3

    rhs = (
        (i2 - i3) * omega_2 * omega_3 / i1,
        (i3 - i1) * omega_3 * omega_1 / i2,
        (i1 - i2) * omega_1 * omega_2 / i3,
    )
    parameters = tuple(symbol for symbol in (i1, i2, i3) if isinstance(symbol, sp.Symbol))
    return FirstOrderSystem(
        state=(omega_1, omega_2, omega_3),
        rhs=rhs,
        parameters=parameters,
        time=time_symbol(),
        simplify_derivatives=False,
    )


def rotational_energy(system: FirstOrderSystem) -> sp.Expr:
    i1, i2, i3 = _principal_moments(system)
    omega_1, omega_2, omega_3 = system.state
    return sp.Rational(1, 2) * (
        i1 * omega_1**2 + i2 * omega_2**2 + i3 * omega_3**2
    )


def angular_momentum_magnitude(system: FirstOrderSystem) -> sp.Expr:
    i1, i2, i3 = _principal_moments(system)
    omega_1, omega_2, omega_3 = system.state
    return sp.sqrt((i1 * omega_1) ** 2 + (i2 * omega_2) ** 2 + (i3 * omega_3) ** 2)


def _principal_moments(system: FirstOrderSystem) -> tuple[sp.Symbol, sp.Symbol, sp.Symbol]:
    by_name = {symbol.name: symbol for symbol in system.parameters}
    missing = {"I1", "I2", "I3"} - set(by_name)
    if missing:
        names = ", ".join(sorted(missing))
        raise ValueError(f"system is missing principal inertia parameters: {names}")
    return by_name["I1"], by_name["I2"], by_name["I3"]


system = build_system()
