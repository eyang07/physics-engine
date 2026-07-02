from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import sympy as sp

from engine.export.manifest import build_manifest, write_manifest
from scripts.example_specs import LENSES, RELATIVISTIC_CHARGED_PARTICLE, SPECS
from scripts.generate_relativistic_charged_particle import (
    generate_relativistic_charged_particle,
    write_relativistic_charged_particle_trajectory,
)
from systems.charged_particle import build_uniform_magnetic_field_system
from systems.relativistic_charged_particle import (
    build_system,
    electric_magnetic_invariant_expression,
    faraday_scalar_expression,
    low_velocity_limit_matches_newtonian_magnetic_field,
    mass_shell_expression,
)


def test_general_charged_particle_export_tracks_measured_invariants() -> None:
    trajectory = generate_relativistic_charged_particle(dt=0.002)

    mass_shell = np.asarray(trajectory.series["mass_shell"], dtype=float)
    four_velocity_norm = np.asarray(trajectory.series["four_velocity_norm"], dtype=float)
    faraday_scalar = np.asarray(trajectory.series["faraday_scalar"], dtype=float)
    electric_magnetic = np.asarray(trajectory.series["electric_magnetic"], dtype=float)

    assert float(np.max(np.abs(mass_shell))) < 1e-10
    np.testing.assert_allclose(four_velocity_norm, -1.0, atol=1e-10)
    np.testing.assert_allclose(
        faraday_scalar,
        2.0 * (0.9**2 - (0.08**2 + (-0.03) ** 2)),
        atol=0.0,
    )
    np.testing.assert_allclose(electric_magnetic, 0.0, atol=0.0)
    assert trajectory.metadata["kind"] == "covariant-em"
    assert trajectory.metadata["worldline"]["massShellSeries"] == "mass_shell"


def test_symbolic_invariants_and_low_velocity_limit_match_newtonian_counterpart() -> None:
    system = build_system()
    p0, p1, p2, p3 = system.state[4:]
    e_x = next(symbol for symbol in system.parameters if symbol.name == "E_x")
    e_y = next(symbol for symbol in system.parameters if symbol.name == "E_y")
    e_z = next(symbol for symbol in system.parameters if symbol.name == "E_z")
    b_x = next(symbol for symbol in system.parameters if symbol.name == "B_x")
    b_y = next(symbol for symbol in system.parameters if symbol.name == "B_y")
    b_z = next(symbol for symbol in system.parameters if symbol.name == "B_z")
    m = next(symbol for symbol in system.parameters if symbol.name == "m")

    assert mass_shell_expression(system) == -p0**2 + p1**2 + p2**2 + p3**2 + m**2
    assert faraday_scalar_expression(system) == 2 * (
        b_x**2 + b_y**2 + b_z**2 - e_x**2 - e_y**2 - e_z**2
    )
    assert electric_magnetic_invariant_expression(system) == e_x * b_x + e_y * b_y + e_z * b_z
    assert low_velocity_limit_matches_newtonian_magnetic_field() == (0, 0, 0)

    newtonian = build_uniform_magnetic_field_system(mass=m, charge=sp.Symbol("q"), magnetic_field_z=b_z)
    x_dot, y_dot, _z_dot = newtonian.qdot
    x_ddot, y_ddot, z_ddot = newtonian.qddot
    assert newtonian.euler_lagrange_expressions() == (
        m * x_ddot - b_z * sp.Symbol("q") * y_dot,
        b_z * sp.Symbol("q") * x_dot + m * y_ddot,
        m * z_ddot,
    )


def test_manifest_registers_relativistic_charged_particle() -> None:
    entry = next(
        item
        for item in build_manifest(SPECS, LENSES)["systems"]
        if item["id"] == RELATIVISTIC_CHARGED_PARTICLE.id
    )

    assert entry["systemKind"] == "covariant-em"
    assert entry["dataPath"] == "/data/relativistic_charged_particle.json"
    assert entry["projections"]["spacetime"] == ["x0", "x1", "x2", "x3"]
    assert entry["projections"]["momentumSpace"] == ["p_x1", "p_x2", "p_x3"]
    assert [quantity["name"] for quantity in entry["conserved"]] == [
        "mass_shell",
        "four_velocity_norm",
        "faraday_scalar",
        "electric_magnetic",
    ]
    assert entry["lenses"] == ["relativisticChargedParticle"]


def test_export_is_deterministic_and_round_trips(tmp_path: Path) -> None:
    output = tmp_path / "relativistic_charged_particle.json"
    viewer_output = tmp_path / "viewer" / "relativistic_charged_particle.json"

    trajectory = write_relativistic_charged_particle_trajectory(
        output,
        viewer_output=viewer_output,
    )
    payload = json.loads(output.read_text(encoding="utf-8"))
    viewer_payload = json.loads(viewer_output.read_text(encoding="utf-8"))

    assert payload == viewer_payload
    assert payload["metadata"]["kind"] == "covariant-em"
    assert payload["metadata"]["fields"]["electric"]["components"] == [0.08, -0.03, 0.0]
    assert payload["metadata"]["fields"]["magnetic"]["components"] == [0.0, 0.0, 0.9]
    residuals = {
        residual["name"]: residual
        for residual in payload["metadata"]["invariantResiduals"]
    }
    for name in (
        "mass_shell",
        "four_velocity_norm",
        "faraday_scalar",
        "electric_magnetic",
    ):
        assert residuals[name]["rigor"] == "measured"
    assert residuals["mass_shell"]["maxAbs"] < 1e-10
    assert trajectory.metadata["rendererHints"]["referenceGeometry"][0]["kind"] == (
        "uniformElectricField"
    )

    second_output = tmp_path / "relativistic_charged_particle_second.json"
    write_relativistic_charged_particle_trajectory(second_output)
    assert json.loads(second_output.read_text(encoding="utf-8")) == payload

    manifest_output = tmp_path / "manifest.json"
    manifest = write_manifest(SPECS, manifest_output, lenses=LENSES)
    assert json.loads(manifest_output.read_text(encoding="utf-8")) == manifest
