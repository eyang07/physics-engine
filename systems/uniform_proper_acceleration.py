from __future__ import annotations

from typing import Sequence

import numpy as np
import sympy as sp

from engine.dynamics import FirstOrderSystem
from engine.relativity import MinkowskiMetric, ProperTimeWorldline


def build_system() -> FirstOrderSystem:
    """Uniform proper acceleration in 1+1 flat spacetime.

    The state is ``(x0, x1, u0, u1)`` with ``x0 = ct`` and ``c = 1``. Starting
    from rest at the origin, the autonomous boost dynamics
    ``du0/dtau = a u1``, ``du1/dtau = a u0`` produces the standard hyperbolic
    worldline.
    """

    worldline = ProperTimeWorldline(dimension=2, light_speed=sp.Integer(1))
    acceleration = sp.Symbol("a", real=True)
    u0, u1 = worldline.four_velocity_symbols
    return worldline.first_order_system((acceleration * u1, acceleration * u0))


def initial_state() -> list[float]:
    """Start at the origin with unit future-directed four-velocity."""

    return [0.0, 0.0, 1.0, 0.0]


def closed_form_worldline(
    proper_time: Sequence[float],
    *,
    acceleration: float,
) -> dict[str, list[float]]:
    """Closed-form hyperbolic motion for constant proper acceleration."""

    if acceleration <= 0.0:
        raise ValueError("acceleration must be positive")
    tau = np.asarray(proper_time, dtype=float)
    rapidity = acceleration * tau
    return {
        "x0": (np.sinh(rapidity) / acceleration).astype(float).tolist(),
        "x1": ((np.cosh(rapidity) - 1.0) / acceleration).astype(float).tolist(),
        "u0": np.cosh(rapidity).astype(float).tolist(),
        "u1": np.sinh(rapidity).astype(float).tolist(),
        "rapidity": rapidity.astype(float).tolist(),
    }


def invariant_interval_rate_series(states: Sequence[Sequence[float]]) -> list[float]:
    """Sample ``eta_mu_nu u^mu u^nu`` along the rollout."""

    state_array = np.asarray(states, dtype=float)
    if state_array.ndim != 2 or state_array.shape[1] != 4:
        raise ValueError("states must have shape (sample_count, 4)")
    velocities = state_array[:, 2:]
    return (-velocities[:, 0] ** 2 + velocities[:, 1] ** 2).astype(float).tolist()


def hyperbola_residual_series(
    states: Sequence[Sequence[float]],
    *,
    acceleration: float,
) -> list[float]:
    """Sample ``(x1 + 1/a)^2 - x0^2 - 1/a^2`` for the Rindler hyperbola."""

    if acceleration <= 0.0:
        raise ValueError("acceleration must be positive")
    state_array = np.asarray(states, dtype=float)
    x0 = state_array[:, 0]
    x1 = state_array[:, 1]
    inverse_a = 1.0 / float(acceleration)
    residual = (x1 + inverse_a) ** 2 - x0**2 - inverse_a**2
    return residual.astype(float).tolist()


def rapidity_residual_series(
    proper_time: Sequence[float],
    states: Sequence[Sequence[float]],
    *,
    acceleration: float,
) -> list[float]:
    """Sample ``atanh(u1/u0) - a tau`` for the analytic rapidity relation."""

    if acceleration <= 0.0:
        raise ValueError("acceleration must be positive")
    tau = np.asarray(proper_time, dtype=float)
    state_array = np.asarray(states, dtype=float)
    rapidity = np.arctanh(state_array[:, 3] / state_array[:, 2])
    return (rapidity - acceleration * tau).astype(float).tolist()


def closed_form_residual_series(
    proper_time: Sequence[float],
    states: Sequence[Sequence[float]],
    *,
    acceleration: float,
) -> dict[str, list[float]]:
    """Sample rollout residuals against the closed-form hyperbolic solution."""

    state_array = np.asarray(states, dtype=float)
    closed = closed_form_worldline(proper_time, acceleration=acceleration)
    return {
        "x0_closed_form_residual": (
            state_array[:, 0] - np.asarray(closed["x0"], dtype=float)
        ).astype(float).tolist(),
        "x1_closed_form_residual": (
            state_array[:, 1] - np.asarray(closed["x1"], dtype=float)
        ).astype(float).tolist(),
        "u0_closed_form_residual": (
            state_array[:, 2] - np.asarray(closed["u0"], dtype=float)
        ).astype(float).tolist(),
        "u1_closed_form_residual": (
            state_array[:, 3] - np.asarray(closed["u1"], dtype=float)
        ).astype(float).tolist(),
    }


def coordinate_time_series(states: Sequence[Sequence[float]]) -> list[float]:
    """Recover coordinate time ``t = x0`` in ``c = 1`` units."""

    return np.asarray(states, dtype=float)[:, 0].astype(float).tolist()


def spacetime_renderer_hints(
    states: Sequence[Sequence[float]],
    *,
    acceleration: float,
) -> dict[str, object]:
    """Renderer-owned framing hints for a 1+1 spacetime diagram."""

    if acceleration <= 0.0:
        raise ValueError("acceleration must be positive")
    state_array = np.asarray(states, dtype=float)
    x0 = state_array[:, 0]
    x1 = state_array[:, 1]
    time_extent = float(max(np.max(x0), 1.0))
    spatial_max = float(max(np.max(x1), 1.0 / acceleration))
    return {
        "diagram": "minkowski-1-plus-1-hyperbola",
        "bounds": {
            "time": [0.0, time_extent],
            "x": [0.0, spatial_max],
        },
        "axes": {
            "time": "x0",
            "space": ["x1"],
            "parameter": "tau",
        },
        "referenceGeometry": [
            {
                "kind": "lightCone",
                "apex": [0.0, 0.0],
                "speed": 1.0,
            },
            {
                "kind": "rindlerHyperbola",
                "acceleration": float(acceleration),
                "equation": "(x1 + 1/a)^2 - x0^2 = 1/a^2",
            },
        ],
    }


def worldline_payload(
    time: Sequence[float],
    states: Sequence[Sequence[float]],
    *,
    acceleration: float,
) -> dict[str, object]:
    """Backend-owned worldline channel consumed by the viewer."""

    state_array = np.asarray(states, dtype=float)
    return {
        "kind": "proper-time-worldline",
        "signature": "(-,+)",
        "units": "c=1",
        "parameter": "tau",
        "coordinateTime": "x0",
        "spatialCoordinates": ["x1"],
        "properTime": np.asarray(time, dtype=float).astype(float).tolist(),
        "points": state_array[:, :2].astype(float).tolist(),
        "fourVelocity": state_array[:, 2:].astype(float).tolist(),
        "properAcceleration": float(acceleration),
        "intervalRateSeries": "proper_interval_rate",
        "rapiditySeries": "rapidity",
        "evaluation": "measured-rollout",
    }


def interval_rate_expression(system: FirstOrderSystem) -> sp.Expr:
    """Symbolic ``eta_mu_nu u^mu u^nu`` for the manifest conserved channel."""

    dimension = len(system.state) // 2
    velocities = system.state[dimension:]
    metric = MinkowskiMetric(dimension=dimension)
    return sp.simplify(metric.norm_squared(velocities))


system = build_system()
