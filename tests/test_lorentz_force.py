from __future__ import annotations

import numpy as np
import pytest
import sympy as sp

from engine.dynamics import invariant_residuals
from engine.electrodynamics import (
    CovariantLorentzForce,
    lorentz_force_operator,
    lorentz_force_system,
    lorentz_four_force,
)
from engine.numerics import integrate_fixed_step
from engine.relativity import ProperTimeWorldline


def test_lorentz_force_operator_has_newtonian_spatial_limit() -> None:
    vx, vy, vz = sp.symbols("v_x v_y v_z", real=True)
    ex, ey, ez = sp.symbols("E_x E_y E_z", real=True)
    bx, by, bz = sp.symbols("B_x B_y B_z", real=True)
    charge, mass, light_speed = sp.symbols("q m c", positive=True)
    worldline = ProperTimeWorldline(
        dimension=4,
        mass=mass,
        light_speed=light_speed,
    )
    momentum = worldline.four_momentum_from_velocity((vx, vy, vz))

    four_force = lorentz_four_force(
        (ex, ey, ez),
        (bx, by, bz),
        momentum,
        charge=charge,
        mass=mass,
        light_speed=light_speed,
    )
    coordinate_force = worldline.coordinate_momentum_derivative_from_four_force(
        (vx, vy, vz),
        four_force,
    )

    expected = (
        charge * (ex + vy * bz - vz * by),
        charge * (ey + vz * bx - vx * bz),
        charge * (ez + vx * by - vy * bx),
    )
    assert tuple(
        sp.simplify(component - expected_component)
        for component, expected_component in zip(coordinate_force, expected)
    ) == (0, 0, 0)


def test_lorentz_force_is_orthogonal_to_four_momentum_symbolically() -> None:
    ex, ey, ez = sp.symbols("E_x E_y E_z", real=True)
    bx, by, bz = sp.symbols("B_x B_y B_z", real=True)
    p0, p1, p2, p3 = sp.symbols("p0 p1 p2 p3", real=True)
    charge, mass = sp.symbols("q m", positive=True)
    worldline = ProperTimeWorldline(dimension=4, mass=mass, light_speed=sp.Integer(1))

    momentum = (p0, p1, p2, p3)
    force = lorentz_four_force(
        (ex, ey, ez),
        (bx, by, bz),
        momentum,
        charge=charge,
        mass=mass,
    )

    assert sp.simplify(worldline.metric.inner_product(momentum, force.components)) == 0


def test_uniform_magnetic_field_preserves_mass_shell_and_four_velocity_norm() -> None:
    mass = 1.0
    magnetic_field = 0.8
    p_spatial = np.array([0.36, 0.0, 0.24], dtype=float)
    p0 = float(np.sqrt(mass**2 + np.dot(p_spatial, p_spatial)))
    system = lorentz_force_system(
        (0, 0, 0),
        (0, 0, magnetic_field),
        charge=1.0,
        mass=mass,
    )

    _, states = integrate_fixed_step(
        system.numerical_rhs(),
        initial_state=[0.0, 0.0, 0.0, 0.0, p0, *p_spatial],
        t_span=(0.0, 4.0),
        dt=0.002,
    )

    worldline = ProperTimeWorldline(
        dimension=4,
        mass=sp.Float(mass),
        light_speed=sp.Integer(1),
    )
    mass_shell = np.asarray(worldline.mass_shell_series(states), dtype=float)
    four_velocity_norm = (
        -states[:, 4] ** 2 + np.sum(states[:, 5:] ** 2, axis=1)
    ) / mass**2
    p_z = states[:, 7]

    assert invariant_residuals({"mass_shell": mass_shell})["mass_shell"].max_abs < 1e-10
    assert (
        invariant_residuals({"four_velocity_norm": four_velocity_norm})[
            "four_velocity_norm"
        ].max_abs
        < 1e-10
    )
    assert invariant_residuals({"p_z": p_z})["p_z"].max_abs < 1e-12


def test_first_order_system_uses_proper_time_worldline_state() -> None:
    q, m, bz = sp.symbols("q m B_z", positive=True)
    force = CovariantLorentzForce(
        electric=(0, 0, 0),
        magnetic=(0, 0, bz),
        charge=q,
        mass=m,
    )
    system = force.first_order_system()
    p0, p1, p2, p3 = force.worldline.four_momentum_symbols

    assert system.state == (*force.worldline.coordinates, p0, p1, p2, p3)
    assert system.time == force.worldline.proper_time
    assert system.rhs[:4] == (p0 / m, p1 / m, p2 / m, p3 / m)
    assert system.rhs[4:] == (0, q * bz * p2 / m, -q * bz * p1 / m, 0)


def test_lorentz_force_validates_shapes() -> None:
    with pytest.raises(ValueError, match="electric"):
        lorentz_force_operator((1, 2), (0, 0, 1))
    with pytest.raises(ValueError, match="magnetic"):
        lorentz_force_operator((1, 2, 3), (0, 1))
    with pytest.raises(ValueError, match="momentum"):
        lorentz_four_force((0, 0, 0), (0, 0, 1), (1, 2, 3))
