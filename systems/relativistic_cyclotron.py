from __future__ import annotations

from typing import Sequence

import numpy as np
import sympy as sp

from engine.dynamics import FirstOrderSystem
from engine.electrodynamics import electromagnetic_invariants, lorentz_force_system


def build_system() -> FirstOrderSystem:
    """Relativistic charged particle in a uniform magnetic field.

    The state is ``(x^mu, p^mu)`` with ``x0 = c t`` and ``c = 1``. The
    independent variable is proper time ``tau``. The uniform field is
    ``E = 0`` and ``B = B_z k``.
    """

    q = sp.Symbol("q", real=True)
    m = sp.Symbol("m", positive=True)
    b_z = sp.Symbol("B_z", real=True)
    return lorentz_force_system(
        (0, 0, 0),
        (0, 0, b_z),
        charge=q,
        mass=m,
        light_speed=sp.Integer(1),
    )


def initial_state(
    *,
    position: Sequence[float] = (0.0, 0.85, 0.0, -1.2),
    velocity: Sequence[float] = (0.0, 0.42, 0.18),
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


def mass_shell_expression(system: FirstOrderSystem) -> sp.Expr:
    """Kinetic mass shell ``p^mu p_mu + m^2`` in mostly-plus signature."""

    p0, p1, p2, p3 = system.state[4:]
    m = next(symbol for symbol in system.parameters if symbol.name == "m")
    return sp.simplify(-(p0**2) + p1**2 + p2**2 + p3**2 + m**2)


def four_velocity_norm_expression(system: FirstOrderSystem) -> sp.Expr:
    """Symbolic ``u^mu u_mu`` for ``u^mu = p^mu / m``."""

    p0, p1, p2, p3 = system.state[4:]
    m = next(symbol for symbol in system.parameters if symbol.name == "m")
    return sp.simplify((-(p0**2) + p1**2 + p2**2 + p3**2) / m**2)


def p_z_expression(system: FirstOrderSystem) -> sp.Expr:
    """Longitudinal momentum conserved by uniform ``B_z``."""

    return system.state[7]


def faraday_scalar_expression(system: FirstOrderSystem) -> sp.Expr:
    """EM scalar invariant ``F_mu_nu F^mu_nu`` for the uniform field."""

    b_z = next(symbol for symbol in system.parameters if symbol.name == "B_z")
    scalar, _dot = electromagnetic_invariants((0, 0, 0), (0, 0, b_z))
    return scalar


def electric_magnetic_invariant_expression(system: FirstOrderSystem) -> sp.Expr:
    """EM pseudoscalar invariant in ``E . B`` normalization."""

    b_z = next(symbol for symbol in system.parameters if symbol.name == "B_z")
    _scalar, dot = electromagnetic_invariants((0, 0, 0), (0, 0, b_z))
    return dot


def gyrofrequency_expression(system: FirstOrderSystem) -> sp.Expr:
    """Coordinate-time gyrofrequency ``omega = q B_z / p0 = q B_z / (gamma m)``."""

    p0 = system.state[4]
    b_z = next(symbol for symbol in system.parameters if symbol.name == "B_z")
    q = next(symbol for symbol in system.parameters if symbol.name == "q")
    return sp.simplify(q * b_z / p0)


def coordinate_time_series(states: Sequence[Sequence[float]]) -> list[float]:
    """Recover coordinate time ``t = x0`` in ``c = 1`` units."""

    return np.asarray(states, dtype=float)[:, 0].astype(float).tolist()


def four_velocity_series(
    states: Sequence[Sequence[float]],
    *,
    mass: float,
) -> list[list[float]]:
    """Return ``u^mu = p^mu / m`` from the exported four-momentum."""

    if mass <= 0.0:
        raise ValueError("mass must be positive")
    momenta = np.asarray(states, dtype=float)[:, 4:]
    return (momenta / mass).astype(float).tolist()


def mass_shell_series(
    states: Sequence[Sequence[float]],
    *,
    mass: float,
) -> list[float]:
    """Sample ``p^mu p_mu + m^2`` along the rollout."""

    state_array = np.asarray(states, dtype=float)
    momenta = state_array[:, 4:]
    values = -momenta[:, 0] ** 2 + np.sum(momenta[:, 1:] ** 2, axis=1) + mass**2
    return values.astype(float).tolist()


def four_velocity_norm_series(
    states: Sequence[Sequence[float]],
    *,
    mass: float,
) -> list[float]:
    """Sample ``u^mu u_mu`` along the rollout."""

    momenta = np.asarray(states, dtype=float)[:, 4:]
    values = (-momenta[:, 0] ** 2 + np.sum(momenta[:, 1:] ** 2, axis=1)) / mass**2
    return values.astype(float).tolist()


def p_z_series(states: Sequence[Sequence[float]]) -> list[float]:
    """Sample the longitudinal four-momentum component."""

    return np.asarray(states, dtype=float)[:, 7].astype(float).tolist()


def em_invariant_series(
    sample_count: int,
    *,
    magnetic_field_z: float,
) -> dict[str, list[float]]:
    """Return constant measured EM invariant series."""

    scalar = float(2.0 * magnetic_field_z**2)
    dot = 0.0
    return {
        "faraday_scalar": [scalar] * sample_count,
        "electric_magnetic": [dot] * sample_count,
    }


def spacetime_renderer_hints(states: Sequence[Sequence[float]]) -> dict[str, object]:
    """Renderer-owned framing hints for the uniform-field trajectory."""

    state_array = np.asarray(states, dtype=float)
    x1 = state_array[:, 1]
    x2 = state_array[:, 2]
    x3 = state_array[:, 3]
    extent = float(max(np.max(np.abs(x1)), np.max(np.abs(x2)), 1.0))
    z_min = float(min(np.min(x3), -1.2))
    z_max = float(max(np.max(x3), 1.2))
    return {
        "diagram": "covariant-em-cyclotron",
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
                "kind": "uniformMagneticField",
                "direction": [0.0, 0.0, 1.0],
                "source": "trajectory.metadata.fields.magnetic",
            }
        ],
    }


def worldline_payload(
    time: Sequence[float],
    states: Sequence[Sequence[float]],
    *,
    mass: float,
) -> dict[str, object]:
    """Backend-owned worldline channel consumed by the viewer."""

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


system = build_system()
