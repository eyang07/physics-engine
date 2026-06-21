from __future__ import annotations

import json

import numpy as np
import sympy as sp

from engine.export import system_entry
from scripts.example_specs import SURFACE_GEODESIC
from scripts.generate_surface_geodesic import (
    generate_surface_geodesic_trajectory,
    write_surface_geodesic_trajectory,
)
from systems.surface_geodesic import (
    cone_surface,
    hyperboloid_surface,
    paraboloid_surface,
    sphere_surface,
    torus_surface,
)


def _sphere_velocity(
    theta: np.ndarray,
    phi: np.ndarray,
    theta_dot: np.ndarray,
    phi_dot: np.ndarray,
    radius: float = 1.0,
) -> np.ndarray:
    d_theta = np.column_stack(
        [
            radius * np.cos(theta) * np.cos(phi),
            radius * np.cos(theta) * np.sin(phi),
            -radius * np.sin(theta),
        ]
    )
    d_phi = np.column_stack(
        [
            -radius * np.sin(theta) * np.sin(phi),
            radius * np.sin(theta) * np.cos(phi),
            np.zeros_like(theta),
        ]
    )
    return theta_dot[:, None] * d_theta + phi_dot[:, None] * d_phi


def test_surface_of_revolution_families_build_metric_geometries() -> None:
    surfaces = (
        torus_surface(),
        paraboloid_surface(),
        cone_surface(),
        hyperboloid_surface(),
    )

    for surface in surfaces:
        metric = surface.first_fundamental_form()
        geometry = surface.metric_geometry()
        assert metric.shape == (2, 2)
        assert sp.simplify(metric - metric.T) == sp.zeros(2, 2)
        assert geometry.dimension == 2
        assert geometry.geodesic_system().state == (
            surface.meridian,
            surface.azimuth,
            surface.velocities[0],
            surface.velocities[1],
        )
        assert sp.simplify(surface.clairaut_quantity() - metric[1, 1] * surface.velocities[1]) == 0


def test_sphere_surface_metric_recovers_round_sphere() -> None:
    radius = sp.Symbol("R", positive=True)
    surface = sphere_surface(radius=radius)
    u, _phi = surface.coordinates

    assert surface.first_fundamental_form() == sp.diag(radius**2, radius**2 * sp.sin(u) ** 2)
    assert sp.simplify(surface.metric_geometry().scalar_curvature() - 2 / radius**2) == 0


def test_gaussian_curvature_matches_standard_surface_closed_forms() -> None:
    radius = sp.Symbol("R", positive=True)
    sphere = sphere_surface(radius=radius)
    assert sp.simplify(sphere.gaussian_curvature() - 1 / radius**2) == 0

    major, minor = sp.symbols("R_major r_minor", positive=True)
    torus = torus_surface(major_radius=major, minor_radius=minor)
    u, _phi = torus.coordinates
    expected_torus = sp.cos(u) / (minor * (major + minor * sp.cos(u)))
    assert sp.simplify(torus.gaussian_curvature() - expected_torus) == 0

    scale = sp.Symbol("a", positive=True)
    paraboloid = paraboloid_surface(scale=scale)
    u, _phi = paraboloid.coordinates
    expected_paraboloid = 4 * scale**2 / (1 + 4 * scale**2 * u**2) ** 2
    assert sp.simplify(paraboloid.gaussian_curvature() - expected_paraboloid) == 0

    assert sp.simplify(cone_surface().gaussian_curvature()) == 0


def test_surface_geodesic_conserves_clairaut_quantity_measured() -> None:
    trajectory = generate_surface_geodesic_trajectory(t_span=(0.0, 5.0), dt=0.01)
    residuals = {
        record["name"]: record
        for record in trajectory.metadata["invariantResiduals"]
    }

    assert trajectory.metadata["family"] == "torus"
    assert trajectory.state_names == ("u", "phi", "u_dot", "phi_dot", "x", "y", "z")
    assert set(trajectory.series) == {"H", "clairaut"}
    assert residuals["clairaut"]["rigor"] == "measured"
    assert residuals["H"]["rigor"] == "measured"
    assert residuals["clairaut"]["maxAbs"] < 1e-8
    assert residuals["H"]["maxAbs"] < 1e-8


