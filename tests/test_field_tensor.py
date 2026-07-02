from __future__ import annotations

import pytest
import sympy as sp

from engine.electrodynamics import (
    FaradayTensor,
    electromagnetic_invariants,
    faraday_tensor,
)


def test_faraday_tensor_is_antisymmetric_by_construction() -> None:
    ex, ey, ez, bx, by, bz = sp.symbols("E_x E_y E_z B_x B_y B_z", real=True)
    tensor = faraday_tensor((ex, ey, ez), (bx, by, bz))
    matrix = tensor.covariant_matrix()

    assert matrix.shape == (4, 4)
    assert sp.simplify(matrix + matrix.T) == sp.zeros(4, 4)
    assert matrix[0, 1] == -ex
    assert matrix[1, 0] == ex
    assert matrix[1, 2] == -bz
    assert matrix[2, 1] == bz


def test_raising_both_indices_uses_mostly_plus_minkowski_metric() -> None:
    ex, ey, ez, bx, by, bz = sp.symbols("E_x E_y E_z B_x B_y B_z", real=True)
    tensor = FaradayTensor((ex, ey, ez), (bx, by, bz))
    raised = tensor.contravariant_matrix()

    assert raised[0, 1] == ex
    assert raised[1, 0] == -ex
    assert raised[1, 2] == -bz
    assert raised[2, 1] == bz


def test_field_invariants_match_electric_and_magnetic_forms() -> None:
    ex, ey, ez, bx, by, bz = sp.symbols("E_x E_y E_z B_x B_y B_z", real=True)
    tensor = faraday_tensor((ex, ey, ez), (bx, by, bz))

    expected_scalar = 2 * (bx**2 + by**2 + bz**2 - ex**2 - ey**2 - ez**2)
    expected_dot = ex * bx + ey * by + ez * bz

    assert sp.simplify(tensor.scalar_invariant() - expected_scalar) == 0
    assert sp.simplify(tensor.electric_magnetic_invariant() - expected_dot) == 0
    assert tensor.invariant_pair() == (tensor.scalar_invariant(), expected_dot)


def test_invariant_helper_matches_tensor_methods() -> None:
    electric = (1, 2, 3)
    magnetic = (5, 7, 11)
    tensor = faraday_tensor(electric, magnetic)

    assert electromagnetic_invariants(electric, magnetic) == tensor.invariant_pair()
    assert tensor.scalar_invariant() == 2 * (
        5**2 + 7**2 + 11**2 - 1**2 - 2**2 - 3**2
    )
    assert tensor.electric_magnetic_invariant() == 1 * 5 + 2 * 7 + 3 * 11


def test_field_components_must_be_spatial_triplets() -> None:
    with pytest.raises(ValueError, match="electric"):
        faraday_tensor((1, 2), (0, 0, 1))
    with pytest.raises(ValueError, match="magnetic"):
        faraday_tensor((1, 2, 3), (0, 1))
