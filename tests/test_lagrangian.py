import numpy as np
import sympy as sp

from engine.export import Trajectory
from engine.mechanics import CoordinateChart, LagrangianSystem
from engine.mechanics.constraints import (
    HolonomicConstraint,
    constrained_euler_lagrange_equations,
)
from engine.mechanics.symmetries import (
    InfinitesimalSymmetry,
    is_variational_symmetry,
    noether_charge,
)
from engine.mechanics.transforms import pullback_lagrangian, pullback_momenta
from engine.numerics import integrate_fixed_step
from systems.harmonic_oscillator import build_system as harmonic_oscillator


def test_harmonic_oscillator_euler_lagrange_equation():
    m, k = sp.symbols("m k")
    system = harmonic_oscillator(mass=m, spring_constant=k)
    (x,) = system.q
    (x_ddot,) = system.qddot

    (equation,) = system.euler_lagrange_equations()

    assert sp.simplify(equation.lhs - (m * x_ddot + k * x)) == 0


def test_harmonic_oscillator_energy():
    m, k = sp.symbols("m k")
    system = harmonic_oscillator(mass=m, spring_constant=k)
    (x,) = system.q
    (x_dot,) = system.qdot

    expected = sp.Rational(1, 2) * m * x_dot**2 + sp.Rational(1, 2) * k * x**2

    assert sp.simplify(system.energy() - expected) == 0


def test_coordinate_pullback_cartesian_free_particle_to_polar():
    cartesian = CoordinateChart.from_names("x y")
    x, y = cartesian.coordinates
    x_dot, y_dot = cartesian.velocities
    m = sp.Symbol("m", positive=True)
    lagrangian = sp.Rational(1, 2) * m * (x_dot**2 + y_dot**2)

    polar = CoordinateChart.from_names("r theta")
    r, theta = polar.coordinates
    r_dot, theta_dot = polar.velocities

    pulled_back = pullback_lagrangian(
        lagrangian,
        cartesian.coordinates,
        polar.coordinates,
        {
            x: r * sp.cos(theta),
            y: r * sp.sin(theta),
        },
        time=cartesian.time,
        old_velocities=cartesian.velocities,
        new_velocities=polar.velocities,
    )

    expected = sp.Rational(1, 2) * m * (r_dot**2 + r**2 * theta_dot**2)
    assert sp.trigsimp(sp.simplify(pulled_back - expected)) == 0


def test_cotangent_pullback_cartesian_momenta_to_polar():
    cartesian = CoordinateChart.from_names("x y")
    x, y = cartesian.coordinates
    p_x, p_y = cartesian.cotangent_bundle().momenta

    polar = CoordinateChart.from_names("r theta")
    r, theta = polar.coordinates

    p_r, p_theta = pullback_momenta(
        (p_x, p_y),
        cartesian.coordinates,
        polar.coordinates,
        {
            x: r * sp.cos(theta),
            y: r * sp.sin(theta),
        },
    )

    assert p_r == p_x * sp.cos(theta) + p_y * sp.sin(theta)
    assert sp.simplify(p_theta - r * (-p_x * sp.sin(theta) + p_y * sp.cos(theta))) == 0


def test_holonomic_constraint_adds_lagrange_multiplier_equations():
    chart = CoordinateChart.from_names("x y")
    x, y = chart.coordinates
    x_dot, y_dot = chart.velocities
    x_ddot, y_ddot = chart.accelerations
    m, ell = sp.symbols("m ell", positive=True)

    lagrangian = sp.Rational(1, 2) * m * (x_dot**2 + y_dot**2)
    system = LagrangianSystem(chart.coordinates, lagrangian, chart.time, chart.velocities)
    constraint = HolonomicConstraint(x**2 + y**2 - ell**2)

    constrained = constrained_euler_lagrange_equations(system, [constraint])
    (lam,) = constrained.multipliers

    assert constrained.equations == (
        sp.Eq(m * x_ddot - 2 * lam * x, 0),
        sp.Eq(m * y_ddot - 2 * lam * y, 0),
    )
    assert constrained.acceleration_constraints == (
        sp.Eq(2 * x * x_ddot + 2 * x_dot**2 + 2 * y * y_ddot + 2 * y_dot**2, 0),
    )


def test_noether_translation_symmetry_returns_momentum():
    chart = CoordinateChart.from_names("x")
    (x,) = chart.coordinates
    (x_dot,) = chart.velocities
    m = sp.Symbol("m", positive=True)
    lagrangian = sp.Rational(1, 2) * m * x_dot**2
    system = LagrangianSystem(chart.coordinates, lagrangian, chart.time, chart.velocities)

    symmetry = InfinitesimalSymmetry.vertical(system.q, [sp.Integer(1)])

    assert is_variational_symmetry(system, symmetry)
    assert sp.simplify(noether_charge(system, symmetry) - m * x_dot) == 0


def test_numeric_rhs_integrates_harmonic_oscillator_with_nearly_constant_energy():
    system = harmonic_oscillator(mass=1.0, spring_constant=1.0)
    rhs = system.numerical_rhs()

    time, states = integrate_fixed_step(rhs, initial_state=[1.0, 0.0], t_span=(0.0, 10.0), dt=0.01)

    x = states[:, 0]
    x_dot = states[:, 1]
    energy = 0.5 * x_dot**2 + 0.5 * x**2

    assert len(time) == len(states)
    assert np.max(np.abs(energy - energy[0])) < 1e-8


def test_trajectory_exports_json_ready_dict():
    trajectory = Trajectory.from_arrays(
        time=[0.0, 0.1],
        states=[[1.0, 0.0], [0.995, -0.1]],
        state_names=["x", "x_dot"],
    )

    assert trajectory.to_dict() == {
        "time": [0.0, 0.1],
        "state_names": ["x", "x_dot"],
        "states": [[1.0, 0.0], [0.995, -0.1]],
    }
