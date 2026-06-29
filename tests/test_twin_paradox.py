from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from engine.export.manifest import build_manifest
from scripts.example_specs import LENSES, SPECS, TWIN_PARADOX
from scripts.generate_twin_paradox import (
    generate_twin_paradox,
    write_twin_paradox_trajectory,
)
from systems.twin_paradox import closed_form_proper_times, twin_worldline_samples


def test_traveling_twin_accumulates_less_proper_time_than_inertial_twin() -> None:
    trajectory = generate_twin_paradox(coordinate_duration=8.0, travel_speed=0.6)
    comparison = trajectory.metadata["properTimeComparison"]
    closed_form = closed_form_proper_times(
        coordinate_duration=8.0,
        travel_speed=0.6,
    )

    assert comparison["inertial"] > comparison["traveler"]
    np.testing.assert_allclose(comparison["inertial"], closed_form["inertial"], atol=1e-12)
    np.testing.assert_allclose(comparison["traveler"], closed_form["traveler"], atol=1e-12)
    np.testing.assert_allclose(comparison["difference"], closed_form["difference"], atol=1e-12)


def test_worldlines_share_endpoints_and_turnaround() -> None:
    samples = twin_worldline_samples(coordinate_duration=8.0, travel_speed=0.6)
    inertial = np.asarray(samples["inertial"]["points"], dtype=float)
    traveler = np.asarray(samples["traveler"]["points"], dtype=float)

    np.testing.assert_allclose(inertial[0], traveler[0])
    np.testing.assert_allclose(inertial[-1], traveler[-1])
    np.testing.assert_allclose(inertial[0], [0.0, 0.0])
    np.testing.assert_allclose(inertial[-1], [8.0, 0.0])
    assert samples["turnaround"] == {"coordinateTime": 4.0, "position": 2.4}


def test_export_carries_measured_proper_time_readouts_and_round_trips(tmp_path: Path) -> None:
    output = tmp_path / "twin_paradox.json"
    viewer_output = tmp_path / "viewer" / "twin_paradox.json"

    trajectory = write_twin_paradox_trajectory(output, viewer_output=viewer_output)
    payload = json.loads(output.read_text(encoding="utf-8"))
    viewer_payload = json.loads(viewer_output.read_text(encoding="utf-8"))

    assert payload == viewer_payload
    assert payload["metadata"]["kind"] == "relativistic-worldline"
    assert len(payload["metadata"]["worldlines"]) == 2
    assert payload["metadata"]["properTimeComparison"]["rigor"] == "measured"
    assert payload["metadata"]["properTimeComparison"]["inertial"] > payload["metadata"]["properTimeComparison"]["traveler"]
    assert "inertial_proper_time" in payload["series"]
    assert "traveler_proper_time" in payload["series"]
    assert trajectory.metadata["rendererHints"]["diagram"] == "minkowski-1-plus-1-dual-worldline"


def test_manifest_registers_twin_paradox_export() -> None:
    entry = next(
        item
        for item in build_manifest(SPECS, LENSES)["systems"]
        if item["id"] == TWIN_PARADOX.id
    )

    assert entry["systemKind"] == "relativistic-worldline"
    assert entry["dataPath"] == "/data/twin_paradox.json"
    assert entry["projections"]["spacetime"] == ["x0", "x1"]
    assert entry["lenses"] == ["twinParadoxWorldlines"]
