from __future__ import annotations

from typing import Sequence

import numpy as np
import sympy as sp

from engine.dynamics import FirstOrderSystem
from engine.mechanics.coordinates import coordinate_symbols, momentum_symbol, time_symbol


def build_system() -> FirstOrderSystem:
    """Relativistic particle in a one-dimensional static harmonic potential.

    The state is ``(x0, x1, p_x0, p_x1)`` with ``x0 = c t``. The momentum
    components are the kinetic four-momentum, and the potential is
    ``V(x1) = k x1^2 / 2``. The independent variable is coordinate time ``t``.
    """

    x0, x1 = coordinate_symbols("x0 x1")
    p0 = momentum_symbol(x0)
    p1 = momentum_symbol(x1)
    t = time_symbol("t")
    mass = sp.Symbol("m", positive=True)
    light_speed = sp.Symbol("c", positive=True)
    stiffness = sp.Symbol("k", positive=True)

    force = -sp.diff(potential_energy_expression(x1, stiffness), x1)
    positive_energy = sp.sqrt(p1**2 + (mass * light_speed) ** 2)
    rhs = (
        light_speed,
        sp.simplify(light_speed * p1 / positive_energy),
        sp.simplify(p1 * force / p0),
        force,
    )
    return FirstOrderSystem(
        state=(x0, x1, p0, p1),
        rhs=rhs,
        parameters=(light_speed, stiffness, mass),
        time=t,
    )


def potential_energy_expression(
    position: sp.Expr,
    stiffness: sp.Expr | float | None = None,
) -> sp.Expr:
    """Static scalar potential ``V = k x^2 / 2``."""

    k = sp.Symbol("k", positive=True) if stiffness is None else sp.sympify(stiffness)
    return sp.simplify(sp.Rational(1, 2) * k * position**2)


def total_energy_expression(system: FirstOrderSystem) -> sp.Expr:
    """Coordinate-time energy ``E = c p^0 + V(x)``."""

    _x0, x1, p0, _p1 = system.state
    c = next(symbol for symbol in system.parameters if symbol.name == "c")
    k = next(symbol for symbol in system.parameters if symbol.name == "k")
    return sp.simplify(c * p0 + potential_energy_expression(x1, k))


def mass_shell_expression(system: FirstOrderSystem) -> sp.Expr:
    """Kinetic mass shell ``p^mu p_mu + m^2 c^2`` in mostly-plus signature."""

    _x0, _x1, p0, p1 = system.state
    c = next(symbol for symbol in system.parameters if symbol.name == "c")
    m = next(symbol for symbol in system.parameters if symbol.name == "m")
    return sp.simplify(-(p0**2) + p1**2 + (m * c) ** 2)


def proper_interval_rate_expression(system: FirstOrderSystem) -> sp.Expr:
    """Symbolic ``eta_mu_nu u^mu u^nu`` for ``u^mu = p^mu / m``."""

    _x0, _x1, p0, p1 = system.state
    m = next(symbol for symbol in system.parameters if symbol.name == "m")
    return sp.simplify((-(p0**2) + p1**2) / m**2)


def coordinate_velocity_expression(system: FirstOrderSystem) -> sp.Expr:
    """Return ``dx1/dt`` from the relativistic Hamiltonian flow."""

    return system.rhs[1]


def newtonian_limit_rhs(system: FirstOrderSystem) -> tuple[sp.Expr, sp.Expr]:
    """Leading non-relativistic oscillator equations ``dx/dt, dp/dt``."""

    _x0, x1, _p0, p1 = system.state
    k = next(symbol for symbol in system.parameters if symbol.name == "k")
    m = next(symbol for symbol in system.parameters if symbol.name == "m")
    return (sp.simplify(p1 / m), sp.simplify(-k * x1))


def initial_state(
    *,
    position: float = 0.9,
    momentum: float = 0.32,
    mass: float = 1.0,
    light_speed: float = 1.0,
) -> list[float]:
    """Start on the positive-energy mass shell at ``x0 = 0``."""

    if mass <= 0.0:
        raise ValueError("mass must be positive")
    if light_speed <= 0.0:
        raise ValueError("light_speed must be positive")
    p0 = np.sqrt(momentum**2 + (mass * light_speed) ** 2)
    return [0.0, float(position), float(p0), float(momentum)]


def mass_shell_series(
    states: Sequence[Sequence[float]],
    *,
    mass: float,
    light_speed: float,
) -> list[float]:
    """Sample ``p^mu p_mu + m^2 c^2`` along the rollout."""

    state_array = np.asarray(states, dtype=float)
    if state_array.ndim != 2 or state_array.shape[1] != 4:
        raise ValueError("states must have shape (sample_count, 4)")
    p0 = state_array[:, 2]
    p1 = state_array[:, 3]
    values = -(p0**2) + p1**2 + (mass * light_speed) ** 2
    return values.astype(float).tolist()


