from __future__ import annotations

import json

import numpy as np
import pytest

from engine.dynamics import invariant_residuals
from engine.export.manifest import build_manifest
from scripts.example_specs import LENSES, N_BODY_GRAVITY
from scripts.generate_n_body_gravity import (
    NBodyInitialState,
    figure_eight_initial_state,
    generate_n_body_trajectory,
    sun_two_planets_initial_state,
    write_n_body_trajectory,
    write_n_body_variant_trajectories,
)
from systems.n_body_gravity import NBodyLayout, build_system


def test_n_body_system_builds_first_order_field_for_arbitrary_body_count() -> None:
    system = build_system(body_count=4)

    assert len(system.state_symbols) == 16
    assert len(system.rhs) == 16
    assert [symbol.name for symbol in system.state_symbols[:8]] == [
        "x1",
        "y1",
        "x2",
        "y2",
        "x3",
        "y3",
        "x4",
        "y4",
    ]
    assert [symbol.name for symbol in system.rhs[:8]] == [
        "vx1",
        "vy1",
        "vx2",
        "vy2",
        "vx3",
        "vy3",
        "vx4",
        "vy4",
    ]


def test_n_body_initial_state_is_centered_in_com_frame() -> None:
    initial = sun_two_planets_initial_state().centered()
    masses = np.asarray(initial.masses, dtype=float)

    position_com = (masses[:, None] * initial.positions).sum(axis=0) / masses.sum()
    velocity_com = (masses[:, None] * initial.velocities).sum(axis=0) / masses.sum()

    assert np.linalg.norm(position_com) < 1e-15
    assert np.linalg.norm(velocity_com) < 1e-15


def test_n_body_figure_eight_invariants_are_measured_and_stay_small() -> None:
    trajectory = generate_n_body_trajectory(t_span=(0.0, 3.0), dt=0.0025)

    assert trajectory.state_names == NBodyLayout(3).state_names
    assert trajectory.series is not None
    assert set(trajectory.series) == {"H", "P_x", "P_y", "L_z"}

    residuals = invariant_residuals(trajectory.series)
    assert residuals["H"].max_relative is not None
    assert residuals["H"].max_relative < 1e-7
    assert residuals["P_x"].max_abs < 1e-12
    assert residuals["P_y"].max_abs < 1e-12
    assert residuals["L_z"].max_abs < 5e-12

    records = {
        record["name"]: record
        for record in (trajectory.metadata or {})["invariantResiduals"]
    }
    assert set(records) == {"H", "P_x", "P_y", "L_z"}
    assert {record["rigor"] for record in records.values()} == {"measured"}


def test_n_body_manifest_exposes_per_body_projections_and_conserved_quantities() -> None:
    manifest = build_manifest((N_BODY_GRAVITY,), LENSES)
    entry = manifest["systems"][0]

    assert entry["id"] == "n-body-gravity"
    assert entry["systemKind"] == "first-order-flow"
    assert entry["projections"]["body1Orbit"] == ["x1", "y1"]
    assert entry["projections"]["body2Orbit"] == ["x2", "y2"]
    assert entry["projections"]["body3Orbit"] == ["x3", "y3"]
    assert [quantity["name"] for quantity in entry["conserved"]] == [
        "H",
        "P_x",
        "P_y",
        "L_z",
    ]
    assert all(quantity["expression_latex"] for quantity in entry["conserved"])


def test_generate_n_body_script_writes_outputs_and_variants(tmp_path) -> None:
    output = tmp_path / "data" / "n_body_gravity.json"
    viewer_output = tmp_path / "viewer" / "public" / "data" / "n_body_gravity.json"
    initial = figure_eight_initial_state()

    trajectory = write_n_body_trajectory(
        output,
        viewer_output=viewer_output,
        initial=initial,
        t_end=0.05,
        dt=0.01,
    )

    assert output.exists()
    assert viewer_output.exists()
    assert json.loads(output.read_text(encoding="utf-8")) == json.loads(
        viewer_output.read_text(encoding="utf-8")
    )
    assert len(trajectory.time) == 6

    variant_output_dir = tmp_path / "variants"
    viewer_variant_output_dir = tmp_path / "viewer-variants"
    variants = write_n_body_variant_trajectories(
        variant_output_dir,
        viewer_output_dir=viewer_variant_output_dir,
    )
    assert len(variants) == 1
    assert sorted(path.name for path in variant_output_dir.glob("*.json")) == [
        "n_body_gravity_sun_two_planets.json",
    ]
    assert sorted(path.name for path in viewer_variant_output_dir.glob("*.json")) == [
        "n_body_gravity_sun_two_planets.json",
    ]


def test_n_body_initial_state_validates_shapes() -> None:
    with pytest.raises(ValueError, match="velocities must match"):
        NBodyInitialState(
            masses=(1.0, 1.0),
            positions=np.zeros((2, 2)),
            velocities=np.zeros((3, 2)),
        )
