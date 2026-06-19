from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import math
from typing import Sequence

import numpy as np
import sympy as sp


TorqueInput = Sequence[float] | Callable[[float, np.ndarray], Sequence[float]]


@dataclass(frozen=True)
class InertiaTensor:
    """Symmetric positive-definite rigid-body inertia tensor."""

    matrix: np.ndarray

    def __post_init__(self) -> None:
        matrix = np.asarray(self.matrix, dtype=float)
        if matrix.shape != (3, 3):
            raise ValueError("inertia tensor matrix must have shape (3, 3)")
        if not np.all(np.isfinite(matrix)):
            raise ValueError("inertia tensor matrix must contain finite values")
        if not np.allclose(matrix, matrix.T, atol=1e-12, rtol=1e-12):
            raise ValueError("inertia tensor matrix must be symmetric")
        eigenvalues = np.linalg.eigvalsh(matrix)
        if np.any(eigenvalues <= 0.0):
            raise ValueError("inertia tensor matrix must be positive definite")
        stored = matrix.copy()
        stored.setflags(write=False)
        object.__setattr__(self, "matrix", stored)

    @classmethod
    def diagonal(cls, moments: Sequence[float]) -> "InertiaTensor":
        values = np.asarray(moments, dtype=float)
        if values.shape != (3,):
            raise ValueError("moments must have shape (3,)")
        return cls(np.diag(values))

    @classmethod
    def rod(
        cls,
        *,
        mass: float,
        length: float,
        radius: float,
        axis: str = "x",
    ) -> "InertiaTensor":
        """Solid cylindrical rod about its center of mass."""

        _require_positive(mass, "mass")
        _require_positive(length, "length")
        _require_positive(radius, "radius")
        axial = 0.5 * mass * radius**2
        transverse = mass * (3.0 * radius**2 + length**2) / 12.0
        return cls.diagonal(_axis_moments(axis, axial, transverse, transverse))

    @classmethod
    def disk(cls, *, mass: float, radius: float, axis: str = "z") -> "InertiaTensor":
        """Thin solid disk about its center of mass."""

        _require_positive(mass, "mass")
        _require_positive(radius, "radius")
        axial = 0.5 * mass * radius**2
        in_plane = 0.25 * mass * radius**2
        return cls.diagonal(_axis_moments(axis, axial, in_plane, in_plane))

    @classmethod
    def sphere(cls, *, mass: float, radius: float) -> "InertiaTensor":
        _require_positive(mass, "mass")
        _require_positive(radius, "radius")
        moment = 0.4 * mass * radius**2
        return cls.diagonal((moment, moment, moment))

    @classmethod
    def box(
        cls,
        *,
        mass: float,
        width: float,
        depth: float,
        height: float,
    ) -> "InertiaTensor":
        _require_positive(mass, "mass")
        _require_positive(width, "width")
        _require_positive(depth, "depth")
        _require_positive(height, "height")
        return cls.diagonal(
            (
                mass * (depth**2 + height**2) / 12.0,
                mass * (width**2 + height**2) / 12.0,
                mass * (width**2 + depth**2) / 12.0,
            )
        )

    def principal_decomposition(self) -> tuple[np.ndarray, np.ndarray]:
        """Return principal moments and principal axes.

        The axes are the columns of the returned matrix.
        """

        moments, axes = np.linalg.eigh(self.matrix)
        return moments.astype(float), axes.astype(float)

    @property
    def inverse(self) -> np.ndarray:
        return np.linalg.inv(self.matrix)


def body_angular_momentum(
    inertia: InertiaTensor,
    angular_velocity: Sequence[float],
) -> np.ndarray:
    """Return body-frame angular momentum ``L = I omega``."""

    return inertia.matrix @ _vector3(angular_velocity, "angular_velocity")


def rotational_kinetic_energy(
    inertia: InertiaTensor,
    angular_velocity: Sequence[float],
) -> float:
    """Return rotational kinetic energy in the body frame."""

    omega = _vector3(angular_velocity, "angular_velocity")
    return float(0.5 * omega @ inertia.matrix @ omega)


def angular_momentum_magnitude(
    inertia: InertiaTensor,
    angular_velocity: Sequence[float],
) -> float:
    return float(np.linalg.norm(body_angular_momentum(inertia, angular_velocity)))


def euler_equations_rhs(
    inertia: InertiaTensor,
    torque: TorqueInput | None = None,
) -> Callable[[float, Sequence[float]], np.ndarray]:
    """Return ``d omega / dt`` for Euler's rigid-body equations.

    The returned function has the same ``(t, state)`` signature as the existing
    numerical integrators. Any conservation observed from an integration is
    measured numerical evidence, not a certificate.
    """

    torque_function = _torque_function(torque)
    inverse = inertia.inverse
    matrix = inertia.matrix

    def rhs(t: float, angular_velocity: Sequence[float]) -> np.ndarray:
        omega = _vector3(angular_velocity, "angular_velocity")
        applied_torque = torque_function(float(t), omega)
        return inverse @ (applied_torque - np.cross(omega, matrix @ omega))

    return rhs


