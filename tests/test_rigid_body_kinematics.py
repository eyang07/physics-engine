from __future__ import annotations

import numpy as np
import pytest
import sympy as sp

from engine.mechanics import (
    InertiaTensor,
    attitude_euler_rhs,
    body_angular_velocity_from_rotation,
    body_to_space_angular_velocity,
    euler_angles_to_rotation_matrix,
    normalize_quaternion,
    orientation_series,
    quaternion_derivative,
    quaternion_multiply,
    quaternion_to_rotation_matrix,
    rotation_matrix_to_euler_angles,
    rotation_matrix_to_quaternion,
    skew_symmetric,
    space_angular_velocity_from_rotation,
    space_to_body_angular_velocity,
    vee_skew,
)
from engine.numerics import integrate_adaptive


def test_quaternion_matrix_round_trip_preserves_rotation() -> None:
    quaternion = normalize_quaternion([0.8, -0.2, 0.3, 0.45])
    rotation = quaternion_to_rotation_matrix(quaternion)
    recovered = rotation_matrix_to_quaternion(rotation)

    assert np.allclose(rotation.T @ rotation, np.eye(3))
    assert np.isclose(np.linalg.det(rotation), 1.0)
    assert np.allclose(
        quaternion_to_rotation_matrix(recovered),
        rotation,
        atol=1e-12,
    )


def test_quaternion_normalization_rejects_zero() -> None:
    assert np.isclose(np.linalg.norm(normalize_quaternion([2.0, 0.0, 0.0, 0.0])), 1.0)
    with pytest.raises(ValueError, match="positive"):
        normalize_quaternion([0.0, 0.0, 0.0, 0.0])


def test_euler_matrix_round_trip_for_non_singular_angles() -> None:
    angles = (0.35, -0.42, 0.91)
    rotation = euler_angles_to_rotation_matrix(*angles)
    recovered = rotation_matrix_to_euler_angles(rotation)

    assert np.allclose(recovered, angles)
    assert np.allclose(euler_angles_to_rotation_matrix(*recovered), rotation)


def test_symbolic_euler_matrix_matches_expected_entries() -> None:
    roll, pitch, yaw = sp.symbols("roll pitch yaw", real=True)
    rotation = euler_angles_to_rotation_matrix(roll, pitch, yaw)

    assert isinstance(rotation, sp.Matrix)
    assert rotation.shape == (3, 3)
    assert sp.simplify(rotation[2, 0] + sp.sin(pitch)) == 0
    assert sp.simplify(rotation[0, 0] - sp.cos(yaw) * sp.cos(pitch)) == 0


def test_body_and_space_angular_velocity_relations() -> None:
    rotation = euler_angles_to_rotation_matrix(0.4, -0.25, 0.7)
    body_omega = np.array([0.3, -0.4, 1.2], dtype=float)
    rotation_derivative = rotation @ skew_symmetric(body_omega)

    recovered_body = body_angular_velocity_from_rotation(rotation, rotation_derivative)
    recovered_space = space_angular_velocity_from_rotation(rotation, rotation_derivative)

    assert np.allclose(recovered_body, body_omega)
    assert np.allclose(recovered_space, rotation @ body_omega)
    assert np.allclose(body_to_space_angular_velocity(rotation, body_omega), recovered_space)
    assert np.allclose(space_to_body_angular_velocity(rotation, recovered_space), body_omega)


def test_space_angular_velocity_relation() -> None:
    rotation = euler_angles_to_rotation_matrix(-0.2, 0.31, -0.8)
    space_omega = np.array([-0.7, 0.5, 0.2], dtype=float)
    rotation_derivative = skew_symmetric(space_omega) @ rotation

    assert np.allclose(
        space_angular_velocity_from_rotation(rotation, rotation_derivative),
        space_omega,
    )
    assert np.allclose(
        body_angular_velocity_from_rotation(rotation, rotation_derivative),
        rotation.T @ space_omega,
    )


def test_vee_rejects_non_skew_matrix() -> None:
    assert np.allclose(vee_skew(skew_symmetric([1.0, 2.0, 3.0])), [1.0, 2.0, 3.0])
    with pytest.raises(ValueError, match="not skew"):
        vee_skew(np.eye(3))


def test_quaternion_multiply_identity_and_known_product() -> None:
    identity = [1.0, 0.0, 0.0, 0.0]
    q = normalize_quaternion([0.5, 0.5, -0.5, 0.5])
    assert np.allclose(quaternion_multiply(identity, q), q)
    # i ⊗ j = k in (w, x, y, z) convention.
    assert np.allclose(
        quaternion_multiply([0, 1, 0, 0], [0, 0, 1, 0]), [0, 0, 0, 1]
    )


def test_quaternion_derivative_inverts_to_body_angular_velocity() -> None:
    # dq = 1/2 q ⊗ (0, omega), so 2 conj(q) ⊗ dq recovers the pure quaternion
    # (0, omega) exactly for a unit quaternion.
    q = normalize_quaternion([0.9, 0.1, -0.2, 0.3])
    omega = np.array([0.4, -0.7, 1.1])
    dq = quaternion_derivative(q, omega)
    conjugate = q * np.array([1.0, -1.0, -1.0, -1.0])
    recovered = 2.0 * quaternion_multiply(conjugate, dq)
    assert np.isclose(recovered[0], 0.0, atol=1e-12)
    assert np.allclose(recovered[1:], omega, atol=1e-12)


def test_attitude_euler_rollout_conserves_space_angular_momentum() -> None:
    inertia = InertiaTensor.diagonal((1.0, 2.0, 3.2))
    initial = np.array([1.0, 0.0, 0.0, 0.0, 0.05, 1.0, 0.05])
    _time, states = integrate_adaptive(
        attitude_euler_rhs(inertia),
        initial_state=initial,
        t_span=(0.0, 5.0),
        sample_dt=0.05,
        rtol=1e-11,
        atol=1e-13,
        max_step=0.05,
    )
    quaternions = states[:, :4]
    omega = states[:, 4:]
    # Torque-free: angular momentum is constant in the space frame.
    space_momentum = np.array(
        [quaternion_to_rotation_matrix(q) @ (inertia.matrix @ w) for q, w in zip(quaternions, omega)]
    )
    drift = float(np.max(np.linalg.norm(space_momentum - space_momentum[0], axis=1)))
    assert drift < 1e-9


def test_orientation_series_is_unit_and_sign_continuous() -> None:
    # A sequence including a sign flip should be re-aligned to stay continuous.
    base = normalize_quaternion([0.9, 0.1, -0.2, 0.3])
    payload = orientation_series([base, -base, base])
    quaternions = np.asarray(payload["quaternion"])
    assert payload["convention"] == "quaternion-wxyz"
    assert payload["rigor"] == "measured"
    assert np.allclose(np.linalg.norm(quaternions, axis=1), 1.0)
    # No sign flip between consecutive samples after alignment.
    assert np.all(np.sum(quaternions[:-1] * quaternions[1:], axis=1) > 0.0)
    # Body axes are the orthonormal columns of the rotation matrix.
    e1 = np.asarray(payload["bodyAxes"]["e1"])
    e2 = np.asarray(payload["bodyAxes"]["e2"])
    e3 = np.asarray(payload["bodyAxes"]["e3"])
    assert np.allclose(np.sum(e1 * e2, axis=1), 0.0, atol=1e-12)
    assert np.allclose(np.cross(e1, e2) - e3, 0.0, atol=1e-12)
