from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import sympy as sp

from engine.export.manifest import build_manifest, write_manifest
from scripts.example_specs import LENSES, RELATIVISTIC_PARTICLE_IN_POTENTIAL, SPECS
from scripts.generate_relativistic_particle_in_potential import (
    generate_relativistic_particle_in_potential,
    write_relativistic_particle_in_potential_trajectory,
)
from systems.relativistic_particle_in_potential import (
    build_system,
    coordinate_velocity_expression,
    initial_state,
    mass_shell_expression,
    newtonian_limit_rhs,
    proper_interval_rate_expression,
    total_energy_expression,
)


def test_static_potential_rollout_tracks_energy_and_mass_shell() -> None:
    trajectory = generate_relativistic_particle_in_potential(dt=0.005)

    energy = np.asarray(trajectory.series["total_energy"], dtype=float)
    mass_shell = np.asarray(trajectory.series["mass_shell"], dtype=float)
    interval_rate = np.asarray(trajectory.series["proper_interval_rate"], dtype=float)

    assert float(np.max(np.abs(energy - energy[0]))) < 1e-10
    assert float(np.max(np.abs(mass_shell - mass_shell[0]))) < 1e-10
    assert abs(float(mass_shell[0])) < 1e-12
    np.testing.assert_allclose(interval_rate, -1.0, atol=1e-10)
    assert initial_state() == [
        0.0,
        0.9,
        float(np.sqrt(1.0 + 0.32**2)),
        0.32,
    ]


def test_symbolic_energy_mass_shell_and_nonrelativistic_limit() -> None:
    system = build_system()
    x0, x1, p0, p1 = system.state
    c, k, m = system.parameters

    assert total_energy_expression(system) == c * p0 + k * x1**2 / 2
    assert mass_shell_expression(system) == -p0**2 + p1**2 + c**2 * m**2
    assert proper_interval_rate_expression(system) == (-p0**2 + p1**2) / m**2
    assert newtonian_limit_rhs(system) == (p1 / m, -k * x1)

    velocity = coordinate_velocity_expression(system)
    nonrel_velocity = sp.series(velocity, c, sp.oo, 2).removeO()
    assert sp.simplify(nonrel_velocity - p1 / m) == 0
    assert system.rhs[3] == -k * x1
    assert system.rhs[0] == c
    assert x0.name == "x0"


def test_manifest_registers_relativistic_particle_in_potential() -> None:
    entry = next(
        item
        for item in build_manifest(SPECS, LENSES)["systems"]
        if item["id"] == RELATIVISTIC_PARTICLE_IN_POTENTIAL.id
    )

    assert entry["systemKind"] == "relativistic-worldline"
    assert entry["dataPath"] == "/data/relativistic_particle_in_potential.json"
    assert entry["projections"]["spacetime"] == ["x0", "x1"]
    assert [quantity["name"] for quantity in entry["conserved"]] == [
        "proper_interval_rate",
        "total_energy",
        "mass_shell",
    ]
    assert entry["lenses"] == ["relativisticWorldline"]


def test_export_is_deterministic_and_round_trips(tmp_path: Path) -> None:
    output = tmp_path / "relativistic_particle_in_potential.json"
    viewer_output = tmp_path / "viewer" / "relativistic_particle_in_potential.json"

    trajectory = write_relativistic_particle_in_potential_trajectory(
        output,
        viewer_output=viewer_output,
    )
    payload = json.loads(output.read_text(encoding="utf-8"))
    viewer_payload = json.loads(viewer_output.read_text(encoding="utf-8"))

    assert payload == viewer_payload
    assert payload["metadata"]["kind"] == "relativistic-worldline"
    assert payload["metadata"]["potential"]["kind"] == "static-scalar-potential"
    assert payload["metadata"]["worldline"]["energySeries"] == "total_energy"
    assert payload["metadata"]["worldline"]["massShellSeries"] == "mass_shell"
    assert payload["metadata"]["worldline"]["intervalRateSeries"] == (
        "proper_interval_rate"
    )
    residuals = {
        residual["name"]: residual
        for residual in payload["metadata"]["invariantResiduals"]
    }
    assert residuals["proper_interval_rate"]["rigor"] == "measured"
    assert residuals["total_energy"]["rigor"] == "measured"
    assert residuals["mass_shell"]["rigor"] == "measured"
    assert residuals["proper_interval_rate"]["maxAbs"] < 1e-10
    assert residuals["total_energy"]["maxAbs"] < 1e-10
    assert residuals["mass_shell"]["maxAbs"] < 1e-10
    assert trajectory.metadata["rendererHints"]["referenceGeometry"][1]["kind"] == (
        "staticPotential"
    )

    second_output = tmp_path / "relativistic_particle_in_potential_second.json"
    write_relativistic_particle_in_potential_trajectory(second_output)
    assert json.loads(second_output.read_text(encoding="utf-8")) == payload

    manifest_output = tmp_path / "manifest.json"
    manifest = write_manifest(SPECS, manifest_output, lenses=LENSES)
    assert json.loads(manifest_output.read_text(encoding="utf-8")) == manifest
