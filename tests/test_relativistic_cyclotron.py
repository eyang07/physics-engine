from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import sympy as sp

from engine.export.manifest import build_manifest, write_manifest
from scripts.example_specs import LENSES, RELATIVISTIC_CYCLOTRON, SPECS
from scripts.generate_relativistic_cyclotron import (
    generate_relativistic_cyclotron,
    write_relativistic_cyclotron_trajectory,
)
from systems.relativistic_cyclotron import (
    build_system,
    electric_magnetic_invariant_expression,
    faraday_scalar_expression,
    gyrofrequency_expression,
    initial_state,
    mass_shell_expression,
    p_z_expression,
)


def test_relativistic_cyclotron_rollout_tracks_uniform_b_invariants() -> None:
    trajectory = generate_relativistic_cyclotron(dt=0.005)

    assert trajectory.state_names == (
        "x0",
        "x1",
        "x2",
        "x3",
        "p_x0",
        "p_x1",
        "p_x2",
        "p_x3",
    )
    mass_shell = np.asarray(trajectory.series["mass_shell"], dtype=float)
    four_velocity_norm = np.asarray(trajectory.series["four_velocity_norm"], dtype=float)
    p_z = np.asarray(trajectory.series["p_z"], dtype=float)
    faraday_scalar = np.asarray(trajectory.series["faraday_scalar"], dtype=float)
    electric_magnetic = np.asarray(trajectory.series["electric_magnetic"], dtype=float)

    assert float(np.max(np.abs(mass_shell))) < 1e-10
    np.testing.assert_allclose(four_velocity_norm, -1.0, atol=1e-10)
    assert float(np.max(np.abs(p_z - p_z[0]))) < 1e-12
    np.testing.assert_allclose(faraday_scalar, 2.0 * 0.9**2, atol=0.0)
    np.testing.assert_allclose(electric_magnetic, 0.0, atol=0.0)
    assert trajectory.metadata["kind"] == "covariant-em"
    assert trajectory.metadata["rendererHints"]["referenceGeometry"][0]["kind"] == (
        "uniformMagneticField"
    )


def test_gyrofrequency_matches_qb_over_gamma_m() -> None:
    mass = 1.0
    charge = 1.0
    magnetic_field_z = 0.9
    velocity = (0.0, 0.42, 0.18)
    trajectory = generate_relativistic_cyclotron(
        mass=mass,
        charge=charge,
        magnetic_field_z=magnetic_field_z,
        velocity=velocity,
        dt=0.005,
    )
    gamma = trajectory.metadata["parameters"]["gamma0"]
    expected = charge * magnetic_field_z / (gamma * mass)

    assert trajectory.metadata["gyrofrequency"]["expectedCoordinateTime"] == expected
    p = trajectory.states[:, 5:7]
    coordinate_time = trajectory.states[:, 0]
    angles = np.unwrap(np.arctan2(p[:, 1], p[:, 0]))
    measured = np.polyfit(coordinate_time, angles, 1)[0]
    assert abs(measured + expected) < 1e-5

    system = build_system()
    p0 = system.state[4]
    q = next(symbol for symbol in system.parameters if symbol.name == "q")
    b_z = next(symbol for symbol in system.parameters if symbol.name == "B_z")
    assert gyrofrequency_expression(system) == q * b_z / p0


def test_symbolic_cyclotron_invariants_match_uniform_field_forms() -> None:
    system = build_system()
    p0, p1, p2, p3 = system.state[4:]
    b_z = next(symbol for symbol in system.parameters if symbol.name == "B_z")
    m = next(symbol for symbol in system.parameters if symbol.name == "m")

    assert mass_shell_expression(system) == -p0**2 + p1**2 + p2**2 + p3**2 + m**2
    assert p_z_expression(system) == p3
    assert faraday_scalar_expression(system) == 2 * b_z**2
    assert electric_magnetic_invariant_expression(system) == 0


def test_initial_state_rejects_superluminal_velocity() -> None:
    try:
        initial_state(velocity=(1.0, 0.0, 0.0))
    except ValueError as exc:
        assert "subluminal" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("expected subluminal validation")


def test_manifest_registers_covariant_em_cyclotron() -> None:
    entry = next(
        item
        for item in build_manifest(SPECS, LENSES)["systems"]
        if item["id"] == RELATIVISTIC_CYCLOTRON.id
    )

    assert entry["systemKind"] == "covariant-em"
    assert entry["dataPath"] == "/data/relativistic_cyclotron.json"
    assert entry["projections"]["spacetime"] == ["x0", "x1", "x2", "x3"]
    assert entry["projections"]["momentumPlane"] == ["p_x1", "p_x2"]
    assert [quantity["name"] for quantity in entry["conserved"]] == [
        "mass_shell",
        "four_velocity_norm",
        "p_z",
        "faraday_scalar",
        "electric_magnetic",
    ]
    assert entry["lenses"] == ["relativisticCyclotron"]


def test_export_is_deterministic_and_round_trips(tmp_path: Path) -> None:
    output = tmp_path / "relativistic_cyclotron.json"
    viewer_output = tmp_path / "viewer" / "relativistic_cyclotron.json"

    trajectory = write_relativistic_cyclotron_trajectory(
        output,
        viewer_output=viewer_output,
    )
    payload = json.loads(output.read_text(encoding="utf-8"))
    viewer_payload = json.loads(viewer_output.read_text(encoding="utf-8"))

    assert payload == viewer_payload
    assert payload["metadata"]["kind"] == "covariant-em"
    assert payload["metadata"]["worldline"]["massShellSeries"] == "mass_shell"
    assert payload["metadata"]["fields"]["magnetic"]["components"] == [0.0, 0.0, 0.9]
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
    assert trajectory.metadata["gyrofrequency"]["expression"] == "q B_z / (gamma m)"

    second_output = tmp_path / "relativistic_cyclotron_second.json"
    write_relativistic_cyclotron_trajectory(second_output)
    assert json.loads(second_output.read_text(encoding="utf-8")) == payload

    manifest_output = tmp_path / "manifest.json"
    manifest = write_manifest(SPECS, manifest_output, lenses=LENSES)
    assert json.loads(manifest_output.read_text(encoding="utf-8")) == manifest
