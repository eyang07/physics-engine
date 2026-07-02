from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import sympy as sp

from engine.export.manifest import build_manifest, system_entry, write_manifest
from scripts.example_specs import LENSES, SCALAR_FIELD_DENSITY, SPECS
from scripts.generate_scalar_field_density import (
    generate_scalar_field_density,
    write_scalar_field_density,
)
from systems.scalar_field_density import build_system


def test_scalar_field_density_symbolic_mode_is_on_shell() -> None:
    system = build_system()
    field_density = system.density
    t, x = system.coordinates
    phi = system.field
    m = system.mass

    expected = sp.diff(phi, t, 2) - sp.diff(phi, x, 2) + m**2 * phi
    assert sp.simplify(field_density.euler_lagrange_expression() - expected) == 0
    assert sp.simplify(system.on_shell_residual_expression()) == 0
    assert field_density.stress_energy_tensor() == field_density.stress_energy_tensor().T


def test_scalar_field_density_manifest_declares_symbolic_contract() -> None:
    entry = system_entry(SCALAR_FIELD_DENSITY)

    assert entry["systemKind"] == "field-density"
    assert entry["dataPath"] == "/data/scalar_field_density.json"
    assert entry["lenses"] == ["scalarFieldDensity"]
    assert [field["name"] for field in entry["fields"]] == [
        "fieldConfiguration",
        "stressEnergyConservation",
    ]
    assert entry["fieldModel"]["kind"] == "scalar-field-density"
    assert entry["fieldModel"]["metricSignature"] == "(-,+)"
    assert entry["fieldModel"]["densityLatex"]
    assert entry["fieldModel"]["eulerLagrangeLatex"]
    assert entry["fieldModel"]["stressEnergyLatex"]
    assert "PDE" in entry["fieldModel"]["nonGoal"]

    manifest_entry = next(
        item
        for item in build_manifest(SPECS, LENSES)["systems"]
        if item["id"] == SCALAR_FIELD_DENSITY.id
    )
    assert manifest_entry == entry


def test_generated_scalar_field_density_exports_surface_and_measured_residual() -> None:
    trajectory = generate_scalar_field_density()

    assert trajectory.metadata is not None
    assert trajectory.metadata["kind"] == "field-density"
    assert trajectory.states.shape == (81, 73)
    assert trajectory.state_names == tuple(f"phi_{index}" for index in range(73))

    field = trajectory.metadata["fields"]["fieldConfiguration"]
    assert field["kind"] == "scalar-field-series"
    assert field["shape"] == [81, 73]
    assert np.asarray(field["values"]).shape == (81, 73)
    assert field["evaluation"] == "analytic-on-shell-mode"

    residual = trajectory.metadata["diagnostics"]["stressEnergyConservation"]
    assert residual["kind"] == "field-diagnostic-grid"
    assert residual["operator"] == "stress-energy-divergence"
    assert residual["rigor"] == "measured"
    assert residual["evaluation"] == "measured-finite-difference-grid"
    assert residual["shape"] == [81, 73, 2]
    assert residual["residualMaxAbs"] < 3e-3
    assert "proof" in residual["note"]


def test_scalar_field_density_export_is_deterministic_and_round_trips(tmp_path: Path) -> None:
    output = tmp_path / "scalar_field_density.json"
    viewer_output = tmp_path / "viewer" / "scalar_field_density.json"

    trajectory = write_scalar_field_density(output, viewer_output=viewer_output)
    payload = json.loads(output.read_text(encoding="utf-8"))
    viewer_payload = json.loads(viewer_output.read_text(encoding="utf-8"))

    assert payload == viewer_payload
    assert payload["metadata"]["kind"] == "field-density"
    assert payload["metadata"]["diagnostics"]["stressEnergyConservation"]["rigor"] == "measured"
    assert trajectory.metadata["fieldDensity"]["evaluation"] == "symbolic-structure-plus-sampled-mode"

    second_output = tmp_path / "scalar_field_density_second.json"
    write_scalar_field_density(second_output)
    assert json.loads(second_output.read_text(encoding="utf-8")) == payload

    manifest_output = tmp_path / "manifest.json"
    manifest = write_manifest(SPECS, manifest_output, lenses=LENSES)
    assert json.loads(manifest_output.read_text(encoding="utf-8")) == manifest
    assert any(item.get("systemKind") == "field-density" for item in manifest["systems"])
