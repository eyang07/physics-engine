from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from engine.export.manifest import build_manifest, write_manifest
from scripts.example_specs import LENSES, RELATIVISTIC_FREE_PARTICLE, SPECS
from scripts.generate_relativistic_free_particle import (
    generate_relativistic_free_particle,
    write_relativistic_free_particle_trajectory,
)
from systems.relativistic_free_particle import (
    build_system,
    initial_state_from_velocity,
    interval_rate_expression,
)


def test_free_particle_worldline_is_straight_and_timelike() -> None:
    trajectory = generate_relativistic_free_particle()
    states = trajectory.states
    tau = trajectory.time
    initial = np.asarray(initial_state_from_velocity(), dtype=float)
    four_velocity = initial[3:]

    np.testing.assert_allclose(
        states[:, 3:],
        np.broadcast_to(four_velocity, states[:, 3:].shape),
        atol=1e-10,
    )
    np.testing.assert_allclose(states[:, :3], np.outer(tau, four_velocity), atol=1e-10)

    interval_rate = np.asarray(trajectory.series["proper_interval_rate"], dtype=float)
    np.testing.assert_allclose(interval_rate, -1.0, atol=1e-10)


def test_manifest_registers_relativistic_worldline_kind() -> None:
    entry = next(
        item
        for item in build_manifest(SPECS, LENSES)["systems"]
        if item["id"] == RELATIVISTIC_FREE_PARTICLE.id
    )

    assert entry["systemKind"] == "relativistic-worldline"
    assert entry["dataPath"] == "/data/relativistic_free_particle.json"
    assert entry["projections"]["spacetime"] == ["x0", "x1", "x2"]
    assert entry["conserved"][0]["name"] == "proper_interval_rate"
    assert entry["lenses"] == ["relativisticWorldline"]


def test_interval_rate_is_symbolic_minkowski_norm() -> None:
    system = build_system()
    x0_dot, x1_dot, x2_dot = system.state[3:]
    assert interval_rate_expression(system) == -(x0_dot**2) + x1_dot**2 + x2_dot**2


def test_export_carries_measured_interval_residual_and_round_trips(tmp_path: Path) -> None:
    output = tmp_path / "relativistic_free_particle.json"
    viewer_output = tmp_path / "viewer" / "relativistic_free_particle.json"

    trajectory = write_relativistic_free_particle_trajectory(
        output,
        viewer_output=viewer_output,
    )
    payload = json.loads(output.read_text(encoding="utf-8"))
    viewer_payload = json.loads(viewer_output.read_text(encoding="utf-8"))

    assert payload == viewer_payload
    assert payload["metadata"]["kind"] == "relativistic-worldline"
    residual = payload["metadata"]["invariantResiduals"][0]
    assert residual["name"] == "proper_interval_rate"
    assert residual["rigor"] == "measured"
    assert residual["maxAbs"] < 1e-10
    assert payload["metadata"]["worldline"]["intervalRateSeries"] == "proper_interval_rate"
    assert trajectory.metadata["rendererHints"]["referenceGeometry"][0]["kind"] == "lightCone"

    manifest_output = tmp_path / "manifest.json"
    manifest = write_manifest(SPECS, manifest_output, lenses=LENSES)
    assert json.loads(manifest_output.read_text(encoding="utf-8")) == manifest