def test_surface_geodesic_exports_mesh_geodesic_and_curvature_payloads() -> None:
    trajectory = generate_surface_geodesic_trajectory(t_span=(0.0, 0.1), dt=0.01)
    geometry = trajectory.metadata["surfaceGeometry"]
    mesh = geometry["surfaceMesh"]
    geodesic = geometry["geodesic"]
    curvature = geometry["curvature"]

    assert geometry["rendererHint"] == "surface-geodesic"
    assert mesh["kind"] == "surface-mesh"
    assert mesh["rendererHint"] == "surface-geodesic"
    assert mesh["shape"] == [49, 65]
    assert np.asarray(mesh["points"], dtype=float).shape == (49, 65, 3)
    assert len(mesh["triangles"]) == 2 * (49 - 1) * (65 - 1)

    assert geodesic["kind"] == "embedded-polyline"
    assert geodesic["rendererHint"] == "surface-geodesic"
    assert np.allclose(np.asarray(geodesic["points"], dtype=float), trajectory.states[:, 4:7])

    assert curvature["kind"] == "scalar-field"
    assert curvature["rendererHint"] == "scalar-field"
    assert curvature["evaluation"] == "symbolic-exact"
    values = np.asarray(curvature["values"], dtype=float)
    assert values.shape == (49, 65)
    assert np.all(np.isfinite(values))
    gauss_bonnet = geometry["curvatureDiagnostics"]["gaussBonnet"]
    assert gauss_bonnet["kind"] == "gauss-bonnet-diagnostic"
    assert gauss_bonnet["rigor"] == "measured"
    assert gauss_bonnet["eulerCharacteristic"] == 0
    assert abs(gauss_bonnet["residual"]) < 1e-10


def test_sphere_gauss_bonnet_matches_two_pi_chi_measured() -> None:
    trajectory = generate_surface_geodesic_trajectory(
        family="sphere",
        t_span=(0.0, 0.1),
        dt=0.01,
    )
    gauss_bonnet = trajectory.metadata["surfaceGeometry"]["curvatureDiagnostics"]["gaussBonnet"]

    assert gauss_bonnet["rigor"] == "measured"
    assert gauss_bonnet["eulerCharacteristic"] == 2
    assert abs(gauss_bonnet["integralCurvature"] - 4.0 * np.pi) < 1e-4
    assert abs(gauss_bonnet["residual"]) < 1e-4


def test_surface_geodesic_manifest_declares_surface_channels() -> None:
    entry = system_entry(SURFACE_GEODESIC)

    assert entry["geometry"]["kind"] == "surface-geodesic"
    assert entry["geometry"]["rendererHint"] == "surface-geodesic"
    assert entry["geometry"]["surfaceMesh"]["source"] == (
        "trajectory.metadata.surfaceGeometry.surfaceMesh"
    )
    assert entry["geometry"]["geodesic"]["source"] == (
        "trajectory.metadata.surfaceGeometry.geodesic"
    )
    assert entry["geometry"]["curvature"]["source"] == (
        "trajectory.metadata.surfaceGeometry.curvature"
    )
    assert entry["geometry"]["parallelTransport"]["source"] == (
        "trajectory.metadata.parallelTransport"
    )
    assert entry["fields"] == [
        {
            "name": "gaussianCurvature",
            "kind": "scalar-field",
            "rendererHint": "scalar-field",
            "source": "trajectory.metadata.surfaceGeometry.curvature",
        }
    ]


def test_surface_geodesic_sphere_family_recovers_great_circle() -> None:
    trajectory = generate_surface_geodesic_trajectory(
        family="sphere",
        t_span=(0.0, 4.0),
        dt=0.01,
    )
    states = trajectory.states
    positions = states[:, 4:7]
    velocities = _sphere_velocity(states[:, 0], states[:, 1], states[:, 2], states[:, 3])
    angular_momentum = np.cross(positions, velocities)
    initial_plane_normal = angular_momentum[0] / np.linalg.norm(angular_momentum[0])

    assert trajectory.metadata["family"] == "sphere"
    assert np.max(np.abs(np.linalg.norm(positions, axis=1) - 1.0)) < 1e-12
    assert np.max(np.abs(positions @ initial_plane_normal)) < 5e-9
    assert np.max(np.linalg.norm(angular_momentum - angular_momentum[0], axis=1)) < 5e-8


def test_surface_geodesic_script_writes_primary_and_viewer_outputs(tmp_path) -> None:
    output = tmp_path / "data" / "surface.json"
    viewer_output = tmp_path / "viewer" / "surface.json"

    write_surface_geodesic_trajectory(
        output,
        viewer_output=viewer_output,
        t_end=0.05,
        dt=0.01,
    )

    assert json.loads(output.read_text(encoding="utf-8")) == json.loads(
        viewer_output.read_text(encoding="utf-8")
    )
