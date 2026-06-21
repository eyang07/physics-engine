from __future__ import annotations

import json

import numpy as np
import pytest
import sympy as sp

from engine.export.manifest import system_entry
from scripts.example_specs import WORMHOLE
from scripts.generate_wormhole import generate_wormhole_trajectory, write_wormhole_trajectory
from systems.wormhole import (
    build_system,
    classify_radial_geodesic,
    domain_assumptions,
    ellis_wormhole_metric,
    radial_effective_potential_values,
    radial_throat_barrier,
    radial_throat_initial_state,
    radial_turning_points,
)


def _metric_norm(state: list[float], *, throat_radius: float) -> float:
    _t, ell, _phi, t_dot, ell_dot, phi_dot = state
    return -t_dot**2 + ell_dot**2 + (ell**2 + throat_radius**2) * phi_dot**2


def test_wormhole_system_uses_ellis_metric_geodesic_flow() -> None:
    system = build_system()
    assert tuple(symbol.name for symbol in system.state) == (
        "t",
        "l",
        "phi",
        "t_dot",
        "l_dot",
        "phi_dot",
    )

    geometry = ellis_wormhole_metric()
    _t, ell, _phi = geometry.coordinates
    (throat_radius,) = geometry.parameters
    gamma = geometry.christoffel_symbols()

    assert sp.simplify(gamma[1, 2, 2] + ell) == 0
    assert sp.simplify(gamma[2, 1, 2] - ell / (ell**2 + throat_radius**2)) == 0
    assert sp.simplify(gamma[2, 2, 1] - ell / (ell**2 + throat_radius**2)) == 0

    initial_state = radial_throat_initial_state()
    assert abs(_metric_norm(initial_state, throat_radius=1.0) + 1.0) < 1e-12


def test_wormhole_domain_rejects_nonpositive_throat() -> None:
    for invalid in (0.0, -1.0):
        with pytest.raises(ValueError, match="throat_radius must be positive"):
            domain_assumptions(throat_radius=invalid)


def test_wormhole_generator_rejects_invalid_throat() -> None:
    with pytest.raises(ValueError, match="throat_radius must be positive"):
        generate_wormhole_trajectory(throat_radius=0.0, t_span=(0.0, 0.2), dt=0.02)


def test_wormhole_exports_domain_assumptions() -> None:
    trajectory = generate_wormhole_trajectory(t_span=(0.0, 0.2), dt=0.02)
    domain = trajectory.metadata["domain"]

    assert domain["kind"] == "coordinate-domain"
    assert domain["background"] == "fixed-ellis-wormhole"
    assert domain["coordinates"] == ["t", "l", "phi"]
    assert domain["throatRadius"] == 1.0
    assert domain["radialCoordinateRange"] == "all-real"
    (constraint,) = domain["constraints"]
    assert constraint["quantity"] == "a"
    assert constraint["relation"] == "greater-than"
    assert constraint["value"] == 0.0


def test_wormhole_manifest_exposes_embedding_contract() -> None:
    entry = system_entry(WORMHOLE)
    geometry = entry["geometry"]

    assert entry["systemKind"] == "wormhole-geodesic"
    assert entry["domain"] == {
        "kind": "coordinate-domain",
        "source": "trajectory.metadata.domain",
    }
    assert {item["name"] for item in entry["conserved"]} == {"E", "L"}
    assert geometry["kind"] == "wormhole-geodesic"
    assert geometry["rendererHint"] == "wormhole-geodesic"
    assert geometry["embeddingMesh"]["source"] == (
        "trajectory.metadata.wormholeGeometry.embeddingMesh"
    )
    assert geometry["geodesic"]["source"] == "trajectory.metadata.wormholeGeometry.geodesic"
    assert geometry["diagnostics"]["throatTraversal"] == (
        "trajectory.metadata.diagnostics.throatTraversal"
    )
    assert geometry["diagnostics"]["geodesicDeviation"] == (
        "trajectory.metadata.diagnostics.geodesicDeviation"
    )


def test_wormhole_exports_throat_traversal_and_measured_invariants() -> None:
    trajectory = generate_wormhole_trajectory(t_span=(0.0, 32.0), dt=0.02)
    residuals = {
        record["name"]: record
        for record in trajectory.metadata["invariantResiduals"]
    }
    traversal = trajectory.metadata["diagnostics"]["throatTraversal"]
    deviation = trajectory.metadata["diagnostics"]["geodesicDeviation"]
    ell = trajectory.states[:, 1]

    assert trajectory.metadata["kind"] == "fixed-background"
    assert np.min(ell) < 0.0
    assert np.max(ell) > 0.0
    assert traversal["crossesThroat"] is True
    assert traversal["rigor"] == "measured"
    assert abs(traversal["crossingTime"] - 15.0) < 0.04
    assert {record["rigor"] for record in residuals.values()} == {"measured"}
    assert residuals["E"]["maxRelative"] < 1e-12
    assert residuals["L"]["maxAbs"] < 1e-12
    assert residuals["metricNorm"]["maxAbs"] < 1e-12
    assert deviation["kind"] == "geodesic-deviation"
    assert deviation["rigor"] == "measured"
    assert deviation["neighborInitialOffset"] == {"phi": 0.03}
    assert deviation["minRelativeSeparation"] < 0.2
    assert abs(deviation["minParameter"] - traversal["crossingTime"]) < 0.04


