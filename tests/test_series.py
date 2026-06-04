"""Exported series should carry the invariants — and they should be flat.

A conserved quantity that visibly does not move is how the viewer proves a
conservation law without a single decimal. These tests confirm the exporter
actually samples those quantities and that they stay constant along the
integrated motion (to the tolerance of fixed-step RK4).
"""

from __future__ import annotations

import numpy as np
import pytest

from scripts import example_specs
from scripts.generate_charged_particle import generate_charged_particle_trajectory
from scripts.generate_ideal_spring import generate_ideal_spring_trajectory
from scripts.generate_kepler_problem import generate_kepler_trajectory
from scripts.generate_pendulum import generate_pendulum_trajectory
from scripts.generate_sphere_geodesic import generate_sphere_geodesic_trajectory
from scripts.generate_uniform_gravity import generate_uniform_gravity_trajectory

CASES = {
    "pendulum": (example_specs.PENDULUM, generate_pendulum_trajectory),
    "sphere-geodesic": (example_specs.SPHERE_GEODESIC, generate_sphere_geodesic_trajectory),
    "charged-particle": (example_specs.CHARGED_PARTICLE, generate_charged_particle_trajectory),
    "uniform-gravity": (example_specs.UNIFORM_GRAVITY, generate_uniform_gravity_trajectory),
    "ideal-spring": (example_specs.IDEAL_SPRING, generate_ideal_spring_trajectory),
    "kepler": (example_specs.KEPLER, generate_kepler_trajectory),
}


@pytest.mark.parametrize("spec, generate", list(CASES.values()), ids=list(CASES))
def test_series_present_and_conserved(spec, generate) -> None:
    trajectory = generate()

    assert trajectory.series is not None
    expected = {quantity.name for quantity in spec.conserved if quantity.expression is not None}
    assert set(trajectory.series) == expected

    for name, values in trajectory.series.items():
        sampled = np.asarray(values, dtype=float)
        assert sampled.shape == trajectory.time.shape

        scale = float(np.abs(sampled).mean()) + 1.0
        drift = float(sampled.max() - sampled.min())
        assert drift <= 1e-2 * scale, f"{spec.id}:{name} drifted by {drift} (scale {scale})"


def test_series_survives_json_roundtrip() -> None:
    trajectory = generate_kepler_trajectory()
    payload = trajectory.to_dict()
    assert "series" in payload
    assert set(payload["series"]) == {"H", "ell"}
    assert all(isinstance(value, float) for value in payload["series"]["ell"])
