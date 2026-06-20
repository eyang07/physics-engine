from __future__ import annotations

import numpy as np

from engine.dynamics import (
    classify_kepler_orbit,
    classify_schwarzschild_orbit,
    kepler_effective_potential_values,
    schwarzschild_effective_potential_values,
)


def test_kepler_turning_points_match_effective_potential_roots() -> None:
    classification = classify_kepler_orbit(
        mass=1.0,
        gravitational_parameter=1.0,
        energy=-0.25,
        angular_momentum=1.0,
    )
    roots = np.asarray(classification.turning_points, dtype=float)
    values = kepler_effective_potential_values(
        roots,
        mass=1.0,
        gravitational_parameter=1.0,
        angular_momentum=1.0,
    )

    assert classification.classification == "bound"
    assert roots.shape == (2,)
    assert np.allclose(values, classification.energy)
    assert classification.to_dict()["evaluation"] == "analytic-effective-potential"


def test_kepler_classification_distinguishes_unbound_and_critical() -> None:
    unbound = classify_kepler_orbit(
        mass=1.0,
        gravitational_parameter=1.0,
        energy=0.25,
        angular_momentum=1.0,
    )
    critical = classify_kepler_orbit(
        mass=1.0,
        gravitational_parameter=1.0,
        energy=0.0,
        angular_momentum=1.0,
    )

    assert unbound.classification == "unbound"
    assert len(unbound.turning_points) == 1
    assert critical.classification == "critical-parabolic"
    assert critical.turning_points == (0.5,)


def test_schwarzschild_turning_points_match_gr_effective_potential_roots() -> None:
    classification = classify_schwarzschild_orbit(
        schwarzschild_radius=2.0,
        energy=0.98,
        angular_momentum=4.0,
    )
    roots = np.asarray(classification.turning_points, dtype=float)
    values = schwarzschild_effective_potential_values(
        roots,
        schwarzschild_radius=2.0,
        angular_momentum=4.0,
    )

    assert classification.family == "schwarzschild-timelike"
    assert classification.classification == "bound"
    assert len(roots) == 3
    assert np.all(roots > 2.0)
    assert np.allclose(values, classification.energy**2)