def test_wormhole_embedding_matches_surface_of_revolution() -> None:
    trajectory = generate_wormhole_trajectory(t_span=(0.0, 0.2), dt=0.02)
    positions = trajectory.states[:, 6:9]
    ell = trajectory.states[:, 1]
    x = positions[:, 0]
    y = positions[:, 1]
    z = positions[:, 2]
    geometry = trajectory.metadata["wormholeGeometry"]
    mesh = geometry["embeddingMesh"]

    assert np.allclose(x**2 + y**2, ell**2 + 1.0)
    assert np.allclose(z, np.arcsinh(ell))
    assert mesh["kind"] == "surface-mesh"
    assert mesh["rendererHint"] == "wormhole-geodesic"
    assert np.asarray(mesh["points"], dtype=float).shape == (73, 65, 3)
    assert np.asarray(mesh["triangles"], dtype=int).shape[1] == 3
    assert np.allclose(np.asarray(geometry["geodesic"]["points"], dtype=float), positions)


def test_wormhole_script_writes_primary_and_viewer_outputs(tmp_path) -> None:
    output = tmp_path / "data" / "wormhole.json"
    viewer_output = tmp_path / "viewer" / "wormhole.json"

    write_wormhole_trajectory(output, viewer_output=viewer_output)

    assert json.loads(output.read_text(encoding="utf-8")) == json.loads(
        viewer_output.read_text(encoding="utf-8")
    )


