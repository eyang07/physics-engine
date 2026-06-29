from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from engine.export.manifest import build_manifest, write_manifest
from scripts.example_specs import LENSES, SPECS, UNIFORM_PROPER_ACCELERATION
from scripts.generate_uniform_proper_acceleration import (
    generate_uniform_proper_acceleration,
    write_uniform_proper_acceleration_trajectory,
)
from systems.uniform_proper_acceleration import (
    closed_form_worldline,
    initial_state,
    interval_rate_expression,
)
from systems.uniform_proper_acceleration import build_system


def test_hyperbolic_worldline_matches_closed_form() -> None:
    acceleration = 0.35
    trajectory = generate_uniform_proper_acceleration(acceleration=acceleration)
    states = trajectory.states
    closed = closed_form_worldline(trajectory.time, acceleration=acceleration)

    np.testing.assert_allclose(states[:, 0], closed["x0"], atol=2e-10)
    np.testing.assert_allclose(states[:, 1], closed["x1"], atol=2e-10)
    np.testing.assert_allclose(states[:, 2], closed["u0"], atol=2e-10)
    np.testing.assert_allclose(states[:, 3], closed["u1"], atol=2e-10)

    interval_rate = np.asarray(trajectory.series["proper_interval_rate"], dtype=float)
    np.testing.assert_allclose(interval_rate, -1.0, atol=2e-10)
    assert initial_state() == [0.0, 0.0, 1.0, 0.0]


def test_measured_residuals_track_hyperbola_and_rapidity_relations() -> None:
    trajectory = generate_uniform_proper_acceleration()

    for name in (
        "hyperbola_residual",
        "rapidity_residual",
        "x0_closed_form_residual",
        "x1_closed_form_residual",
        "u0_closed_form_residual",
        "u1_closed_form_residual",
    ):
        residual = np.asarray(trajectory.series[name], dtype=float)
        assert float(np.max(np.abs(residual))) < 1e-9

    exported_residuals = {
        residual["name"]: residual for residual in trajectory.metadata["invariantResiduals"]
    }
    assert exported_residuals["rapidity_residual"]["rigor"] == "measured"
    assert exported_residuals["hyperbola_residual"]["maxAbs"] < 1e-9


def test_manifest_registers_uniform_proper_acceleration_export() -> None:
    entry = next(
        item
        for item in build_manifest(SPECS, LENSES)["systems"]
        if item["id"] == UNIFORM_PROPER_ACCELERATION.id
    )

    assert entry["systemKind"] == "relativistic-worldline"
    assert entry["dataPath"] == "/data/uniform_proper_acceleration.json"
    assert entry["projections"]["spacetime"] == ["x0", "x1"]
    assert entry["conserved"][0]["name"] == "proper_interval_rate"
    assert entry["lenses"] == ["relativisticWorldline"]


def test_interval_rate_is_symbolic_minkowski_norm() -> None:
    system = build_system()
    u0, u1 = system.state[2:]
    assert interval_rate_expression(system) == -(u0**2) + u1**2


def test_export_is_deterministic_and_round_trips(tmp_path: Path) -> None:
    output = tmp_path / "uniform_proper_acceleration.json"
    viewer_output = tmp_path / "viewer" / "uniform_proper_acceleration.json"

    trajectory = write_uniform_proper_acceleration_trajectory(
        output,
        viewer_output=viewer_output,
    )
    payload = json.loads(output.read_text(encoding="utf-8"))
    viewer_payload = json.loads(viewer_output.read_text(encoding="utf-8"))

    assert payload == viewer_payload
    assert payload["metadata"]["kind"] == "relativistic-worldline"
    assert payload["metadata"]["worldline"]["properAcceleration"] == 0.35
    assert payload["metadata"]["worldline"]["rapiditySeries"] == "rapidity"
    assert payload["metadata"]["closedForm"]["evaluation"] == "measured-against-rollout"
    assert trajectory.metadata["rendererHints"]["referenceGeometry"][1]["kind"] == "rindlerHyperbola"

    second_output = tmp_path / "uniform_proper_acceleration_second.json"
    write_uniform_proper_acceleration_trajectory(second_output)
    assert json.loads(second_output.read_text(encoding="utf-8")) == payload

    manifest_output = tmp_path / "manifest.json"
    manifest = write_manifest(SPECS, manifest_output, lenses=LENSES)
    assert json.loads(manifest_output.read_text(encoding="utf-8")) == manifest
