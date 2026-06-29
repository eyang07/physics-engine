from __future__ import annotations

from typing import Sequence

import numpy as np
import sympy as sp

from engine.dynamics import FirstOrderSystem
from engine.relativity import ProperTimeWorldline


def build_system(dimension: int = 2) -> FirstOrderSystem:
    """Free proper-time worldline primitive used by the twin comparison export."""

    return ProperTimeWorldline(dimension=dimension, light_speed=sp.Integer(1)).first_order_system()


def lorentz_factor(speed: float) -> float:
    """Return ``gamma`` for a dimensionless speed ``|v| < 1``."""

    speed_value = float(speed)
    if not 0.0 <= abs(speed_value) < 1.0:
        raise ValueError("speed must satisfy |v| < 1 in c = 1 units")
    return float(1.0 / np.sqrt(1.0 - speed_value**2))


def closed_form_proper_times(
    *,
    coordinate_duration: float = 8.0,
    travel_speed: float = 0.6,
) -> dict[str, float]:
    """Closed-form proper-time totals for the idealized twin-paradox path."""

    if coordinate_duration <= 0.0:
        raise ValueError("coordinate_duration must be positive")
    gamma = lorentz_factor(travel_speed)
    inertial = float(coordinate_duration)
    traveler = float(coordinate_duration / gamma)
    return {
        "inertial": inertial,
        "traveler": traveler,
        "difference": inertial - traveler,
        "gamma": gamma,
    }


def twin_worldline_samples(
    *,
    coordinate_duration: float = 8.0,
    travel_speed: float = 0.6,
    sample_count: int = 401,
) -> dict[str, object]:
    """Sample two endpoint-sharing worldlines in 1+1 Minkowski spacetime.

    Both worldlines begin at ``(x0, x1) = (0, 0)`` and end at
    ``(coordinate_duration, 0)``. The traveling twin moves at ``+v`` for half the
    coordinate time, turns instantaneously, then moves at ``-v`` back to the
    origin. This is the standard piecewise-inertial idealization; the turn event
    is metadata, not a resolved acceleration model.
    """

    if sample_count < 3:
        raise ValueError("sample_count must be at least 3")
    if coordinate_duration <= 0.0:
        raise ValueError("coordinate_duration must be positive")
    gamma = lorentz_factor(travel_speed)
    coordinate_time = np.linspace(0.0, coordinate_duration, sample_count)
    half_duration = 0.5 * coordinate_duration

    inertial_points = np.column_stack(
        [coordinate_time, np.zeros_like(coordinate_time)]
    )
    traveler_x = np.where(
        coordinate_time <= half_duration,
        travel_speed * coordinate_time,
        travel_speed * (coordinate_duration - coordinate_time),
    )
    traveler_points = np.column_stack([coordinate_time, traveler_x])
    traveler_proper_time = coordinate_time / gamma
    inertial_proper_time = coordinate_time.copy()

    outbound = coordinate_time <= half_duration
    traveler_four_velocity = np.column_stack(
        [
            np.full_like(coordinate_time, gamma),
            np.where(outbound, gamma * travel_speed, -gamma * travel_speed),
        ]
    )
    # Assign the exact endpoint velocity to the inbound leg; the kink itself is
    # already marked by `turnaround`.
    traveler_four_velocity[0] = [gamma, gamma * travel_speed]
    inertial_four_velocity = np.column_stack(
        [np.ones_like(coordinate_time), np.zeros_like(coordinate_time)]
    )
    totals = closed_form_proper_times(
        coordinate_duration=coordinate_duration,
        travel_speed=travel_speed,
    )

    return {
        "coordinateTime": coordinate_time.astype(float),
        "inertial": {
            "points": inertial_points.astype(float),
            "properTime": inertial_proper_time.astype(float),
            "fourVelocity": inertial_four_velocity.astype(float),
            "properTimeTotal": totals["inertial"],
        },
        "traveler": {
            "points": traveler_points.astype(float),
            "properTime": traveler_proper_time.astype(float),
            "fourVelocity": traveler_four_velocity.astype(float),
            "properTimeTotal": totals["traveler"],
        },
        "turnaround": {
            "coordinateTime": half_duration,
            "position": travel_speed * half_duration,
        },
        "totals": totals,
    }


def twin_renderer_hints(samples: dict[str, object]) -> dict[str, object]:
    """Renderer-owned framing hints for the dual-worldline spacetime diagram."""

    coordinate_time = np.asarray(samples["coordinateTime"], dtype=float)
    traveler = samples["traveler"]
    traveler_points = np.asarray(traveler["points"], dtype=float)
    extent = float(max(np.max(np.abs(traveler_points[:, 1])), 1.0))
    return {
        "diagram": "minkowski-1-plus-1-dual-worldline",
        "bounds": {
            "time": [0.0, float(coordinate_time[-1])],
            "x": [-extent, extent],
            "y": [0.0, 0.0],
        },
        "axes": {
            "time": "x0",
            "space": ["x1"],
        },
        "referenceGeometry": [
            {
                "kind": "lightCone",
                "apex": [0.0, 0.0],
                "speed": 1.0,
            },
            {
                "kind": "sharedEndpoint",
                "points": [
                    [0.0, 0.0],
                    [float(coordinate_time[-1]), 0.0],
                ],
            },
        ],
    }


def worldline_records(samples: dict[str, object]) -> list[dict[str, object]]:
    """Return backend-owned worldline records for trajectory metadata."""

    coordinate_time = np.asarray(samples["coordinateTime"], dtype=float)
    records = []
    for key, label in (("inertial", "Inertial twin"), ("traveler", "Traveling twin")):
        entry = samples[key]
        records.append(
            {
                "id": key,
                "label": label,
                "kind": "proper-time-worldline",
                "signature": "(-,+)",
                "units": "c=1",
                "coordinateTime": coordinate_time.astype(float).tolist(),
                "properTime": np.asarray(entry["properTime"], dtype=float).tolist(),
                "properTimeTotal": float(entry["properTimeTotal"]),
                "points": np.asarray(entry["points"], dtype=float).tolist(),
                "fourVelocity": np.asarray(entry["fourVelocity"], dtype=float).tolist(),
                "evaluation": "measured-sampled-worldline",
                "rigor": "measured",
            }
        )
    return records


def state_series(samples: dict[str, object]) -> np.ndarray:
    """Primary trajectory state matching the manifest: inertial ``(x, u)``."""

    inertial = np.asarray(samples["inertial"]["points"], dtype=float)
    four_velocity = np.asarray(samples["inertial"]["fourVelocity"], dtype=float)
    return np.column_stack([inertial, four_velocity])


system = build_system()
