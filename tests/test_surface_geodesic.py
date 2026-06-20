from __future__ import annotations

import json

import numpy as np
import sympy as sp

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
