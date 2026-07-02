from __future__ import annotations

from typing import Sequence

import numpy as np
import sympy as sp

from engine.dynamics import FirstOrderSystem
from engine.electrodynamics import electromagnetic_invariants, lorentz_force_system


def build_system() -> FirstOrderSystem:
    """Relativistic charged particle in crossed uniform ``E`` and ``B`` fields.

    The state is ``(x^mu, p^mu)`` with ``x0 = c t`` and ``c = 1``. The fields
    are ``E = E_x i`` and ``B = B_z k``, so the analytic drift is
    ``E x B / B^2 = -(E_x / B_z) j``.
    """

    q = sp.Symbol("q", real=True)
    m = sp.Symbol("m", positive=True)
    e_x = sp.Symbol("E_x", real=True)
    b_z = sp.Symbol("B_z", real=True, nonzero=True)
    return lorentz_force_system(
        (e_x, 0, 0),
        (0, 0, b_z),
        charge=q,
        mass=m,
        light_speed=sp.Integer(1),
    )


def analytic_drift_velocity(
    *,
    electric_field_x: float,
    magnetic_field_z: float,
) -> tuple[float, float, float]:
    """Return ``E x B / B^2`` for ``E = E_x i`` and ``B = B_z k``."""

    if magnetic_field_z == 0.0:
        raise ValueError("magnetic_field_z must be nonzero")
    return (0.0, -float(electric_field_x) / float(magnetic_field_z), 0.0)


def initial_state(
    *,
    position: Sequence[float] = (0.0, 0.0, 0.0, -0.8),
    electric_field_x: float = 0.25,
    magnetic_field_z: float = 1.0,
    parallel_velocity_z: float = 0.0,
    mass: float = 1.0,
) -> list[float]:
    """Return an on-shell initial state moving at the analytic drift velocity."""

    if len(position) != 4:
        raise ValueError("position must have four spacetime components")
    if mass <= 0.0:
        raise ValueError("mass must be positive")
    drift = analytic_drift_velocity(
        electric_field_x=electric_field_x,
        magnetic_field_z=magnetic_field_z,
    )
    spatial_velocity = np.asarray(
        (drift[0], drift[1], float(parallel_velocity_z)),
        dtype=float,
    )
    speed_squared = float(np.dot(spatial_velocity, spatial_velocity))
    if speed_squared >= 1.0:
        raise ValueError("drift plus parallel velocity must be subluminal")

    gamma = 1.0 / np.sqrt(1.0 - speed_squared)
    momentum = [mass * gamma, *(mass * gamma * component for component in spatial_velocity)]
    return [float(component) for component in position] + [float(component) for component in momentum]


def mass_shell_expression(system: FirstOrderSystem) -> sp.Expr:
    p0, p1, p2, p3 = system.state[4:]
    m = next(symbol for symbol in system.parameters if symbol.name == "m")
    return sp.simplify(-(p0**2) + p1**2 + p2**2 + p3**2 + m**2)


def four_velocity_norm_expression(system: FirstOrderSystem) -> sp.Expr:
    p0, p1, p2, p3 = system.state[4:]
    m = next(symbol for symbol in system.parameters if symbol.name == "m")
    return sp.simplify((-(p0**2) + p1**2 + p2**2 + p3**2) / m**2)


def p_z_expression(system: FirstOrderSystem) -> sp.Expr:
    return system.state[7]


def drift_velocity_y_expression(system: FirstOrderSystem) -> sp.Expr:
    """Symbolic analytic drift component ``(E x B / B^2)_y``."""

    e_x = next(symbol for symbol in system.parameters if symbol.name == "E_x")
    b_z = next(symbol for symbol in system.parameters if symbol.name == "B_z")
    return sp.simplify(-e_x / b_z)


def faraday_scalar_expression(system: FirstOrderSystem) -> sp.Expr:
    e_x = next(symbol for symbol in system.parameters if symbol.name == "E_x")
    b_z = next(symbol for symbol in system.parameters if symbol.name == "B_z")
    scalar, _dot = electromagnetic_invariants((e_x, 0, 0), (0, 0, b_z))
    return sp.expand(scalar)


def electric_magnetic_invariant_expression(system: FirstOrderSystem) -> sp.Expr:
    e_x = next(symbol for symbol in system.parameters if symbol.name == "E_x")
    b_z = next(symbol for symbol in system.parameters if symbol.name == "B_z")
    _scalar, dot = electromagnetic_invariants((e_x, 0, 0), (0, 0, b_z))
    return dot


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


def p_z_series(states: Sequence[Sequence[float]]) -> list[float]:
    return np.asarray(states, dtype=float)[:, 7].astype(float).tolist()


def em_invariant_series(
    sample_count: int,
    *,
    electric_field_x: float,
    magnetic_field_z: float,
) -> dict[str, list[float]]:
    scalar = float(2.0 * (magnetic_field_z**2 - electric_field_x**2))
    dot = 0.0
    return {
        "faraday_scalar": [scalar] * sample_count,
        "electric_magnetic": [dot] * sample_count,
    }


def measured_drift_velocity(
    states: Sequence[Sequence[float]],
) -> tuple[float, float, float]:
    """Measure spatial displacement per coordinate-time displacement."""

    state_array = np.asarray(states, dtype=float)
    elapsed = float(state_array[-1, 0] - state_array[0, 0])
    if elapsed == 0.0:
        raise ValueError("coordinate-time displacement must be nonzero")
    displacement = state_array[-1, 1:4] - state_array[0, 1:4]
    return tuple((displacement / elapsed).astype(float).tolist())


def spacetime_renderer_hints(states: Sequence[Sequence[float]]) -> dict[str, object]:
    state_array = np.asarray(states, dtype=float)
    x1 = state_array[:, 1]
    x2 = state_array[:, 2]
    x3 = state_array[:, 3]
    extent = float(max(np.max(np.abs(x1)), np.max(np.abs(x2)), 1.0))
    z_min = float(min(np.min(x3), -1.0))
    z_max = float(max(np.max(x3), 1.0))
    return {
        "diagram": "covariant-em-crossed-eb-drift",
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
                "direction": [1.0, 0.0, 0.0],
                "source": "trajectory.metadata.fields.electric",
            },
            {
                "kind": "uniformMagneticField",
                "direction": [0.0, 0.0, 1.0],
                "source": "trajectory.metadata.fields.magnetic",
            },
            {
                "kind": "driftVelocity",
                "source": "trajectory.metadata.drift",
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


system = build_system()
