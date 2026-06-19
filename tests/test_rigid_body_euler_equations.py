from __future__ import annotations

import numpy as np
import pytest

from engine.mechanics import (
    InertiaTensor,
    angular_momentum_magnitude,
    body_angular_momentum,
    euler_equations_rhs,
    rotational_kinetic_energy,
)
from engine.numerics import integrate_adaptive, integrate_fixed_step


def test_euler_equations_rhs_matches_body_frame_formula() -> None:
    inertia = InertiaTensor(
        np.array(
            [
                [2.0, 0.2, 0.0],
                [0.2, 3.0, 0.1],
                [0.0, 0.1, 4.0],
            ]
        )
    )
    omega = np.array([0.4, -0.3, 1.2])
    torque = np.array([0.1, 0.2, -0.05])

    rhs = euler_equations_rhs(inertia, torque=torque)

    expected = inertia.inverse @ (torque - np.cross(omega, inertia.matrix @ omega))
    assert np.allclose(rhs(1.5, omega), expected)


def test_euler_equations_accept_callable_torque_and_validate_shapes() -> None:
    inertia = InertiaTensor.diagonal([1.0, 2.0, 3.0])

    rhs = euler_equations_rhs(inertia, torque=lambda t, omega: [t, omega[0], 0.0])
    assert np.allclose(rhs(0.25, [0.5, 0.0, 0.0]), [0.25, 0.25, 0.0])

    with pytest.raises(ValueError, match="angular_velocity"):
        rhs(0.0, [1.0, 2.0])
    with pytest.raises(ValueError, match="torque"):
        euler_equations_rhs(inertia, torque=[1.0, 2.0])


def test_constant_torque_on_spherical_body_integrates_linearly() -> None:
    inertia = InertiaTensor.diagonal([2.0, 2.0, 2.0])
    initial = np.array([0.1, 0.2, -0.3])
    torque = np.array([0.4, -0.2, 0.6])
    rhs = euler_equations_rhs(inertia, torque=torque)

    time, states = integrate_fixed_step(rhs, initial_state=initial, t_span=(0.0, 2.0), dt=0.1)

    expected = initial + time[:, None] * torque[None, :] / 2.0
    assert np.allclose(states, expected, atol=1e-12)


def test_torque_free_rollout_conserves_energy_and_angular_momentum_magnitude_measured() -> None:
    inertia = InertiaTensor.diagonal([2.0, 3.0, 5.0])
    initial = np.array([0.31, 0.44, 1.2])
    rhs = euler_equations_rhs(inertia)

    _time, states = integrate_adaptive(
        rhs,
        initial_state=initial,
        t_span=(0.0, 10.0),
        sample_dt=0.02,
        rtol=1e-11,
        atol=1e-13,
        max_step=0.02,
    )

    energies = np.array([rotational_kinetic_energy(inertia, omega) for omega in states])
    momenta = np.array([angular_momentum_magnitude(inertia, omega) for omega in states])

    assert np.ptp(energies) / energies[0] < 1e-10
    assert np.ptp(momenta) / momenta[0] < 1e-10


def test_axisymmetric_body_has_steady_body_frame_precession() -> None:
    transverse_moment = 2.0
    axial_moment = 5.0
    axial_omega = 1.1
    transverse_omega = 0.3
    inertia = InertiaTensor.diagonal([transverse_moment, transverse_moment, axial_moment])
    rhs = euler_equations_rhs(inertia)

    time, states = integrate_adaptive(
        rhs,
        initial_state=[transverse_omega, 0.0, axial_omega],
        t_span=(0.0, 6.0),
        sample_dt=0.02,
        rtol=1e-11,
        atol=1e-13,
        max_step=0.02,
    )

    precession_rate = (axial_moment - transverse_moment) * axial_omega / transverse_moment
    expected = np.column_stack(
        [
            transverse_omega * np.cos(precession_rate * time),
            transverse_omega * np.sin(precession_rate * time),
            np.full_like(time, axial_omega),
        ]
    )

    assert np.allclose(states, expected, atol=1e-9)
    assert np.allclose(
        [body_angular_momentum(inertia, states[0]), body_angular_momentum(inertia, states[-1])],
        [inertia.matrix @ expected[0], inertia.matrix @ expected[-1]],
        atol=1e-9,
    )
