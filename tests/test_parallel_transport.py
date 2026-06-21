from __future__ import annotations

import numpy as np
import sympy as sp

from engine.dynamics import MetricGeometry, two_sphere_metric
from scripts.generate_surface_geodesic import generate_surface_geodesic_trajectory


def test_parallel_transport_on_flat_space_is_trivial() -> None:
    x, y = sp.symbols("x y", real=True)
    geometry = MetricGeometry((x, y), sp.eye(2))
    parameter = np.linspace(0.0, 1.0, 101)
    curve = np.column_stack([parameter, parameter**2])
    initial = np.array([0.4, -0.7])

    transported = geometry.parallel_transport(parameter, curve, initial)

    assert np.allclose(transported, initial)


def test_sphere_latitude_holonomy_matches_enclosed_solid_angle() -> None:
    sphere = two_sphere_metric(radius=1.0)
    theta0 = 0.9
    parameter = np.linspace(0.0, 2.0 * np.pi, 2401)
    curve = np.column_stack([np.full_like(parameter, theta0), parameter])
    initial = np.array([1.0, 0.0])

    transported = sphere.parallel_transport(parameter, curve, initial)
    signed_angle = sphere.oriented_angle_2d(curve[0], initial, transported[-1])
    holonomy = signed_angle % (2.0 * np.pi)
    solid_angle = 2.0 * np.pi * (1.0 - np.cos(theta0))

    assert abs(holonomy - solid_angle) < 2e-5


def test_surface_geodesic_exports_parallel_transport_frame() -> None:
    trajectory = generate_surface_geodesic_trajectory(t_span=(0.0, 0.2), dt=0.01)
    payload = trajectory.metadata["parallelTransport"]
    vectors = np.asarray(payload["vectors"], dtype=float)
    embedded = np.asarray(payload["embeddedVectors"], dtype=float)

    assert payload["kind"] == "parallel-transport-frame"
    assert payload["rendererHint"] == "parallel-transport"
    assert payload["rigor"] == "measured"
    assert vectors.shape == (len(trajectory.time), 2)
    assert embedded.shape == (len(trajectory.time), 3)
    assert np.all(np.isfinite(vectors))
    assert np.all(np.isfinite(embedded))
