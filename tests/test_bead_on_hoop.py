import numpy as np
import sympy as sp

from scripts.generate_bead_on_hoop import generate_bead_on_hoop_trajectory
from systems.bead_on_hoop import build_system


def test_bead_on_rotating_hoop_equation_and_energy():
    m, radius, g, omega = sp.symbols("m R g Omega")
    system = build_system(mass=m, radius=radius, gravity=g, angular_speed=omega)
    (theta,) = system.q
    (theta_dot,) = system.qdot
    (theta_ddot,) = system.qddot

    (equation,) = system.euler_lagrange_expressions()
    expected = (
        m * radius**2 * theta_ddot
        - m * radius**2 * omega**2 * sp.sin(theta) * sp.cos(theta)
        + m * g * radius * sp.sin(theta)
    )
    expected_energy = (
        m * radius**2 * theta_dot**2 / 2
        - m * radius**2 * omega**2 * sp.sin(theta) ** 2 / 2
        - m * g * radius * sp.cos(theta)
    )

    assert sp.simplify(equation - expected) == 0
    assert sp.simplify(system.energy() - expected_energy) == 0


def test_bead_on_rotating_hoop_generated_path_stays_on_constraint():
    trajectory = generate_bead_on_hoop_trajectory(t_span=(0.0, 4.0), dt=0.01)
    theta, _theta_dot, x, y, z = trajectory.states.T
    radius = np.sqrt(x**2 + y**2 + z**2)

    assert trajectory.state_names == ("theta", "theta_dot", "x", "y", "z")
    assert np.max(np.abs(radius - 1.0)) < 1e-12
    assert np.max(np.abs(z + np.cos(theta))) < 1e-12
    assert trajectory.metadata is not None
    assert trajectory.metadata["angular_speed"] == 4.0
    assert "potentialPlots" in trajectory.metadata
    hints = trajectory.metadata["rendererHints"]
    assert hints["referenceGeometry"][0]["kind"] == "constraintHoop"
    assert hints["referenceGeometry"][0]["radius"] == 1.0
    assert hints["camera"]["target"] == [0.0, 0.0, 0.0]
