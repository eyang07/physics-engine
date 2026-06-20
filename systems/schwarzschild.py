from __future__ import annotations

from typing import Literal, Sequence

import numpy as np
from scipy.integrate import quad
import sympy as sp

from engine.dynamics import (
    FirstOrderSystem,
    schwarzschild_equatorial_metric,
    schwarzschild_turning_points,
)

SchwarzschildGeodesicKind = Literal["timelike", "null"]


def build_system(
    schwarzschild_radius: sp.Expr | float | None = None,
) -> FirstOrderSystem:
    """Equatorial Schwarzschild geodesic flow in geometrized units."""

    return schwarzschild_equatorial_metric(schwarzschild_radius).geodesic_system()


def timelike_bound_constants(
    *,
    semi_latus_rectum: float = 40.0,
    eccentricity: float = 0.1,
    mass_parameter: float = 1.0,
) -> tuple[float, float]:
    """Specific energy and angular momentum for a bound Schwarzschild orbit.

    Uses Darwin's ``p,e`` parameterization with ``r = p M / (1 + e cos chi)``.
    """

    p = semi_latus_rectum
    e = eccentricity
    if p <= 3.0 + e**2:
        raise ValueError("semi_latus_rectum must exceed 3 + eccentricity^2")
    if not 0.0 <= e < 1.0:
        raise ValueError("eccentricity must satisfy 0 <= e < 1")
    energy_squared = ((p - 2.0) ** 2 - 4.0 * e**2) / (p * (p - 3.0 - e**2))
    angular_momentum_squared = mass_parameter**2 * p**2 / (p - 3.0 - e**2)
    return float(np.sqrt(energy_squared)), float(np.sqrt(angular_momentum_squared))


def timelike_bound_initial_state(
    *,
    schwarzschild_radius: float = 2.0,
    semi_latus_rectum: float = 40.0,
    eccentricity: float = 0.1,
) -> list[float]:
    mass_parameter = schwarzschild_radius / 2.0
    energy, angular_momentum = timelike_bound_constants(
        semi_latus_rectum=semi_latus_rectum,
        eccentricity=eccentricity,
        mass_parameter=mass_parameter,
    )
    periapsis = semi_latus_rectum * mass_parameter / (1.0 + eccentricity)
    factor = 1.0 - schwarzschild_radius / periapsis
    return [
        0.0,
        periapsis,
        0.0,
        energy / factor,
        0.0,
        angular_momentum / periapsis**2,
    ]


def null_scattering_initial_state(
    *,
    schwarzschild_radius: float = 2.0,
    impact_parameter: float = 30.0,
    start_radius: float = 300.0,
) -> list[float]:
    if start_radius <= schwarzschild_radius:
        raise ValueError("start_radius must lie outside the horizon")
    factor = 1.0 - schwarzschild_radius / start_radius
    radial_speed_squared = 1.0 - factor * impact_parameter**2 / start_radius**2
    if radial_speed_squared <= 0.0:
        raise ValueError("start_radius is inside the null turning point")
    return [
        0.0,
        start_radius,
        -0.1,
        1.0 / factor,
        -float(np.sqrt(radial_speed_squared)),
        impact_parameter / start_radius**2,
    ]


def embedding_xy(states: Sequence[Sequence[float]]) -> np.ndarray:
    state_array = np.asarray(states, dtype=float)
    r = state_array[:, 1]
    phi = state_array[:, 2]
    return np.column_stack([r * np.cos(phi), r * np.sin(phi)])


def conserved_series(
    states: Sequence[Sequence[float]],
    *,
    schwarzschild_radius: float,
) -> dict[str, list[float]]:
    state_array = np.asarray(states, dtype=float)
    r = state_array[:, 1]
    t_dot = state_array[:, 3]
    r_dot = state_array[:, 4]
    phi_dot = state_array[:, 5]
    factor = 1.0 - schwarzschild_radius / r
    energy = factor * t_dot
    angular_momentum = r**2 * phi_dot
    norm = -factor * t_dot**2 + r_dot**2 / factor + r**2 * phi_dot**2
    return {
        "E": energy.astype(float).tolist(),
        "L": angular_momentum.astype(float).tolist(),
        "metricNorm": norm.astype(float).tolist(),
    }


def periapsis_precession(
    states: Sequence[Sequence[float]],
) -> dict[str, float]:
    state_array = np.asarray(states, dtype=float)
    r = state_array[:, 1]
    phi = state_array[:, 2]
    minima = [
        index
        for index in range(1, len(r) - 1)
        if r[index] < r[index - 1] and r[index] <= r[index + 1]
    ]
    if len(minima) < 2:
        raise ValueError("at least two periapses are required to measure precession")
    delta_phi = float(phi[minima[1]] - phi[minima[0]])
    return {
        "deltaPhi": delta_phi,
        "precessionPerOrbit": delta_phi - 2.0 * np.pi,
        "firstPeriapsisIndex": int(minima[0]),
        "secondPeriapsisIndex": int(minima[1]),
        "evaluation": "measured-rollout-periapsis-spacing",
        "rigor": "measured",
    }


def weak_field_precession(*, semi_latus_rectum: float) -> float:
    """Weak-field periapsis advance for p measured in units of M."""

    return float(6.0 * np.pi / semi_latus_rectum)


def photon_sphere_radius(*, schwarzschild_radius: float) -> float:
    return 1.5 * float(schwarzschild_radius)


def weak_field_light_bending(
    *,
    schwarzschild_radius: float,
    impact_parameter: float,
) -> float:
    return float(2.0 * schwarzschild_radius / impact_parameter)


def null_light_bending(
    *,
    schwarzschild_radius: float,
    impact_parameter: float,
) -> dict[str, float]:
    roots = schwarzschild_turning_points(
        schwarzschild_radius=schwarzschild_radius,
        energy=1.0,
        angular_momentum=impact_parameter,
        kind="null",
    )
    closest_approach = max(roots)
    u_max = 1.0 / closest_approach

    def integrand(u: float) -> float:
        return impact_parameter / np.sqrt(
            1.0 - impact_parameter**2 * u**2 * (1.0 - schwarzschild_radius * u)
        )

    half_angle, _error = quad(integrand, 0.0, u_max, points=[u_max], limit=200)
    bending = 2.0 * half_angle - np.pi
    return {
        "impactParameter": float(impact_parameter),
        "closestApproach": float(closest_approach),
        "bendingAngle": float(bending),
        "weakFieldPrediction": weak_field_light_bending(
            schwarzschild_radius=schwarzschild_radius,
            impact_parameter=impact_parameter,
        ),
        "photonSphereRadius": photon_sphere_radius(
            schwarzschild_radius=schwarzschild_radius
        ),
        "evaluation": "null-effective-potential-quadrature",
    }


system = build_system()


__all__ = [
    "SchwarzschildGeodesicKind",
    "build_system",
    "conserved_series",
    "embedding_xy",
    "null_light_bending",
    "null_scattering_initial_state",
    "periapsis_precession",
    "photon_sphere_radius",
    "timelike_bound_constants",
    "timelike_bound_initial_state",
    "weak_field_light_bending",
    "weak_field_precession",
]
