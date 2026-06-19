from __future__ import annotations

import numpy as np
import pytest
import sympy as sp

from engine.mechanics import (
    body_angular_velocity_from_rotation,
    body_to_space_angular_velocity,
    euler_angles_to_rotation_matrix,
    normalize_quaternion,
    quaternion_to_rotation_matrix,
    rotation_matrix_to_euler_angles,
    rotation_matrix_to_quaternion,
    skew_symmetric,
    space_angular_velocity_from_rotation,
    space_to_body_angular_velocity,
    vee_skew,
)


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
