from __future__ import annotations

from typing import Sequence

import numpy as np
import sympy as sp

from engine.dynamics import FirstOrderSystem
from engine.electrodynamics import electromagnetic_invariants, lorentz_force_system
from engine.relativity import ProperTimeWorldline


def build_system() -> FirstOrderSystem:
    """Relativistic charged particle in a configurable uniform static EM field.

    The state is ``(x^mu, p^mu)`` with ``x0 = c t`` and ``c = 1``. The
    independent variable is proper time ``tau``. The field parameters are the
    static uniform components ``(E_x, E_y, E_z)`` and ``(B_x, B_y, B_z)``.
    """

    q = sp.Symbol("q", real=True)
    m = sp.Symbol("m", positive=True)
    e_x, e_y, e_z = sp.symbols("E_x E_y E_z", real=True)
    b_x, b_y, b_z = sp.symbols("B_x B_y B_z", real=True)
    return lorentz_force_system(
        (e_x, e_y, e_z),
        (b_x, b_y, b_z),
        charge=q,
        mass=m,
        light_speed=sp.Integer(1),
    )


def initial_state(
    *,
    position: Sequence[float] = (0.0, 0.35, -0.2, -0.9),
    velocity: Sequence[float] = (0.08, 0.32, 0.16),
    mass: float = 1.0,
) -> list[float]:
    """Return an on-shell ``(x^mu, p^mu)`` initial state from coordinate velocity."""

    if len(position) != 4:
        raise ValueError("position must have four spacetime components")
    spatial_velocity = np.asarray(velocity, dtype=float)
    if spatial_velocity.shape != (3,):
        raise ValueError("velocity must have three spatial components")
    if mass <= 0.0:
        raise ValueError("mass must be positive")
    speed_squared = float(np.dot(spatial_velocity, spatial_velocity))
    if speed_squared >= 1.0:
        raise ValueError("coordinate velocity must be subluminal in c = 1 units")

    gamma = 1.0 / np.sqrt(1.0 - speed_squared)
    momentum = [mass * gamma, *(mass * gamma * component for component in spatial_velocity)]
    return [float(component) for component in position] + [float(component) for component in momentum]


def _parameter(system: FirstOrderSystem, name: str) -> sp.Symbol:
    return next(symbol for symbol in system.parameters if symbol.name == name)


def mass_shell_expression(system: FirstOrderSystem) -> sp.Expr:
    p0, p1, p2, p3 = system.state[4:]
    m = _parameter(system, "m")
    return sp.simplify(-(p0**2) + p1**2 + p2**2 + p3**2 + m**2)


def four_velocity_norm_expression(system: FirstOrderSystem) -> sp.Expr:
    p0, p1, p2, p3 = system.state[4:]
    m = _parameter(system, "m")
    return sp.simplify((-(p0**2) + p1**2 + p2**2 + p3**2) / m**2)


def field_components(system: FirstOrderSystem) -> tuple[tuple[sp.Expr, ...], tuple[sp.Expr, ...]]:
    electric = tuple(_parameter(system, name) for name in ("E_x", "E_y", "E_z"))
    magnetic = tuple(_parameter(system, name) for name in ("B_x", "B_y", "B_z"))
    return electric, magnetic


def faraday_scalar_expression(system: FirstOrderSystem) -> sp.Expr:
    electric, magnetic = field_components(system)
    scalar, _dot = electromagnetic_invariants(electric, magnetic)
    return sp.expand(scalar)


def electric_magnetic_invariant_expression(system: FirstOrderSystem) -> sp.Expr:
    electric, magnetic = field_components(system)
    _scalar, dot = electromagnetic_invariants(electric, magnetic)
    return sp.expand(dot)


def nonrelativistic_spatial_force(
    system: FirstOrderSystem,
) -> tuple[sp.Expr, sp.Expr, sp.Expr]:
    """Return ``q(E + v x B)`` in the low-velocity limit."""

    q = _parameter(system, "q")
    electric, magnetic = field_components(system)
    vx, vy, vz = sp.symbols("v_x v_y v_z", real=True)
    ex, ey, ez = electric
    bx, by, bz = magnetic
    return (
        sp.simplify(q * (ex + vy * bz - vz * by)),
        sp.simplify(q * (ey + vz * bx - vx * bz)),
        sp.simplify(q * (ez + vx * by - vy * bx)),
    )


def coordinate_time_series(states: Sequence[Sequence[float]]) -> list[float]:
    return np.asarray(states, dtype=float)[:, 0].astype(float).tolist()


