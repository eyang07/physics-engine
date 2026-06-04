import numpy as np
import sympy as sp

from engine.mechanics import CoordinateChart, HamiltonianSystem, legendre_transform
from engine.numerics import integrate_fixed_step
from systems.harmonic_oscillator import build_system as harmonic_oscillator
from systems.pendulum import build_system as pendulum


def test_coordinate_chart_exposes_tangent_and_cotangent_bundle_charts():
    chart = CoordinateChart.from_names("x y")
    x, y = chart.coordinates

    tangent = chart.tangent_bundle()
    cotangent = chart.cotangent_bundle()

    assert tangent.coordinates == (x, y)
    assert tangent.velocities == (sp.Symbol("x_dot", real=True), sp.Symbol("y_dot", real=True))
    assert tangent.state_symbols == tangent.coordinates + tangent.velocities
    assert cotangent.coordinates == (x, y)
    assert cotangent.momenta == (sp.Symbol("p_x", real=True), sp.Symbol("p_y", real=True))
    assert cotangent.state_symbols == cotangent.coordinates + cotangent.momenta


def test_harmonic_oscillator_legendre_transform():
    m, k = sp.symbols("m k")
    system = harmonic_oscillator(mass=m, spring_constant=k)
    (x,) = system.q
    (x_dot,) = system.qdot

    transform = legendre_transform(system)
    hamiltonian_system = transform.hamiltonian_system
    (p_x,) = hamiltonian_system.p

    expected_hamiltonian = p_x**2 / (2 * m) + k * x**2 / 2

    assert transform.momentum_definitions[p_x] == m * x_dot
    assert sp.simplify(transform.momentum_to_velocity[x_dot] - p_x / m) == 0
    assert sp.simplify(hamiltonian_system.hamiltonian - expected_hamiltonian) == 0
    assert hamiltonian_system.hamilton_equations() == (p_x / m, -k * x)


def test_pendulum_legendre_transform():
    m, ell, g = sp.symbols("m ell g")
    system = pendulum(mass=m, length=ell, gravity=g)
    (theta,) = system.q
    (theta_dot,) = system.qdot

    transform = legendre_transform(system)
    hamiltonian_system = transform.hamiltonian_system
    (p_theta,) = hamiltonian_system.p

    expected_hamiltonian = p_theta**2 / (2 * m * ell**2) + m * g * ell * (1 - sp.cos(theta))

    assert transform.momentum_definitions[p_theta] == m * ell**2 * theta_dot
    assert sp.simplify(transform.momentum_to_velocity[theta_dot] - p_theta / (m * ell**2)) == 0
    assert sp.simplify(hamiltonian_system.hamiltonian - expected_hamiltonian) == 0
    assert hamiltonian_system.hamilton_equations() == (
        p_theta / (m * ell**2),
        -g * ell * m * sp.sin(theta),
    )


def test_hamiltonian_system_numerical_rhs_for_harmonic_oscillator():
    chart = CoordinateChart.from_names("x")
    (x,) = chart.coordinates
    (p_x,) = chart.cotangent_bundle().momenta
    hamiltonian = p_x**2 / 2 + x**2 / 2
    system = HamiltonianSystem(chart.coordinates, (p_x,), hamiltonian, chart.time)

    rhs = system.numerical_rhs()
    time, states = integrate_fixed_step(rhs, initial_state=[1.0, 0.0], t_span=(0.0, 10.0), dt=0.01)
    energy = 0.5 * states[:, 0] ** 2 + 0.5 * states[:, 1] ** 2

    assert len(time) == len(states)
    assert np.max(np.abs(energy - energy[0])) < 1e-8


def test_lagrangian_and_hamiltonian_pendulum_flows_agree_numerically():
    lagrangian_system = pendulum(mass=1.0, length=1.0, gravity=9.81)
    hamiltonian_system = legendre_transform(lagrangian_system).hamiltonian_system

    lagrangian_rhs = lagrangian_system.numerical_rhs()
    hamiltonian_rhs = hamiltonian_system.numerical_rhs()

    _, lagrangian_states = integrate_fixed_step(
        lagrangian_rhs,
        initial_state=[0.85, 0.0],
        t_span=(0.0, 4.0),
        dt=0.01,
    )
    _, hamiltonian_states = integrate_fixed_step(
        hamiltonian_rhs,
        initial_state=[0.85, 0.0],
        t_span=(0.0, 4.0),
        dt=0.01,
    )

    theta_from_lagrangian = lagrangian_states[:, 0]
    theta_dot_from_lagrangian = lagrangian_states[:, 1]
    theta_from_hamiltonian = hamiltonian_states[:, 0]
    theta_dot_from_hamiltonian = hamiltonian_states[:, 1]

    assert np.max(np.abs(theta_from_lagrangian - theta_from_hamiltonian)) < 1e-10
    assert np.max(np.abs(theta_dot_from_lagrangian - theta_dot_from_hamiltonian)) < 1e-10
