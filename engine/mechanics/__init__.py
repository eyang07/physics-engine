"""Symbolic mechanics primitives."""

from engine.mechanics.coordinates import CoordinateChart, CotangentBundleChart, TangentBundleChart
from engine.mechanics.hamiltonian import HamiltonianSystem, legendre_transform
from engine.mechanics.lagrangian import LagrangianSystem
from engine.mechanics.poisson import is_conserved, poisson_bracket, time_evolution
from engine.mechanics.rigid_body import (
    InertiaTensor,
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
from engine.mechanics.small_oscillations import (
    NormalModeResult,
    mass_and_stiffness_matrices,
    normal_modes,
)
from engine.mechanics.symplectic import (
    canonical_symplectic_matrix,
    hamiltonian_vector_field,
    is_canonical_transformation,
    liouville_divergence,
)

__all__ = [
    "CoordinateChart",
    "CotangentBundleChart",
    "HamiltonianSystem",
    "InertiaTensor",
    "LagrangianSystem",
    "NormalModeResult",
    "TangentBundleChart",
    "body_angular_velocity_from_rotation",
    "body_to_space_angular_velocity",
    "canonical_symplectic_matrix",
    "euler_angles_to_rotation_matrix",
    "hamiltonian_vector_field",
    "is_canonical_transformation",
    "is_conserved",
    "legendre_transform",
    "liouville_divergence",
    "mass_and_stiffness_matrices",
    "normal_modes",
    "normalize_quaternion",
    "poisson_bracket",
    "quaternion_to_rotation_matrix",
    "rotation_matrix_to_euler_angles",
    "rotation_matrix_to_quaternion",
    "skew_symmetric",
    "space_angular_velocity_from_rotation",
    "space_to_body_angular_velocity",
    "time_evolution",
    "vee_skew",
]
