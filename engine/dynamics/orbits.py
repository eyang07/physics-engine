"""Effective-potential orbit classification helpers.

These helpers compute deterministic analytic/numeric orbit metadata from
backend-owned dynamics. They are not sampled rollout diagnostics and do not
claim proof; they provide the effective-potential channels and turning-point
roots the viewer can render without re-deriving orbital physics.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Sequence

import numpy as np

SchwarzschildOrbitKind = Literal["timelike", "null"]


def _positive_real_roots(coefficients: Sequence[float], *, minimum: float = 0.0) -> tuple[float, ...]:
    roots = np.roots(np.asarray(coefficients, dtype=float))
    real_roots = sorted(
        float(root.real)
        for root in roots
        if abs(float(root.imag)) < 1e-9 and float(root.real) > minimum
    )
    unique: list[float] = []
    for root in real_roots:
        if not unique or abs(root - unique[-1]) > 1e-8 * max(1.0, abs(root)):
            unique.append(root)
    return tuple(unique)


@dataclass(frozen=True)
class OrbitClassification:
    """Effective-potential turning-point summary."""

    family: str
    classification: str
    energy: float
    angular_momentum: float
    turning_points: tuple[float, ...]
    coordinate: str = "r"
    evaluation: str = "analytic-effective-potential"

    def __post_init__(self) -> None:
        if not self.family:
            raise ValueError("family must be non-empty")
        if not self.classification:
            raise ValueError("classification must be non-empty")
        if not np.isfinite(self.energy) or not np.isfinite(self.angular_momentum):
            raise ValueError("energy and angular momentum must be finite")
        if any(not np.isfinite(point) or point <= 0.0 for point in self.turning_points):
            raise ValueError("turning points must be positive finite radii")
        object.__setattr__(
            self,
            "turning_points",
            tuple(float(point) for point in self.turning_points),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "family": self.family,
            "classification": self.classification,
            "coordinate": self.coordinate,
            "energy": self.energy,
            "angularMomentum": self.angular_momentum,
            "turningPoints": list(self.turning_points),
            "evaluation": self.evaluation,
        }


def kepler_effective_potential_values(
    radius_values: Sequence[float],
    *,
    mass: float,
    gravitational_parameter: float,
    angular_momentum: float,
) -> np.ndarray:
    radii = np.asarray(radius_values, dtype=float)
    if np.any(radii <= 0.0):
        raise ValueError("Kepler effective-potential radii must be positive")
    return angular_momentum**2 / (2.0 * mass * radii**2) - gravitational_parameter * mass / radii


def kepler_turning_points(
    *,
    mass: float,
    gravitational_parameter: float,
    energy: float,
    angular_momentum: float,
) -> tuple[float, ...]:
    if mass <= 0.0 or gravitational_parameter <= 0.0:
        raise ValueError("mass and gravitational_parameter must be positive")
    if abs(angular_momentum) < 1e-12:
        return ()
    if abs(energy) < 1e-12:
        return (angular_momentum**2 / (2.0 * gravitational_parameter * mass**2),)
    return _positive_real_roots(
        [
            energy,
            gravitational_parameter * mass,
            -(angular_momentum**2) / (2.0 * mass),
        ]
    )


def classify_kepler_orbit(
    *,
    mass: float,
    gravitational_parameter: float,
    energy: float,
    angular_momentum: float,
) -> OrbitClassification:
    if abs(angular_momentum) < 1e-12:
        classification = "radial-collision"
    elif energy < -1e-12:
        classification = "bound"
    elif energy > 1e-12:
        classification = "unbound"
    else:
        classification = "critical-parabolic"
    return OrbitClassification(
        family="kepler",
        classification=classification,
        energy=float(energy),
        angular_momentum=float(angular_momentum),
        turning_points=kepler_turning_points(
            mass=mass,
            gravitational_parameter=gravitational_parameter,
            energy=energy,
            angular_momentum=angular_momentum,
        ),
    )


def schwarzschild_effective_potential_values(
    radius_values: Sequence[float],
    *,
    schwarzschild_radius: float,
    angular_momentum: float,
    kind: SchwarzschildOrbitKind = "timelike",
) -> np.ndarray:
    radii = np.asarray(radius_values, dtype=float)
    if schwarzschild_radius <= 0.0:
        raise ValueError("schwarzschild_radius must be positive")
    if np.any(radii <= schwarzschild_radius):
        raise ValueError("Schwarzschild radii must lie outside the horizon")
    epsilon = 1.0 if kind == "timelike" else 0.0
    return (1.0 - schwarzschild_radius / radii) * (
        epsilon + angular_momentum**2 / radii**2
    )


def schwarzschild_turning_points(
    *,
    schwarzschild_radius: float,
    energy: float,
    angular_momentum: float,
    kind: SchwarzschildOrbitKind = "timelike",
) -> tuple[float, ...]:
    if schwarzschild_radius <= 0.0:
        raise ValueError("schwarzschild_radius must be positive")
    epsilon = 1.0 if kind == "timelike" else 0.0
    energy_squared = energy**2
    coefficients = [
        epsilon - energy_squared,
        -epsilon * schwarzschild_radius,
        angular_momentum**2,
        -schwarzschild_radius * angular_momentum**2,
    ]
    return _positive_real_roots(coefficients, minimum=schwarzschild_radius)


def classify_schwarzschild_orbit(
    *,
    schwarzschild_radius: float,
    energy: float,
    angular_momentum: float,
    kind: SchwarzschildOrbitKind = "timelike",
) -> OrbitClassification:
    turning_points = schwarzschild_turning_points(
        schwarzschild_radius=schwarzschild_radius,
        energy=energy,
        angular_momentum=angular_momentum,
        kind=kind,
    )
    if kind == "timelike" and energy < 1.0 and len(turning_points) >= 2:
        classification = "bound"
    elif turning_points:
        classification = "unbound"
    else:
        classification = "plunging"
    return OrbitClassification(
        family=f"schwarzschild-{kind}",
        classification=classification,
        energy=float(energy),
        angular_momentum=float(angular_momentum),
        turning_points=turning_points,
        evaluation="analytic-gr-effective-potential",
    )


__all__ = [
    "OrbitClassification",
    "SchwarzschildOrbitKind",
    "classify_kepler_orbit",
    "classify_schwarzschild_orbit",
    "kepler_effective_potential_values",
    "kepler_turning_points",
    "schwarzschild_effective_potential_values",
    "schwarzschild_turning_points",
]
