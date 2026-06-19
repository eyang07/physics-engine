from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

import numpy as np
from scipy.linalg import eigh
import sympy as sp

from engine.mechanics.lagrangian import LagrangianSystem


@dataclass(frozen=True)
class NormalModeResult:
    """Small-oscillation normal modes around one equilibrium."""

    coordinates: tuple[str, ...]
    mass_matrix: np.ndarray
    stiffness_matrix: np.ndarray
    frequencies: np.ndarray
    mode_shapes: np.ndarray

    def __post_init__(self) -> None:
        dimension = len(self.coordinates)
        if dimension == 0:
            raise ValueError("normal modes require at least one coordinate")
        for label, matrix in (
            ("mass_matrix", self.mass_matrix),
            ("stiffness_matrix", self.stiffness_matrix),
            ("mode_shapes", self.mode_shapes),
        ):
            if matrix.shape != (dimension, dimension):
                raise ValueError(f"{label} must have shape {(dimension, dimension)}")
            if not np.all(np.isfinite(matrix)):
                raise ValueError(f"{label} must contain finite values")
        if self.frequencies.shape != (dimension,):
            raise ValueError(f"frequencies must have shape {(dimension,)}")
        if not np.all(np.isfinite(self.frequencies)):
            raise ValueError("frequencies must contain finite values")
        if np.any(self.frequencies < 0.0):
            raise ValueError("frequencies must be nonnegative")

    def to_dict(self) -> dict[str, object]:
        return {
            "coordinates": list(self.coordinates),
            "massMatrix": self.mass_matrix.astype(float).tolist(),
            "stiffnessMatrix": self.stiffness_matrix.astype(float).tolist(),
            "frequencies": self.frequencies.astype(float).tolist(),
            "modeShapes": self.mode_shapes.astype(float).tolist(),
        }


def mass_and_stiffness_matrices(
    system: LagrangianSystem,
    equilibrium: Mapping[sp.Symbol, sp.Expr | float],
    *,
    substitutions: Mapping[sp.Symbol, sp.Expr | float] | None = None,
) -> tuple[sp.Matrix, sp.Matrix]:
    """Return symbolic M and K for small oscillations around ``equilibrium``.

    The mass matrix is ``d²L/dqdot²`` and the stiffness matrix is
    ``-d²L(q, 0)/dq²``, both evaluated at the equilibrium and optional
    parameter substitutions.
    """

    missing = [coordinate for coordinate in system.q if coordinate not in equilibrium]
    if missing:
        names = ", ".join(symbol.name for symbol in missing)
        raise ValueError(f"equilibrium is missing coordinate(s): {names}")

    substitutions = substitutions or {}
    zero_velocity = {velocity: 0 for velocity in system.qdot}
    replacement = {**zero_velocity, **equilibrium, **substitutions}

    mass = sp.hessian(system.lagrangian, system.qdot)
    potential_part = system.lagrangian.subs(zero_velocity)
    stiffness = -sp.hessian(potential_part, system.q)
    return (
        sp.simplify(mass.subs(replacement)),
        sp.simplify(stiffness.subs(replacement)),
    )


def normal_modes(
    system: LagrangianSystem,
    equilibrium: Mapping[sp.Symbol, sp.Expr | float],
    *,
    substitutions: Mapping[sp.Symbol, sp.Expr | float] | None = None,
    tolerance: float = 1e-12,
) -> NormalModeResult:
    """Solve the small-oscillation generalized eigenproblem ``K u = w² M u``."""

    if tolerance <= 0.0:
        raise ValueError("tolerance must be positive")
    mass, stiffness = mass_and_stiffness_matrices(
        system,
        equilibrium,
        substitutions=substitutions,
    )
    mass_array = _numeric_matrix(mass, "mass matrix")
    stiffness_array = _numeric_matrix(stiffness, "stiffness matrix")
    eigenvalues, eigenvectors = eigh(stiffness_array, mass_array)
    if np.any(eigenvalues < -tolerance):
        raise ValueError("small-oscillation stiffness has negative eigenvalues")
    frequencies = np.sqrt(np.maximum(eigenvalues, 0.0))
    return NormalModeResult(
        coordinates=tuple(symbol.name for symbol in system.q),
        mass_matrix=mass_array,
        stiffness_matrix=stiffness_array,
        frequencies=frequencies,
        mode_shapes=eigenvectors,
    )


def _numeric_matrix(matrix: sp.Matrix, label: str) -> np.ndarray:
    array = np.asarray(matrix.tolist(), dtype=float)
    if array.ndim != 2 or array.shape[0] != array.shape[1]:
        raise ValueError(f"{label} must be square")
    if not np.all(np.isfinite(array)):
        raise ValueError(f"{label} must contain finite numeric values")
    if not np.allclose(array, array.T, atol=1e-10, rtol=1e-10):
        raise ValueError(f"{label} must be symmetric")
    return array
