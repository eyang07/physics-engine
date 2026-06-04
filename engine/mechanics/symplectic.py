from __future__ import annotations

from typing import Sequence

import sympy as sp


def canonical_symplectic_matrix(dimension: int) -> sp.Matrix:
    """Return J for state ordering (q_0, ..., q_n, p_0, ..., p_n).

    Hamiltonian vector fields are represented as X_H = J grad H.
    """

    if dimension <= 0:
        raise ValueError("dimension must be positive")

    zero = sp.zeros(dimension)
    identity = sp.eye(dimension)
    return sp.Matrix.vstack(
        sp.Matrix.hstack(zero, identity),
        sp.Matrix.hstack(-identity, zero),
    )


def canonical_symplectic_form_matrix(dimension: int) -> sp.Matrix:
    """Return the matrix of omega = sum_i dq_i wedge dp_i.

    With the state ordering (q, p), this matrix is -J when X_H = J grad H.
    """

    return -canonical_symplectic_matrix(dimension)


def hamiltonian_vector_field(
    hamiltonian: sp.Expr,
    coordinates: Sequence[sp.Symbol],
    momenta: Sequence[sp.Symbol],
) -> sp.Matrix:
    """Return X_H = J grad H in canonical coordinates."""

    if len(coordinates) != len(momenta):
        raise ValueError("coordinates and momenta must have the same length")

    state = tuple(coordinates) + tuple(momenta)
    gradient = sp.Matrix([sp.diff(hamiltonian, symbol) for symbol in state])
    vector_field = canonical_symplectic_matrix(len(coordinates)) * gradient
    return sp.simplify(vector_field)


def phase_space_divergence(
    vector_field: Sequence[sp.Expr] | sp.Matrix,
    coordinates: Sequence[sp.Symbol],
    momenta: Sequence[sp.Symbol],
) -> sp.Expr:
    """Return div X in canonical phase-space coordinates."""

    state = tuple(coordinates) + tuple(momenta)
    vector = tuple(vector_field)
    if len(vector) != len(state):
        raise ValueError("vector field dimension must match phase-space dimension")

    return sp.simplify(
        sum(sp.diff(component, symbol) for component, symbol in zip(vector, state, strict=True))
    )


def liouville_divergence(
    hamiltonian: sp.Expr,
    coordinates: Sequence[sp.Symbol],
    momenta: Sequence[sp.Symbol],
) -> sp.Expr:
    """Return div X_H. Liouville's theorem gives zero in canonical coordinates."""

    return phase_space_divergence(
        hamiltonian_vector_field(hamiltonian, coordinates, momenta),
        coordinates,
        momenta,
    )


def satisfies_liouville_theorem(
    hamiltonian: sp.Expr,
    coordinates: Sequence[sp.Symbol],
    momenta: Sequence[sp.Symbol],
) -> bool:
    return liouville_divergence(hamiltonian, coordinates, momenta) == 0


def is_canonical_transformation(
    new_coordinates_and_momenta: Sequence[sp.Expr],
    old_coordinates: Sequence[sp.Symbol],
    old_momenta: Sequence[sp.Symbol],
) -> bool:
    """Return whether a phase-space map preserves the canonical symplectic form.

    The map is given by z_new = Phi(z_old). It is canonical when
    D Phi J_old D Phi^T = J_new.
    """

    old_state = tuple(old_coordinates) + tuple(old_momenta)
    new_state = tuple(new_coordinates_and_momenta)
    if len(new_state) != len(old_state):
        raise ValueError("phase-space map dimension must match old phase-space dimension")
    if len(old_coordinates) != len(old_momenta):
        raise ValueError("old coordinates and momenta must have the same length")

    jacobian = sp.Matrix(new_state).jacobian(old_state)
    j = canonical_symplectic_matrix(len(old_coordinates))
    return sp.simplify(jacobian * j * jacobian.T - j) == sp.zeros(len(old_state))

