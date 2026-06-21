from __future__ import annotations

import json

import numpy as np
import sympy as sp

from engine.export.manifest import system_entry
from scripts.example_specs import SCHWARZSCHILD
from scripts.generate_schwarzschild import (
    generate_schwarzschild_trajectory,
    write_schwarzschild_trajectory,
)
from systems.schwarzschild import (
    build_system,
    kretschmann_scalar_values,
    null_light_bending,
    null_scattering_initial_state,
    photon_sphere_radius,
    ricci_scalar_values,
    timelike_bound_initial_state,
)


def _metric_norm(state: list[float], *, schwarzschild_radius: float) -> float:
    _t, r, _phi, t_dot, r_dot, phi_dot = state
    factor = 1.0 - schwarzschild_radius / r
    return -factor * t_dot**2 + r_dot**2 / factor + r**2 * phi_dot**2


def test_schwarzschild_system_uses_equatorial_metric_geodesic_flow() -> None:
    system = build_system()
    assert tuple(symbol.name for symbol in system.state) == (
        "t",
        "r",
        "phi",
        "t_dot",
        "r_dot",
        "phi_dot",
    )

    t_state = timelike_bound_initial_state()
    n_state = null_scattering_initial_state()
    assert abs(_metric_norm(t_state, schwarzschild_radius=2.0) + 1.0) < 1e-12
    assert abs(_metric_norm(n_state, schwarzschild_radius=2.0)) < 1e-12


def test_schwarzschild_manifest_exposes_orbit_and_effective_potential() -> None:
    entry = system_entry(SCHWARZSCHILD)
    potentials = entry["effectivePotentials"]

    assert entry["systemKind"] == "schwarzschild-geodesic"
    assert {item["name"] for item in entry["conserved"]} == {"E", "L"}
    assert [potential["name"] for potential in potentials] == ["schwarzschild_radial"]
    assert potentials[0]["turningPointsSource"].endswith(".turningPoints")
    assert potentials[0]["classificationSource"] == "trajectory.metadata.orbitClassification"
    assert [field["name"] for field in entry["fields"]] == [
        "ricciScalar",
        "kretschmannScalar",
    ]


def test_timelike_schwarzschild_exports_precession_and_measured_invariants() -> None:
    trajectory = generate_schwarzschild_trajectory(kind="timelike")
    residuals = {
        record["name"]: record
        for record in trajectory.metadata["invariantResiduals"]
    }
    precession = trajectory.metadata["diagnostics"]["perihelionPrecession"]
    weak = precession["weakFieldPrediction"]
    plot = trajectory.metadata["potentialPlots"][0]

    assert trajectory.metadata["kind"] == "timelike"
    assert {record["rigor"] for record in residuals.values()} == {"measured"}
    assert residuals["E"]["maxRelative"] < 1e-10
    assert residuals["L"]["maxRelative"] < 1e-10
    assert residuals["metricNorm"]["maxAbs"] < 1e-10
    assert precession["rigor"] == "measured"
    assert abs(precession["precessionPerOrbit"] - weak) / weak < 0.15
    assert plot["name"] == "schwarzschild_radial"
    assert plot["rendererHint"] == "effective-potential"
    assert plot["classification"] == "bound"
    assert len(plot["turningPoints"]) >= 2
    curvature = trajectory.metadata["curvatureScalars"]
    ricci = curvature["ricciScalar"]
    kretschmann = curvature["kretschmannScalar"]
    radii = np.asarray(ricci["axes"][0], dtype=float)
    assert ricci["evaluation"] == "symbolic-exact"
    assert kretschmann["evaluation"] == "symbolic-exact"
    assert np.allclose(np.asarray(ricci["values"], dtype=float), 0.0)
    assert np.allclose(
        np.asarray(kretschmann["values"], dtype=float),
        kretschmann_scalar_values(radii, schwarzschild_radius=2.0),
    )


def test_null_schwarzschild_exports_light_bending_and_photon_sphere() -> None:
    trajectory = generate_schwarzschild_trajectory(kind="null")
    residuals = {
        record["name"]: record
        for record in trajectory.metadata["invariantResiduals"]
    }
    bending = trajectory.metadata["diagnostics"]["lightBending"]

    assert trajectory.metadata["kind"] == "null"
    assert residuals["E"]["maxRelative"] < 1e-10
    assert residuals["L"]["maxRelative"] < 1e-10
    assert residuals["metricNorm"]["maxAbs"] < 1e-10
    assert bending["photonSphereRadius"] == photon_sphere_radius(schwarzschild_radius=2.0)
    assert bending["closestApproach"] > bending["photonSphereRadius"]
    assert abs(bending["bendingAngle"] - bending["weakFieldPrediction"]) / bending[
        "weakFieldPrediction"
    ] < 0.12

    direct = null_light_bending(schwarzschild_radius=2.0, impact_parameter=30.0)
    assert abs(direct["bendingAngle"] - bending["bendingAngle"]) < 1e-12


def test_schwarzschild_effective_potential_expression() -> None:
    system = SCHWARZSCHILD.build()
    r = next(symbol for symbol in system.state if symbol.name == "r")
    rs = next(symbol for symbol in system.parameters if symbol.name == "r_s")
    ell = sp.Symbol("L")
    (potential,) = SCHWARZSCHILD.effective_potentials

    expected = (1 - rs / r) * (1 + ell**2 / r**2)
    assert sp.simplify(potential.expression_for(system) - expected) == 0


def test_schwarzschild_curvature_scalars_match_vacuum_closed_forms() -> None:
    radii = np.array([3.0, 5.0, 10.0])

    assert np.allclose(ricci_scalar_values(radii, schwarzschild_radius=2.0), 0.0)
    assert np.allclose(
        kretschmann_scalar_values(radii, schwarzschild_radius=2.0),
        12.0 * 2.0**2 / radii**6,
    )


def test_schwarzschild_script_writes_primary_and_viewer_outputs(tmp_path) -> None:
    output = tmp_path / "data" / "schwarzschild.json"
    viewer_output = tmp_path / "viewer" / "schwarzschild.json"

    write_schwarzschild_trajectory(output, viewer_output=viewer_output)

    assert json.loads(output.read_text(encoding="utf-8")) == json.loads(
        viewer_output.read_text(encoding="utf-8")
    )