def total_energy_series(
    states: Sequence[Sequence[float]],
    *,
    stiffness: float,
    light_speed: float,
) -> list[float]:
    """Sample coordinate-time energy ``c p^0 + k x^2 / 2``."""

    state_array = np.asarray(states, dtype=float)
    if state_array.ndim != 2 or state_array.shape[1] != 4:
        raise ValueError("states must have shape (sample_count, 4)")
    position = state_array[:, 1]
    p0 = state_array[:, 2]
    values = light_speed * p0 + 0.5 * stiffness * position**2
    return values.astype(float).tolist()


def proper_interval_rate_series(
    states: Sequence[Sequence[float]],
    *,
    mass: float,
) -> list[float]:
    """Sample ``eta_mu_nu u^mu u^nu`` for ``u^mu = p^mu / m``."""

    if mass <= 0.0:
        raise ValueError("mass must be positive")
    state_array = np.asarray(states, dtype=float)
    if state_array.ndim != 2 or state_array.shape[1] != 4:
        raise ValueError("states must have shape (sample_count, 4)")
    p0 = state_array[:, 2]
    p1 = state_array[:, 3]
    values = (-(p0**2) + p1**2) / mass**2
    return values.astype(float).tolist()


def coordinate_time_series(states: Sequence[Sequence[float]], *, light_speed: float) -> list[float]:
    """Recover coordinate time ``t = x0 / c``."""

    if light_speed <= 0.0:
        raise ValueError("light_speed must be positive")
    return (np.asarray(states, dtype=float)[:, 0] / light_speed).astype(float).tolist()


def proper_time_series(
    coordinate_time: Sequence[float],
    states: Sequence[Sequence[float]],
    *,
    mass: float,
    light_speed: float,
) -> list[float]:
    """Accumulate proper time from ``d tau / dt = m c / p^0``."""

    if mass <= 0.0:
        raise ValueError("mass must be positive")
    if light_speed <= 0.0:
        raise ValueError("light_speed must be positive")
    time = np.asarray(coordinate_time, dtype=float)
    state_array = np.asarray(states, dtype=float)
    if time.ndim != 1 or state_array.ndim != 2 or len(time) != state_array.shape[0]:
        raise ValueError("coordinate_time and states must have matching sample counts")
    rate = mass * light_speed / state_array[:, 2]
    proper_time = np.zeros_like(time)
    for index in range(1, len(time)):
        dt = time[index] - time[index - 1]
        proper_time[index] = proper_time[index - 1] + 0.5 * dt * (
            rate[index - 1] + rate[index]
        )
    return proper_time.astype(float).tolist()


def four_velocity_series(
    states: Sequence[Sequence[float]],
    *,
    mass: float,
) -> list[list[float]]:
    """Return ``u^mu = p^mu / m`` from the exported kinetic four-momentum."""

    if mass <= 0.0:
        raise ValueError("mass must be positive")
    momenta = np.asarray(states, dtype=float)[:, 2:]
    return (momenta / mass).astype(float).tolist()


def spacetime_renderer_hints(states: Sequence[Sequence[float]]) -> dict[str, object]:
    """Renderer-owned framing hints for a 1+1 spacetime diagram."""

    state_array = np.asarray(states, dtype=float)
    x0 = state_array[:, 0]
    x1 = state_array[:, 1]
    spatial_extent = float(max(np.max(np.abs(x1)), 1.0))
    time_extent = float(max(np.max(x0), 1.0))
    return {
        "diagram": "minkowski-1-plus-1-potential",
        "bounds": {
            "time": [0.0, time_extent],
            "x": [-spatial_extent, spatial_extent],
        },
        "axes": {
            "time": "x0",
            "space": ["x1"],
            "parameter": "t",
        },
        "referenceGeometry": [
            {
                "kind": "lightCone",
                "apex": [0.0, 0.0],
                "speed": 1.0,
            },
            {
                "kind": "staticPotential",
                "potential": "V(x1) = k x1^2 / 2",
            },
        ],
    }


def worldline_payload(
    time: Sequence[float],
    states: Sequence[Sequence[float]],
    *,
    mass: float,
    light_speed: float,
) -> dict[str, object]:
    """Backend-owned worldline channel consumed by the viewer."""

    state_array = np.asarray(states, dtype=float)
    coordinate_time = coordinate_time_series(states, light_speed=light_speed)
    return {
        "kind": "coordinate-time-worldline",
        "signature": "(-,+)",
        "units": "c=1",
        "parameter": "t",
        "coordinateTime": "x0",
        "spatialCoordinates": ["x1"],
        "properTime": proper_time_series(
            time,
            states,
            mass=mass,
            light_speed=light_speed,
        ),
        "points": state_array[:, :2].astype(float).tolist(),
        "fourMomentum": state_array[:, 2:].astype(float).tolist(),
        "fourVelocity": four_velocity_series(states, mass=mass),
        "intervalRateSeries": "proper_interval_rate",
        "energySeries": "total_energy",
        "massShellSeries": "mass_shell",
        "evaluation": "measured-rollout",
        "coordinateTimeSamples": coordinate_time,
    }


system = build_system()
