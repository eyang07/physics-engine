import json

import numpy as np
import sympy as sp

from scripts.generate_charged_particle import (
    generate_charged_particle_trajectory,
    write_charged_particle_trajectory,
)
from scripts.generate_sphere_geodesic import (
    generate_sphere_geodesic_trajectory,
    write_sphere_geodesic_trajectory,
)
from systems.charged_particle import build_uniform_magnetic_field_system
from systems.sphere_geodesic import build_system as sphere_geodesic


def sphere_velocity(theta, phi, theta_dot, phi_dot, radius=1.0):
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


def test_sphere_geodesic_equations():
    m, radius = sp.symbols("m R")
    system = sphere_geodesic(mass=m, radius=radius)
    theta, _phi = system.q
    theta_dot, phi_dot = system.qdot
    theta_ddot, phi_ddot = system.qddot

    theta_equation, phi_equation = system.euler_lagrange_expressions()

    expected_theta = m * radius**2 * (
        theta_ddot - sp.sin(theta) * sp.cos(theta) * phi_dot**2
    )
    expected_phi = m * radius**2 * (
        sp.sin(theta) ** 2 * phi_ddot
        + 2 * sp.sin(theta) * sp.cos(theta) * theta_dot * phi_dot
    )

    assert sp.simplify(theta_equation - expected_theta) == 0
    assert sp.simplify(phi_equation - expected_phi) == 0


def test_sphere_geodesic_generated_path_stays_on_great_circle():
    trajectory = generate_sphere_geodesic_trajectory(t_span=(0.0, 4.0), dt=0.01)
    states = trajectory.states
    positions = states[:, 4:7]
    velocities = sphere_velocity(states[:, 0], states[:, 1], states[:, 2], states[:, 3])
    angular_momentum = np.cross(positions, velocities)
    initial_plane_normal = angular_momentum[0] / np.linalg.norm(angular_momentum[0])

    assert trajectory.state_names == (
        "theta",
        "phi",
        "theta_dot",
        "phi_dot",
        "x",
        "y",
        "z",
    )
    assert np.max(np.abs(np.linalg.norm(positions, axis=1) - 1.0)) < 1e-12
    assert np.max(np.abs(positions @ initial_plane_normal)) < 5e-9
    assert np.max(np.linalg.norm(angular_momentum - angular_momentum[0], axis=1)) < 5e-8


def test_charged_particle_lorentz_force_equations():
    m, q, b_z = sp.symbols("m q B_z")
    system = build_uniform_magnetic_field_system(
        mass=m,
        charge=q,
        magnetic_field_z=b_z,
    )
    _x, _y, _z = system.q
    x_dot, y_dot, _z_dot = system.qdot
    x_ddot, y_ddot, z_ddot = system.qddot

    equations = system.euler_lagrange_expressions()

    assert equations == (
        m * x_ddot - b_z * q * y_dot,
        b_z * q * x_dot + m * y_ddot,
        m * z_ddot,
    )


def test_charged_particle_generated_motion_conserves_speed_and_z_velocity():
    trajectory = generate_charged_particle_trajectory(t_span=(0.0, 8.0), dt=0.01)
    velocities = trajectory.states[:, 3:6]
    speed_squared = np.sum(velocities**2, axis=1)

    assert trajectory.state_names == ("x", "y", "z", "x_dot", "y_dot", "z_dot")
    assert np.max(np.abs(speed_squared - speed_squared[0])) < 1e-10
    assert np.max(np.abs(velocities[:, 2] - velocities[0, 2])) < 1e-12


def test_new_example_scripts_write_primary_and_viewer_outputs(tmp_path):
    sphere_output = tmp_path / "data" / "sphere.json"
    sphere_viewer_output = tmp_path / "viewer" / "sphere.json"
    charged_output = tmp_path / "data" / "charged.json"
    charged_viewer_output = tmp_path / "viewer" / "charged.json"

    write_sphere_geodesic_trajectory(
        sphere_output,
        viewer_output=sphere_viewer_output,
        t_end=0.05,
        dt=0.01,
    )
    write_charged_particle_trajectory(
        charged_output,
        viewer_output=charged_viewer_output,
        t_end=0.05,
        dt=0.01,
    )

    assert json.loads(sphere_output.read_text(encoding="utf-8")) == json.loads(
        sphere_viewer_output.read_text(encoding="utf-8")
    )
    assert json.loads(charged_output.read_text(encoding="utf-8")) == json.loads(
        charged_viewer_output.read_text(encoding="utf-8")
    )