def four_velocity_series(
    states: Sequence[Sequence[float]],
    *,
    mass: float,
) -> list[list[float]]:
    if mass <= 0.0:
        raise ValueError("mass must be positive")
    momenta = np.asarray(states, dtype=float)[:, 4:]
    return (momenta / mass).astype(float).tolist()


def mass_shell_series(
    states: Sequence[Sequence[float]],
    *,
    mass: float,
) -> list[float]:
    momenta = np.asarray(states, dtype=float)[:, 4:]
    values = -momenta[:, 0] ** 2 + np.sum(momenta[:, 1:] ** 2, axis=1) + mass**2
    return values.astype(float).tolist()


def four_velocity_norm_series(
    states: Sequence[Sequence[float]],
    *,
    mass: float,
) -> list[float]:
    momenta = np.asarray(states, dtype=float)[:, 4:]
    values = (-momenta[:, 0] ** 2 + np.sum(momenta[:, 1:] ** 2, axis=1)) / mass**2
    return values.astype(float).tolist()


def em_invariant_series(
    sample_count: int,
    *,
    electric: Sequence[float],
    magnetic: Sequence[float],
) -> dict[str, list[float]]:
    e = np.asarray(electric, dtype=float)
    b = np.asarray(magnetic, dtype=float)
    scalar = float(2.0 * (np.dot(b, b) - np.dot(e, e)))
    dot = float(np.dot(e, b))
    return {
        "faraday_scalar": [scalar] * sample_count,
        "electric_magnetic": [dot] * sample_count,
    }


def spacetime_renderer_hints(states: Sequence[Sequence[float]]) -> dict[str, object]:
    state_array = np.asarray(states, dtype=float)
    x1 = state_array[:, 1]
    x2 = state_array[:, 2]
    x3 = state_array[:, 3]
    extent = float(max(np.max(np.abs(x1)), np.max(np.abs(x2)), 1.0))
    z_min = float(min(np.min(x3), -1.0))
    z_max = float(max(np.max(x3), 1.0))
    return {
        "diagram": "covariant-em-general-charged-particle",
        "bounds": {
            "x": [-extent, extent],
            "y": [-extent, extent],
            "z": [z_min, z_max],
        },
        "axes": {
            "space": ["x1", "x2", "x3"],
            "momentum": ["p_x1", "p_x2", "p_x3"],
            "parameter": "tau",
            "coordinateTime": "x0",
        },
        "referenceGeometry": [
            {
                "kind": "uniformElectricField",
                "source": "trajectory.metadata.fields.electric",
            },
            {
                "kind": "uniformMagneticField",
                "source": "trajectory.metadata.fields.magnetic",
            },
        ],
    }


def worldline_payload(
    time: Sequence[float],
    states: Sequence[Sequence[float]],
    *,
    mass: float,
) -> dict[str, object]:
    state_array = np.asarray(states, dtype=float)
    return {
        "kind": "proper-time-covariant-em-worldline",
        "signature": "(-,+,+,+)",
        "units": "c=1",
        "parameter": "tau",
        "properTime": np.asarray(time, dtype=float).astype(float).tolist(),
        "coordinateTime": coordinate_time_series(states),
        "spatialCoordinates": ["x1", "x2", "x3"],
        "points": state_array[:, :4].astype(float).tolist(),
        "fourMomentum": state_array[:, 4:].astype(float).tolist(),
        "fourVelocity": four_velocity_series(states, mass=mass),
        "massShellSeries": "mass_shell",
        "fourVelocityNormSeries": "four_velocity_norm",
        "evaluation": "measured-rollout",
    }


def low_velocity_limit_matches_newtonian_magnetic_field() -> tuple[sp.Expr, sp.Expr, sp.Expr]:
    """Return residuals against the Newtonian uniform-``B_z`` charged-particle force."""

    system = build_system()
    vx, vy, _vz = sp.symbols("v_x v_y v_z", real=True)
    q = _parameter(system, "q")
    m = _parameter(system, "m")
    b_z = _parameter(system, "B_z")
    force = nonrelativistic_spatial_force(system)
    substitutions = {
        _parameter(system, "E_x"): 0,
        _parameter(system, "E_y"): 0,
        _parameter(system, "E_z"): 0,
        _parameter(system, "B_x"): 0,
        _parameter(system, "B_y"): 0,
    }
    acceleration = tuple(sp.simplify(component.subs(substitutions) / m) for component in force)
    expected = (q * b_z * vy / m, -q * b_z * vx / m, sp.Integer(0))
    return tuple(
        sp.simplify(component - expected_component)
        for component, expected_component in zip(acceleration, expected)
    )


system = build_system()
