from __future__ import annotations

import pytest
import sympy as sp

from engine.relativity import CONTRAVARIANT, COVARIANT, FourVector, MinkowskiMetric


def test_norm_squared_uses_the_global_signature() -> None:
    # eta_{mu nu} v^mu v^nu = -t^2 + x^2 + y^2 + z^2.
    vector = FourVector((2, 1, 0, 0))
    assert vector.norm_squared() == -3

    spacelike = FourVector((1, 2, 0, 0))
    assert spacelike.norm_squared() == 3

    # Matches the metric's own inner product of the components with itself.
    metric = MinkowskiMetric()
    assert vector.norm_squared() == metric.norm_squared((2, 1, 0, 0))


def test_classification_matches_the_sign_of_norm_squared() -> None:
    timelike = FourVector((2, 1, 0, 0))
    null = FourVector((1, 1, 0, 0))
    spacelike = FourVector((1, 2, 0, 0))

    assert timelike.norm_squared() < 0 and timelike.classify() == "timelike"
    assert null.norm_squared() == 0 and null.classify() == "null"
    assert spacelike.norm_squared() > 0 and spacelike.classify() == "spacelike"

    assert timelike.is_timelike
    assert null.is_null
    assert spacelike.is_spacelike


def test_lowering_then_contracting_reproduces_the_norm() -> None:
    vector = FourVector((2, 1, 3, 5))
    lowered = vector.lower()
    assert lowered.variance == COVARIANT
    # v_mu v^mu == eta_{mu nu} v^mu v^nu.
    assert lowered.contract(vector) == vector.norm_squared()


def test_covariant_norm_matches_contravariant_norm() -> None:
    vector = FourVector((2, 1, 3, 5))
    lowered = vector.lower()
    # Raising/lowering must not change the invariant norm².
    assert lowered.norm_squared() == vector.norm_squared()
    # Round-trip back to the original contravariant vector.
    assert lowered.raise_index().components == vector.components


def test_symbolic_and_numeric_paths_agree() -> None:
    t, x, y, z = sp.symbols("t x y z", real=True)
    symbolic = FourVector((t, x, y, z))
    symbolic_norm = symbolic.norm_squared()

    substitution = {t: 2, x: 1, y: 3, z: 5}
    numeric = FourVector((2, 1, 3, 5))

    assert symbolic_norm == -(t**2) + x**2 + y**2 + z**2
    assert symbolic_norm.subs(substitution) == numeric.norm_squared()


def test_contract_requires_opposite_variance() -> None:
    a = FourVector((1, 2, 3, 4), variance=CONTRAVARIANT)
    b = FourVector((4, 3, 2, 1), variance=CONTRAVARIANT)
    with pytest.raises(ValueError):
        a.contract(b)
    # A contravariant and a covariant contract fine.
    assert a.contract(b.lower()) == a.lower().contract(b)


def test_lower_and_raise_reject_redundant_calls() -> None:
    contravariant = FourVector((1, 2, 3, 4), variance=CONTRAVARIANT)
    with pytest.raises(ValueError):
        contravariant.raise_index()
    covariant = FourVector((1, 2, 3, 4), variance=COVARIANT)
    with pytest.raises(ValueError):
        covariant.lower()


def test_invalid_construction_is_rejected() -> None:
    with pytest.raises(ValueError):
        FourVector((1,))
    with pytest.raises(ValueError):
        FourVector((1, 2), variance="mixed")


def test_classify_requires_numeric_components() -> None:
    a = sp.Symbol("a", real=True)
    with pytest.raises(ValueError):
        FourVector((a, 0, 0, 0)).classify()


def test_works_in_lower_dimensions() -> None:
    # 1+1 dimensions: eta = diag(-1, 1).
    vector = FourVector((3, 0))
    assert vector.norm_squared() == -9
    assert vector.classify() == "timelike"
