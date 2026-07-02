from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from engine.export.manifest import build_manifest, write_manifest
from scripts.example_specs import CROSSED_EB_DRIFT, LENSES, SPECS
from scripts.generate_crossed_eb_drift import (
    generate_crossed_eb_drift,
    write_crossed_eb_drift_trajectory,
)
from systems.crossed_eb_drift import (
    analytic_drift_velocity,
    build_system,
    drift_velocity_y_expression,
    electric_magnetic_invariant_expression,
    faraday_scalar_expression,
    mass_shell_expression,
)


def test_crossed_field_rollout_tracks_exb_drift_and_invariants() -> None:
    trajectory = generate_crossed_eb_drift(dt=0.005)

    expected_drift = np.asarray(trajectory.metadata["drift"]["expectedVelocity"])
    measured_drift = np.asarray(trajectory.metadata["drift"]["measuredVelocity"])
    np.testing.assert_allclose(measured_drift, expected_drift, atol=1e-12)

    mass_shell = np.asarray(trajectory.series["mass_shell"], dtype=float)
    four_velocity_norm = np.asarray(trajectory.series["four_velocity_norm"], dtype=float)
    p_z = np.asarray(trajectory.series["p_z"], dtype=float)
    faraday_scalar = np.asarray(trajectory.series["faraday_scalar"], dtype=float)
    electric_magnetic = np.asarray(trajectory.series["electric_magnetic"], dtype=float)

    assert float(np.max(np.abs(mass_shell))) < 1e-10
    np.testing.assert_allclose(four_velocity_norm, -1.0, atol=1e-10)
    assert float(np.max(np.abs(p_z - p_z[0]))) < 1e-12
    np.testing.assert_allclose(faraday_scalar, 2.0 * (1.0**2 - 0.25**2), atol=0.0)
    np.testing.assert_allclose(electric_magnetic, 0.0, atol=0.0)
    assert trajectory.metadata["rendererHints"]["referenceGeometry"][2]["kind"] == (
        "driftVelocity"
    )


def test_symbolic_crossed_field_invariants_and_drift_formula() -> None:
    system = build_system()
    p0, p1, p2, p3 = system.state[4:]
    e_x = next(symbol for symbol in system.parameters if symbol.name == "E_x")
    b_z = next(symbol for symbol in system.parameters if symbol.name == "B_z")
    m = next(symbol for symbol in system.parameters if symbol.name == "m")

    assert mass_shell_expression(system) == -p0**2 + p1**2 + p2**2 + p3**2 + m**2
    assert drift_velocity_y_expression(system) == -e_x / b_z
    assert faraday_scalar_expression(system) == 2 * (b_z**2 - e_x**2)
    assert electric_magnetic_invariant_expression(system) == 0
    assert analytic_drift_velocity(electric_field_x=0.25, magnetic_field_z=1.0) == (
        0.0,
        -0.25,
        0.0,
    )


def test_manifest_registers_crossed_eb_drift() -> None:
    entry = next(
        item
        for item in build_manifest(SPECS, LENSES)["systems"]
        if item["id"] == CROSSED_EB_DRIFT.id
    )

    assert entry["systemKind"] == "covariant-em"
    assert entry["dataPath"] == "/data/crossed_eb_drift.json"
    assert entry["projections"]["spacetime"] == ["x0", "x1", "x2", "x3"]
    assert entry["projections"]["driftPlane"] == ["x1", "x2"]
    assert entry["lenses"] == ["crossedEbDrift"]


def test_export_is_deterministic_and_round_trips(tmp_path: Path) -> None:
    output = tmp_path / "crossed_eb_drift.json"
    viewer_output = tmp_path / "viewer" / "crossed_eb_drift.json"

    trajectory = write_crossed_eb_drift_trajectory(
        output,
        viewer_output=viewer_output,
    )
    payload = json.loads(output.read_text(encoding="utf-8"))
    viewer_payload = json.loads(viewer_output.read_text(encoding="utf-8"))

    assert payload == viewer_payload
    assert payload["metadata"]["kind"] == "covariant-em"
    assert payload["metadata"]["drift"]["expression"] == "E x B / B^2"
    assert payload["metadata"]["fields"]["electric"]["components"] == [0.25, 0.0, 0.0]
    assert payload["metadata"]["fields"]["magnetic"]["components"] == [0.0, 0.0, 1.0]
    residuals = {
        residual["name"]: residual
        for residual in payload["metadata"]["invariantResiduals"]
    }
    for name in (
        "mass_shell",
        "four_velocity_norm",
        "p_z",
        "faraday_scalar",
        "electric_magnetic",
    ):
        assert residuals[name]["rigor"] == "measured"
    assert residuals["mass_shell"]["maxAbs"] < 1e-10
    assert residuals["p_z"]["maxAbs"] < 1e-12
    np.testing.assert_allclose(
        payload["metadata"]["drift"]["measuredVelocity"],
        payload["metadata"]["drift"]["expectedVelocity"],
        atol=1e-12,
    )
    assert trajectory.metadata["worldline"]["massShellSeries"] == "mass_shell"

    second_output = tmp_path / "crossed_eb_drift_second.json"
    write_crossed_eb_drift_trajectory(second_output)
    assert json.loads(second_output.read_text(encoding="utf-8")) == payload

    manifest_output = tmp_path / "manifest.json"
    manifest = write_manifest(SPECS, manifest_output, lenses=LENSES)
    assert json.loads(manifest_output.read_text(encoding="utf-8")) == manifest
