from __future__ import annotations

import json

import numpy as np
import sympy as sp

from engine.dynamics import invariant_residuals
from engine.export.manifest import build_manifest
from scripts.example_specs import DOUBLE_PENDULUM, LENSES
from scripts.generate_double_pendulum import (
    generate_double_pendulum_trajectory,
    write_double_pendulum_trajectory,
    write_double_pendulum_variant_trajectories,
)
from systems.double_pendulum import build_system


def test_double_pendulum_lagrangian_pipeline_derives_coupled_equations() -> None:
    m1, m2, ell1, ell2, g = sp.symbols("m1 m2 ell1 ell2 g", positive=True)
    system = build_system(
        mass1=m1,
        mass2=m2,
        length1=ell1,
        length2=ell2,
        gravity=g,
    )
    theta1, theta2 = system.q
    theta1_dot, theta2_dot = system.qdot
    delta = theta1 - theta2

    mass_matrix, forcing = system.mass_matrix_and_forcing()
    expected_mass_matrix = sp.Matrix(
        [
            [(m1 + m2) * ell1**2, m2 * ell1 * ell2 * sp.cos(delta)],
            [m2 * ell1 * ell2 * sp.cos(delta), m2 * ell2**2],
        ]
    )
    expected_forcing = sp.Matrix(
        [
            -m2 * ell1 * ell2 * sp.sin(delta) * theta2_dot**2
            - (m1 + m2) * g * ell1 * sp.sin(theta1),
            m2 * ell1 * ell2 * sp.sin(delta) * theta1_dot**2
            - m2 * g * ell2 * sp.sin(theta2),
        ]
    )

    assert sp.simplify(mass_matrix - expected_mass_matrix) == sp.zeros(2)
    assert sp.simplify(forcing - expected_forcing) == sp.zeros(2, 1)


def test_double_pendulum_energy_diagnostic_is_measured_and_stays_small() -> None:
    trajectory = generate_double_pendulum_trajectory(t_span=(0.0, 6.0), dt=0.0025)

    assert trajectory.state_names == (
        "theta1",
        "theta2",
        "theta1_dot",
        "theta2_dot",
        "x1",
        "y1",
        "x2",
        "y2",
    )
    assert trajectory.series is not None
    energy = np.asarray(trajectory.series["H"], dtype=float)
    residual = invariant_residuals({"H": energy})["H"]
    assert residual.max_abs < 1e-6

    metadata = trajectory.metadata or {}
    records = {record["name"]: record for record in metadata["invariantResiduals"]}
    assert records["H"]["rigor"] == "measured"
    assert records["H"]["maxAbs"] < 1e-6


def test_double_pendulum_manifest_carries_schema_projections_and_energy() -> None:
    manifest = build_manifest((DOUBLE_PENDULUM,), LENSES)
    entry = manifest["systems"][0]

    assert entry["id"] == "double-pendulum"
    assert [state["name"] for state in entry["state"]] == [
        "theta1",
        "theta2",
        "theta1_dot",
        "theta2_dot",
        "x1",
        "y1",
        "x2",
        "y2",
    ]
    assert entry["projections"] == {
        "bobPositions": ["x1", "y1", "x2", "y2"],
        "theta1Phase": ["theta1", "theta1_dot"],
        "theta2Phase": ["theta2", "theta2_dot"],
    }
    assert [quantity["name"] for quantity in entry["conserved"]] == ["H"]
    assert entry["conserved"][0]["symmetry"] == "time translation"
    assert entry["physics"]["lagrangian"]
    assert entry["physics"]["energy"]


def test_generate_double_pendulum_script_writes_outputs_and_variants(tmp_path) -> None:
    output = tmp_path / "data" / "double_pendulum.json"
    viewer_output = tmp_path / "viewer" / "public" / "data" / "double_pendulum.json"

    trajectory = write_double_pendulum_trajectory(
        output,
        viewer_output=viewer_output,
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
    variants = write_double_pendulum_variant_trajectories(
        variant_output_dir,
        viewer_output_dir=viewer_variant_output_dir,
    )
    assert len(variants) == 2
    assert sorted(path.name for path in variant_output_dir.glob("*.json")) == [
        "double_pendulum_near_linear.json",
        "double_pendulum_unequal_links.json",
    ]
    assert sorted(path.name for path in viewer_variant_output_dir.glob("*.json")) == [
        "double_pendulum_near_linear.json",
        "double_pendulum_unequal_links.json",
    ]
