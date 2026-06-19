from __future__ import annotations

import numpy as np
import pytest

from engine.mechanics import InertiaTensor


def test_inertia_tensor_validates_shape_symmetry_and_positive_definiteness() -> None:
    with pytest.raises(ValueError, match="shape"):
        InertiaTensor(np.eye(2))
    with pytest.raises(ValueError, match="symmetric"):
        InertiaTensor(np.array([[1.0, 0.2, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]))
    with pytest.raises(ValueError, match="positive definite"):
        InertiaTensor(np.diag([1.0, 0.0, 2.0]))


def test_inertia_tensor_stores_immutable_copy() -> None:
    matrix = np.diag([1.0, 2.0, 3.0])
    tensor = InertiaTensor(matrix)
    matrix[0, 0] = 99.0

    assert np.allclose(tensor.matrix, np.diag([1.0, 2.0, 3.0]))
    with pytest.raises(ValueError, match="read-only"):
        tensor.matrix[0, 0] = 4.0


def test_standard_shape_constructors_match_known_moments() -> None:
    rod = InertiaTensor.rod(mass=3.0, length=2.0, radius=0.2, axis="x")
    assert np.allclose(
        rod.matrix,
        np.diag(
            [
                0.5 * 3.0 * 0.2**2,
                3.0 * (3.0 * 0.2**2 + 2.0**2) / 12.0,
                3.0 * (3.0 * 0.2**2 + 2.0**2) / 12.0,
            ]
        ),
    )

    disk = InertiaTensor.disk(mass=2.0, radius=1.5, axis="z")
    assert np.allclose(
        disk.matrix,
        np.diag([0.25 * 2.0 * 1.5**2, 0.25 * 2.0 * 1.5**2, 0.5 * 2.0 * 1.5**2]),
    )

    sphere = InertiaTensor.sphere(mass=5.0, radius=0.4)
    assert np.allclose(sphere.matrix, np.eye(3) * (0.4 * 5.0 * 0.4**2))

    box = InertiaTensor.box(mass=6.0, width=1.0, depth=2.0, height=3.0)
    assert np.allclose(
        box.matrix,
        np.diag(
            [
                6.0 * (2.0**2 + 3.0**2) / 12.0,
                6.0 * (1.0**2 + 3.0**2) / 12.0,
                6.0 * (1.0**2 + 2.0**2) / 12.0,
            ]
        ),
    )


def test_principal_decomposition_reconstructs_tensor_with_orthonormal_axes() -> None:
    rotation = np.array(
        [
            [0.0, -1.0, 0.0],
            [1.0, 0.0, 0.0],
            [0.0, 0.0, 1.0],
        ]
    )
    diagonal = np.diag([1.0, 2.0, 4.0])
    tensor = InertiaTensor(rotation @ diagonal @ rotation.T)

    moments, axes = tensor.principal_decomposition()

    assert np.allclose(moments, [1.0, 2.0, 4.0])
    assert np.allclose(axes.T @ axes, np.eye(3))
    assert np.allclose(axes @ np.diag(moments) @ axes.T, tensor.matrix)


def test_shape_constructors_reject_invalid_dimensions() -> None:
    with pytest.raises(ValueError, match="mass"):
        InertiaTensor.sphere(mass=0.0, radius=1.0)
    with pytest.raises(ValueError, match="axis"):
        InertiaTensor.disk(mass=1.0, radius=1.0, axis="bad")
