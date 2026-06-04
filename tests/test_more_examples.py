import numpy as np
import sympy as sp

from scripts.generate_ideal_spring import generate_ideal_spring_trajectory
from scripts.generate_kepler_problem import generate_kepler_trajectory
from scripts.generate_uniform_gravity import generate_uniform_gravity_trajectory
from systems.ideal_spring import build_system as ideal_spring
from systems.kepler_problem import build_system as kepler_problem
from systems.uniform_gravity import build_system as uniform_gravity


def test_uniform_gravity_equations():
    m, g = sp.symbols("m g")
    system = uniform_gravity(mass=m, gravity=g)
    x_ddot, z_ddot = system.qddot
    x_equation, z_equation = system.euler_lagrange_expressions()

    assert sp.simplify(x_equation - m * x_ddot) == 0
    assert sp.simplify(z_equation - (g * m + m * z_ddot)) == 0


def test_uniform_gravity_generated_motion_is_parabolic():
    trajectory = generate_uniform_gravity_trajectory(t_span=(0.0, 0.5), dt=0.005)
    time = trajectory.time
    x, z, x_dot, z_dot = trajectory.states.T

    assert np.max(np.abs(x - x_dot[0] * time)) < 1e-12
    assert np.max(np.abs(z - (z_dot[0] * time - 0.5 * 9.81 * time**2))) < 1e-10
    assert np.max(np.abs(x_dot - x_dot[0])) < 1e-12
    assert np.max(np.abs(z_dot - (z_dot[0] - 9.81 * time))) < 1e-10


def test_ideal_spring_equation_and_energy():
    m, k = sp.symbols("m k")
    system = ideal_spring(mass=m, spring_constant=k)
    (x,) = system.q
    (x_dot,) = system.qdot
    (x_ddot,) = system.qddot

    assert system.euler_lagrange_expressions() == (k * x + m * x_ddot,)
    assert sp.simplify(system.energy() - (m * x_dot**2 / 2 + k * x**2 / 2)) == 0


def test_ideal_spring_generated_motion_conserves_energy():
    trajectory = generate_ideal_spring_trajectory(t_span=(0.0, 8.0), dt=0.01)
    x, x_dot = trajectory.states.T
    energy = 0.5 * x_dot**2 + 0.5 * x**2

    assert np.max(np.abs(energy - energy[0])) < 1e-8


def test_kepler_equations():
    m, mu = sp.symbols("m mu")
    system = kepler_problem(mass=m, gravitational_parameter=mu)
    r, _phi = system.q
    r_dot, phi_dot = system.qdot
    r_ddot, phi_ddot = system.qddot

    radial, angular = system.euler_lagrange_expressions()

    assert sp.simplify(radial - (m * r_ddot - m * r * phi_dot**2 + m * mu / r**2)) == 0
    assert sp.simplify(angular - (m * r**2 * phi_ddot + 2 * m * r * r_dot * phi_dot)) == 0


def test_kepler_generated_motion_conserves_energy_and_angular_momentum():
    trajectory = generate_kepler_trajectory(t_span=(0.0, 8.0), dt=0.01)
    r, _phi, r_dot, phi_dot, _x, _y = trajectory.states.T
    angular_momentum = r**2 * phi_dot
    energy = 0.5 * (r_dot**2 + r**2 * phi_dot**2) - 1.0 / r

    assert np.max(np.abs(angular_momentum - angular_momentum[0])) < 1e-8
    assert np.max(np.abs(energy - energy[0])) < 1e-8