def test_wormhole_exports_scalar_curvature_field() -> None:
    throat_radius = 1.3
    trajectory = generate_wormhole_trajectory(
        throat_radius=throat_radius, t_span=(0.0, 0.2), dt=0.02
    )
    geometry = trajectory.metadata["wormholeGeometry"]
    curvature = geometry["curvature"]
    mesh = geometry["embeddingMesh"]

    assert curvature["kind"] == "scalar-field"
    assert curvature["rendererHint"] == "scalar-field"
    assert curvature["name"] == "scalarCurvature"
    assert curvature["coordinates"] == ["l", "phi"]
    assert curvature["evaluation"] == "symbolic-exact"

    l_axis = np.asarray(curvature["axes"][0], dtype=float)
    phi_axis = np.asarray(curvature["axes"][1], dtype=float)
    values = np.asarray(curvature["values"], dtype=float)

    # The curvature grid aligns vertex-for-vertex with the embedding mesh so the
    # viewer can color the throat surface directly from this field.
    assert curvature["shape"] == mesh["shape"]
    assert np.allclose(l_axis, np.asarray(mesh["axes"][0], dtype=float))
    assert np.allclose(phi_axis, np.asarray(mesh["axes"][1], dtype=float))
    assert values.shape == (len(l_axis), len(phi_axis))

    # Samples are exact evaluations of the MetricGeometry scalar curvature, with
    # no phi dependence (broadcast across the azimuthal axis).
    metric = ellis_wormhole_metric(throat_radius)
    _t, ell, _phi = metric.coordinates
    expected_fn = sp.lambdify(ell, metric.scalar_curvature(), modules="numpy")
    expected = np.asarray(expected_fn(l_axis), dtype=float)
    assert np.allclose(values, expected[:, None])

    # The throat (l = 0) is sampled and is the curvature extremum R = -2/a^2,
    # decaying toward zero away from the throat.
    throat = curvature["throat"]
    assert throat["l"] == 0.0
    assert np.isclose(throat["scalarCurvature"], -2.0 / throat_radius**2)
    assert np.isclose(values.min(), -2.0 / throat_radius**2)
    assert float(values[0, 0]) > float(values[values.shape[0] // 2, 0])


def test_wormhole_reflected_turning_points_match_effective_potential() -> None:
    # A geodesic with angular momentum whose specific energy sits below the
    # throat barrier turns around symmetrically and never crosses the throat.
    throat_radius = 1.0
    angular_momentum = 2.0
    energy = float(np.sqrt(3.0))
    barrier = radial_throat_barrier(
        throat_radius=throat_radius, angular_momentum=angular_momentum
    )
    assert barrier == 1.0 + angular_momentum**2  # epsilon + L^2/a^2

    reduction = classify_radial_geodesic(
        throat_radius=throat_radius,
        energy=energy,
        angular_momentum=angular_momentum,
    )
    assert reduction.classification == "reflected"
    assert reduction.family == "ellis-wormhole"
    assert reduction.coordinate == "l"

    turning_points = np.asarray(reduction.turning_points, dtype=float)
    assert turning_points.shape == (2,)
    assert np.allclose(turning_points, [-1.0, 1.0])
    # The potential reaches exactly E^2 at the turning points (l_dot = 0 there).
    values = radial_effective_potential_values(
        turning_points,
        throat_radius=throat_radius,
        angular_momentum=angular_momentum,
    )
    assert np.allclose(values, energy**2)


def test_wormhole_radial_geodesic_energy_balance_and_classification() -> None:
    trajectory = generate_wormhole_trajectory(t_span=(0.0, 32.0), dt=0.02)
    ell = trajectory.states[:, 1]
    l_dot = trajectory.states[:, 4]
    energy = trajectory.metadata["orbitClassification"]["energy"]
    angular_momentum = trajectory.metadata["orbitClassification"]["angularMomentum"]

    # The default preset is a purely radial traversal: L = 0, so the centrifugal
    # term vanishes and the throat barrier is the bare timelike rest term.
    assert abs(angular_momentum) < 1e-12
    assert radial_turning_points(
        throat_radius=1.0, energy=energy, angular_momentum=angular_momentum
    ) == ()

    # The conserved E/L reduction reproduces the integrated radial velocity:
    # l_dot^2 = E^2 - V_eff^2(l) at every sample, to integration tolerance.
    potential = radial_effective_potential_values(
        ell, throat_radius=1.0, angular_momentum=angular_momentum
    )
    assert np.allclose(energy**2 - potential, l_dot**2, atol=1e-9)

    classification = trajectory.metadata["orbitClassification"]
    assert classification["classification"] == "traversing"
    assert classification["throatBarrier"] == 1.0
    # The analytic traversal class agrees with the measured rollout diagnostic.
    assert trajectory.metadata["diagnostics"]["throatTraversal"]["crossesThroat"] is True


def test_wormhole_exports_effective_potential_plot() -> None:
    trajectory = generate_wormhole_trajectory(t_span=(0.0, 32.0), dt=0.02)
    (plot,) = trajectory.metadata["potentialPlots"]

    assert plot["name"] == "wormhole_radial"
    assert plot["coordinate"] == "l"
    assert plot["rendererHint"] == "effective-potential"
    assert plot["energyKind"] == "specific-energy-squared"
    assert plot["classification"] == "traversing"
    assert plot["turningPoints"] == []
    assert plot["throatBarrier"] == 1.0
    assert plot["evaluation"] == "analytic-ellis-effective-potential"

    coordinate_values = np.asarray(plot["coordinateValues"], dtype=float)
    potential_values = np.asarray(plot["potentialValues"], dtype=float)
    assert coordinate_values.shape == potential_values.shape
    # The throat (l = 0) is sampled and is the potential maximum (barrier).
    assert np.isclose(coordinate_values.min(), -coordinate_values.max())
    throat_index = int(np.argmin(np.abs(coordinate_values)))
    assert np.isclose(coordinate_values[throat_index], 0.0)
    assert np.isclose(potential_values[throat_index], plot["throatBarrier"])
    assert potential_values[throat_index] >= potential_values.max() - 1e-12
    # The exported curve matches the analytic reduction sample-for-sample.
    expected = radial_effective_potential_values(
        coordinate_values, throat_radius=1.0, angular_momentum=plot["angularMomentum"]
    )
    assert np.allclose(potential_values, expected)


def test_wormhole_manifest_exposes_effective_potential() -> None:
    entry = system_entry(WORMHOLE)
    potentials = {item["name"]: item for item in entry["effectivePotentials"]}

    assert "wormhole_radial" in potentials
    potential = potentials["wormhole_radial"]
    assert potential["coordinate"] == "l"
    assert potential["conserved"] == "L"
    assert potential["plotSource"] == (
        "trajectory.metadata.potentialPlots[name=wormhole_radial]"
    )
    assert potential["turningPointsSource"] == (
        "trajectory.metadata.potentialPlots[name=wormhole_radial].turningPoints"
    )
    assert potential["classificationSource"] == "trajectory.metadata.orbitClassification"
    assert "wormholeEffectivePotential" in entry["lenses"]


def test_wormhole_manifest_declares_curvature_scalar_field() -> None:
    entry = system_entry(WORMHOLE)

    assert entry["geometry"]["curvature"] == {
        "kind": "scalar-field",
        "source": "trajectory.metadata.wormholeGeometry.curvature",
    }
    fields = {item["name"]: item for item in entry["fields"]}
    assert fields["scalarCurvature"]["kind"] == "scalar-field"
    assert fields["scalarCurvature"]["rendererHint"] == "scalar-field"
    assert fields["scalarCurvature"]["source"] == (
        "trajectory.metadata.wormholeGeometry.curvature"
    )
