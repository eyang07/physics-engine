from __future__ import annotations

from typing import Sequence

import numpy as np
import sympy as sp

from engine.dynamics import FirstOrderSystem
from engine.relativity import MinkowskiMetric, ProperTimeWorldline


def build_system(dimension: int = 3) -> FirstOrderSystem:
    """Free proper-time worldline in flat Minkowski spacetime.

    The state is ``(x^mu, u^mu)`` with ``x^0 = c t`` and geometrized ``c = 1``.
    The independent variable is proper time ``tau``. With zero four-acceleration
    the solution is the straight worldline ``x^mu(tau) = x^mu(0) + u^mu tau``.
    """

    return ProperTimeWorldline(dimension=dimension, light_speed=sp.Integer(1)).first_order_system()


def initial_state_from_velocity(
    velocity: Sequence[float] = (0.55, 0.18),
    *,
    dimension: int = 3,
) -> list[float]:
    """Return ``(x^mu, u^mu)`` at the origin for a spatial coordinate velocity."""

    spatial = tuple(float(component) for component in velocity)
    if len(spatial) != dimension - 1:
        raise ValueError(f"velocity must have {dimension - 1} spatial components")
    speed_squared = float(np.dot(spatial, spatial))
    if speed_squared >= 1.0:
        raise ValueError("coordinate velocity must be subluminal in c = 1 units")
    gamma = 1.0 / np.sqrt(1.0 - speed_squared)
    four_velocity = [gamma, *(gamma * component for component in spatial)]
    return [0.0] * dimension + four_velocity


def invariant_interval_rate_series(states: Sequence[Sequence[float]]) -> list[float]:
    """Sample ``eta_mu_nu u^mu u^nu`` along the rollout.

    This is the invariant interval per unit proper time. For a proper-time
    parameterized timelike free particle it is identically ``-1`` in c = 1
    units; exporting it as a measured series keeps the viewer from recomputing
    the physics.
    """

    state_array = np.asarray(states, dtype=float)
    if state_array.ndim != 2 or state_array.shape[1] % 2 != 0:
        raise ValueError("states must be a 2D array with coordinate and velocity halves")
    dimension = state_array.shape[1] // 2
    velocities = state_array[:, dimension:]
    return (
        -velocities[:, 0] ** 2
        + np.sum(velocities[:, 1:] ** 2, axis=1)
    ).astype(float).tolist()


def coordinate_time_series(states: Sequence[Sequence[float]]) -> list[float]:
    """Recover coordinate time ``t = x^0 / c`` with geometrized ``c = 1``."""

    return np.asarray(states, dtype=float)[:, 0].astype(float).tolist()


def spacetime_renderer_hints(states: Sequence[Sequence[float]]) -> dict[str, object]:
    """Renderer-owned framing hints for a 2+1 spacetime diagram."""

    state_array = np.asarray(states, dtype=float)
    x0 = state_array[:, 0]
    x1 = state_array[:, 1]
    x2 = state_array[:, 2]
    spatial_extent = float(max(np.max(np.abs(x1)), np.max(np.abs(x2)), 1.0))
    time_extent = float(max(np.max(x0), 1.0))
    return {
        "diagram": "minkowski-2-plus-1",
        "bounds": {
            "time": [0.0, time_extent],
            "x": [-spatial_extent, spatial_extent],
            "y": [-spatial_extent, spatial_extent],
        },
        "axes": {
            "time": "x0",
            "space": ["x1", "x2"],
            "parameter": "tau",
        },
        "referenceGeometry": [
            {
                "kind": "lightCone",
                "apex": [0.0, 0.0, 0.0],
                "speed": 1.0,
            }
        ],
    }


def worldline_payload(time: Sequence[float], states: Sequence[Sequence[float]]) -> dict[str, object]:
    """Backend-owned worldline channel consumed by the viewer."""

    state_array = np.asarray(states, dtype=float)
    return {
        "kind": "proper-time-worldline",
        "signature": "(-,+,+)",
        "units": "c=1",
        "parameter": "tau",
        "coordinateTime": "x0",
        "spatialCoordinates": ["x1", "x2"],
        "properTime": np.asarray(time, dtype=float).astype(float).tolist(),
        "points": state_array[:, :3].astype(float).tolist(),
        "fourVelocity": state_array[:, 3:].astype(float).tolist(),
        "intervalRateSeries": "proper_interval_rate",
        "evaluation": "measured-rollout",
    }


def interval_rate_expression(system: FirstOrderSystem) -> sp.Expr:
    """Symbolic ``eta_mu_nu u^mu u^nu`` for the manifest conserved channel."""

    dimension = len(system.state) // 2
    velocities = system.state[dimension:]
    metric = MinkowskiMetric(dimension=dimension)
    return sp.simplify(metric.norm_squared(velocities))


system = build_system()