def normalize_quaternion(quaternion: Sequence[float]) -> np.ndarray:
    """Return a unit quaternion in ``(w, x, y, z)`` order."""

    q = np.asarray(quaternion, dtype=float)
    if q.shape != (4,):
        raise ValueError("quaternion must have shape (4,)")
    norm = float(np.linalg.norm(q))
    if not np.isfinite(norm) or norm <= 0.0:
        raise ValueError("quaternion norm must be positive and finite")
    return q / norm


def quaternion_to_rotation_matrix(quaternion: Sequence[float]) -> np.ndarray:
    """Convert a ``(w, x, y, z)`` unit quaternion to an SO(3) matrix."""

    w, x, y, z = normalize_quaternion(quaternion)
    return np.array(
        [
            [1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
            [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
            [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)],
        ],
        dtype=float,
    )


def rotation_matrix_to_quaternion(rotation: Sequence[Sequence[float]]) -> np.ndarray:
    """Convert an SO(3) rotation matrix to a unit quaternion ``(w, x, y, z)``."""

    matrix = _rotation_matrix(rotation)
    trace = float(np.trace(matrix))
    if trace > 0.0:
        scale = 2.0 * math.sqrt(trace + 1.0)
        quaternion = np.array(
            [
                0.25 * scale,
                (matrix[2, 1] - matrix[1, 2]) / scale,
                (matrix[0, 2] - matrix[2, 0]) / scale,
                (matrix[1, 0] - matrix[0, 1]) / scale,
            ],
            dtype=float,
        )
    else:
        index = int(np.argmax(np.diag(matrix)))
        if index == 0:
            scale = 2.0 * math.sqrt(1.0 + matrix[0, 0] - matrix[1, 1] - matrix[2, 2])
            quaternion = np.array(
                [
                    (matrix[2, 1] - matrix[1, 2]) / scale,
                    0.25 * scale,
                    (matrix[0, 1] + matrix[1, 0]) / scale,
                    (matrix[0, 2] + matrix[2, 0]) / scale,
                ],
                dtype=float,
            )
        elif index == 1:
            scale = 2.0 * math.sqrt(1.0 + matrix[1, 1] - matrix[0, 0] - matrix[2, 2])
            quaternion = np.array(
                [
                    (matrix[0, 2] - matrix[2, 0]) / scale,
                    (matrix[0, 1] + matrix[1, 0]) / scale,
                    0.25 * scale,
                    (matrix[1, 2] + matrix[2, 1]) / scale,
                ],
                dtype=float,
            )
        else:
            scale = 2.0 * math.sqrt(1.0 + matrix[2, 2] - matrix[0, 0] - matrix[1, 1])
            quaternion = np.array(
                [
                    (matrix[1, 0] - matrix[0, 1]) / scale,
                    (matrix[0, 2] + matrix[2, 0]) / scale,
                    (matrix[1, 2] + matrix[2, 1]) / scale,
                    0.25 * scale,
                ],
                dtype=float,
            )
    if quaternion[0] < 0.0:
        quaternion = -quaternion
    return normalize_quaternion(quaternion)


def euler_angles_to_rotation_matrix(
    roll: float | sp.Expr,
    pitch: float | sp.Expr,
    yaw: float | sp.Expr,
) -> np.ndarray | sp.Matrix:
    """Return ``Rz(yaw) * Ry(pitch) * Rx(roll)``.

    Numeric inputs return a NumPy array; symbolic inputs return a SymPy matrix.
    """

    if any(isinstance(value, sp.Basic) for value in (roll, pitch, yaw)):
        cr, sr = sp.cos(roll), sp.sin(roll)
        cp, spitch = sp.cos(pitch), sp.sin(pitch)
        cy, sy = sp.cos(yaw), sp.sin(yaw)
        return sp.Matrix(
            [
                [cy * cp, cy * spitch * sr - sy * cr, cy * spitch * cr + sy * sr],
                [sy * cp, sy * spitch * sr + cy * cr, sy * spitch * cr - cy * sr],
                [-spitch, cp * sr, cp * cr],
            ]
        )
    cr, sr = math.cos(float(roll)), math.sin(float(roll))
    cp, spitch = math.cos(float(pitch)), math.sin(float(pitch))
    cy, sy = math.cos(float(yaw)), math.sin(float(yaw))
    return np.array(
        [
            [cy * cp, cy * spitch * sr - sy * cr, cy * spitch * cr + sy * sr],
            [sy * cp, sy * spitch * sr + cy * cr, sy * spitch * cr - cy * sr],
            [-spitch, cp * sr, cp * cr],
        ],
        dtype=float,
    )


def rotation_matrix_to_euler_angles(
    rotation: Sequence[Sequence[float]],
) -> tuple[float, float, float]:
    """Return ZYX Euler angles as ``(roll, pitch, yaw)``."""

    matrix = _rotation_matrix(rotation)
    pitch = math.asin(float(np.clip(-matrix[2, 0], -1.0, 1.0)))
    cp = math.cos(pitch)
    if abs(cp) < 1e-12:
        raise ValueError("Euler angle extraction is singular at this pitch")
    roll = math.atan2(matrix[2, 1], matrix[2, 2])
    yaw = math.atan2(matrix[1, 0], matrix[0, 0])
    return roll, pitch, yaw


def skew_symmetric(vector: Sequence[float]) -> np.ndarray:
    x, y, z = _vector3(vector, "vector")
    return np.array(
        [
            [0.0, -z, y],
            [z, 0.0, -x],
            [-y, x, 0.0],
        ],
        dtype=float,
    )


def vee_skew(matrix: Sequence[Sequence[float]]) -> np.ndarray:
    array = np.asarray(matrix, dtype=float)
    if array.shape != (3, 3):
        raise ValueError("skew matrix must have shape (3, 3)")
    if not np.allclose(array + array.T, np.zeros((3, 3)), atol=1e-9, rtol=1e-9):
        raise ValueError("matrix is not skew-symmetric")
    return np.array([array[2, 1], array[0, 2], array[1, 0]], dtype=float)


def body_angular_velocity_from_rotation(
    rotation: Sequence[Sequence[float]],
    rotation_derivative: Sequence[Sequence[float]],
) -> np.ndarray:
    """Return body-frame angular velocity from ``R`` and ``Rdot``."""

    matrix = _rotation_matrix(rotation)
    derivative = _matrix3(rotation_derivative, "rotation_derivative")
    return vee_skew(matrix.T @ derivative)


def space_angular_velocity_from_rotation(
    rotation: Sequence[Sequence[float]],
    rotation_derivative: Sequence[Sequence[float]],
) -> np.ndarray:
    """Return space-frame angular velocity from ``R`` and ``Rdot``."""

    matrix = _rotation_matrix(rotation)
    derivative = _matrix3(rotation_derivative, "rotation_derivative")
    return vee_skew(derivative @ matrix.T)


def body_to_space_angular_velocity(
    rotation: Sequence[Sequence[float]],
    body_angular_velocity: Sequence[float],
) -> np.ndarray:
    return _rotation_matrix(rotation) @ _vector3(body_angular_velocity, "body_angular_velocity")


def space_to_body_angular_velocity(
    rotation: Sequence[Sequence[float]],
    space_angular_velocity: Sequence[float],
) -> np.ndarray:
    return _rotation_matrix(rotation).T @ _vector3(space_angular_velocity, "space_angular_velocity")


def _matrix3(matrix: Sequence[Sequence[float]], label: str) -> np.ndarray:
    array = np.asarray(matrix, dtype=float)
    if array.shape != (3, 3):
        raise ValueError(f"{label} must have shape (3, 3)")
    if not np.all(np.isfinite(array)):
        raise ValueError(f"{label} must contain finite values")
    return array


def _rotation_matrix(matrix: Sequence[Sequence[float]]) -> np.ndarray:
    array = _matrix3(matrix, "rotation")
    if not np.allclose(array.T @ array, np.eye(3), atol=1e-9, rtol=1e-9):
        raise ValueError("rotation matrix must be orthonormal")
    determinant = float(np.linalg.det(array))
    if not np.isclose(determinant, 1.0, atol=1e-9, rtol=1e-9):
        raise ValueError("rotation matrix determinant must be +1")
    return array


def _vector3(vector: Sequence[float], label: str) -> np.ndarray:
    array = np.asarray(vector, dtype=float)
    if array.shape != (3,):
        raise ValueError(f"{label} must have shape (3,)")
    if not np.all(np.isfinite(array)):
        raise ValueError(f"{label} must contain finite values")
    return array


def _require_positive(value: float, label: str) -> None:
    if not np.isfinite(value) or value <= 0.0:
        raise ValueError(f"{label} must be positive and finite")


def _torque_function(
    torque: TorqueInput | None,
) -> Callable[[float, np.ndarray], np.ndarray]:
    if torque is None:

        def zero_torque(_t: float, _angular_velocity: np.ndarray) -> np.ndarray:
            return np.zeros(3, dtype=float)

        return zero_torque
    if callable(torque):

        def evaluated_torque(t: float, angular_velocity: np.ndarray) -> np.ndarray:
            return _vector3(torque(t, angular_velocity.copy()), "torque")

        return evaluated_torque
    constant = _vector3(torque, "torque")

    def constant_torque(_t: float, _angular_velocity: np.ndarray) -> np.ndarray:
        return constant

    return constant_torque


def _axis_moments(
    axis: str,
    axial: float,
    first_transverse: float,
    second_transverse: float,
) -> tuple[float, float, float]:
    if axis == "x":
        return axial, first_transverse, second_transverse
    if axis == "y":
        return first_transverse, axial, second_transverse
    if axis == "z":
        return first_transverse, second_transverse, axial
    raise ValueError("axis must be one of 'x', 'y', or 'z'")
