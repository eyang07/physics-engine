"""Exported series should carry the invariants, and they should be flat.

A conserved quantity that visibly does not move is measured evidence for the
structure the symbolic backend derives, not a proof. These tests confirm the
exporter samples those quantities, labels the residuals as measured, and keeps
them constant along the integrated motion to the tolerance of fixed-step RK4.
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from scripts import example_specs
from scripts.generate_bead_on_hoop import generate_bead_on_hoop_trajectory
from scripts.generate_charged_particle import generate_charged_particle_trajectory
from scripts.generate_double_pendulum import generate_double_pendulum_trajectory
from scripts.generate_free_rigid_body import generate_free_rigid_body_trajectory
from scripts.generate_henon_heiles import generate_henon_heiles_trajectory
from scripts.generate_ideal_spring import generate_ideal_spring_trajectory
from scripts.generate_kepler_problem import generate_kepler_trajectory
from scripts.generate_n_body_gravity import generate_n_body_trajectory
from scripts.generate_pendulum import generate_pendulum_trajectory
from scripts.generate_sphere_geodesic import generate_sphere_geodesic_trajectory
from scripts.generate_symmetric_top import generate_symmetric_top_trajectory
from scripts.generate_uniform_gravity import generate_uniform_gravity_trajectory

CASES = {
    "pendulum": (example_specs.PENDULUM, generate_pendulum_trajectory),
    "sphere-geodesic": (example_specs.SPHERE_GEODESIC, generate_sphere_geodesic_trajectory),
    "charged-particle": (example_specs.CHARGED_PARTICLE, generate_charged_particle_trajectory),
    "uniform-gravity": (example_specs.UNIFORM_GRAVITY, generate_uniform_gravity_trajectory),
    "ideal-spring": (example_specs.IDEAL_SPRING, generate_ideal_spring_trajectory),
    "kepler": (example_specs.KEPLER, generate_kepler_trajectory),
    "bead-on-hoop": (example_specs.BEAD_ON_HOOP, generate_bead_on_hoop_trajectory),
    "double-pendulum": (
        example_specs.DOUBLE_PENDULUM,
        generate_double_pendulum_trajectory,
    ),
    "n-body-gravity": (example_specs.N_BODY_GRAVITY, generate_n_body_trajectory),
    "free-rigid-body": (
        example_specs.FREE_RIGID_BODY,
        generate_free_rigid_body_trajectory,
    ),
    "symmetric-top": (
        example_specs.SYMMETRIC_TOP,
        generate_symmetric_top_trajectory,
    ),
    "henon-heiles": (example_specs.HENON_HEILES, generate_henon_heiles_trajectory),
}


@pytest.mark.parametrize("spec, generate", list(CASES.values()), ids=list(CASES))
def test_series_present_and_conserved(spec, generate) -> None:
    trajectory = generate()

    assert trajectory.series is not None
    expected = {
        quantity.name
        for quantity in spec.conserved
        if quantity.expression_for(spec.build()) is not None
    }
    assert set(trajectory.series) >= expected

    for name in expected:
        values = trajectory.series[name]
        sampled = np.asarray(values, dtype=float)
        assert sampled.shape == trajectory.time.shape

        scale = float(np.abs(sampled).mean()) + 1.0
        drift = float(sampled.max() - sampled.min())
        assert drift <= 1e-2 * scale, f"{spec.id}:{name} drifted by {drift} (scale {scale})"

    assert trajectory.metadata is not None
    residuals = trajectory.metadata["invariantResiduals"]
    assert isinstance(residuals, list)
    assert len(residuals) == len(expected)
    for record in residuals:
        assert set(record) == {
            "name",
            "series",
            "reference",
            "referenceKind",
            "rigor",
            "maxAbs",
            "rms",
            "maxRelative",
            "scale",
        }
        assert record["name"] in expected
        assert record["series"] in trajectory.series
        assert record["referenceKind"] == "initial"
        assert record["rigor"] == "measured"
        assert isinstance(record["reference"], float)
        assert isinstance(record["maxAbs"], float)
        assert isinstance(record["rms"], float)
        assert isinstance(record["scale"], float)
        assert math.isfinite(record["reference"])
        assert math.isfinite(record["maxAbs"])
        assert math.isfinite(record["rms"])
        assert math.isfinite(record["scale"])
        assert record["maxAbs"] >= 0.0
        assert record["rms"] >= 0.0
        assert record["rms"] <= record["maxAbs"] + 1e-15
        if record["maxRelative"] is not None:
            assert math.isfinite(record["maxRelative"])
            assert record["maxRelative"] >= 0.0
            if record["series"] == "H":
                assert record["maxRelative"] < 1e-1


def test_series_survives_json_roundtrip() -> None:
    trajectory = generate_kepler_trajectory()
    payload = trajectory.to_dict()
    assert "series" in payload
    assert set(payload["series"]) == {"H", "ell"}
    assert all(isinstance(value, float) for value in payload["series"]["ell"])
