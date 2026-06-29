from __future__ import annotations

import pytest
import sympy as sp

from engine.relativity import (
    FourVector,
    LorentzTransform,
    boost_along_axis,
    boost_from_rapidity,
    boost_from_velocity,
    rapidity_from_velocity,
    spatial_rotation,
    velocity_addition,
    velocity_from_rapidity,
)


def _is_zero(matrix: sp.Matrix) -> bool:
    return sp.simplify(sp.expand_trig(matrix)) == sp.zeros(*matrix.shape)


def test_general_boost_preserves_the_metric_symbolically() -> None:
    phi = sp.Symbol("phi", real=True)
    boost = boost_along_axis(phi, axis=1, dimension=4)
    eta = boost.metric.eta
    # Lambda^T eta Lambda == eta for an arbitrary rapidity.
    assert _is_zero(boost.matrix.T * eta * boost.matrix - eta)
    assert boost.preserves_metric()


def test_general_direction_velocity_boost_preserves_the_metric() -> None:
    vx, vy = sp.symbols("v_x v_y", real=True)
    boost = boost_from_velocity((vx, vy))
    assert boost.dimension == 3
    assert boost.preserves_metric()


def test_collinear_rapidities_add() -> None:
    phi1, phi2 = sp.symbols("phi_1 phi_2", real=True)
    composed = boost_along_axis(phi1) @ boost_along_axis(phi2)
    combined = boost_along_axis(phi1 + phi2)
    assert _is_zero(composed.matrix - combined.matrix)


def test_velocity_addition_formula_matches_boost_composition() -> None:
    v1, v2 = sp.symbols("v_1 v_2", real=True)
    composed = boost_from_velocity((v1,)) @ boost_from_velocity((v2,))
    # Recover the boost velocity from the composed transform: beta = -Lambda[0,1]/Lambda[0,0].
    recovered = sp.simplify(-composed.matrix[0, 1] / composed.matrix[0, 0])
    assert sp.simplify(recovered - velocity_addition(v1, v2)) == 0


def test_velocity_addition_is_subluminal_and_classical_limit() -> None:
    # Two half-light-speed velocities add to 0.8c, not 1.0c.
    assert velocity_addition(sp.Rational(1, 2), sp.Rational(1, 2)) == sp.Rational(4, 5)
    # Adding the speed of light yields the speed of light.
    assert velocity_addition(1, sp.Rational(1, 3)) == 1


def test_boost_preserves_a_four_vector_norm() -> None:
    phi = sp.Symbol("phi", real=True)
    boost = boost_along_axis(phi)
    t, x, y, z = sp.symbols("t x y z", real=True)
    vector = FourVector((t, x, y, z))
    boosted = boost.apply(vector)
    assert sp.simplify(boosted.norm_squared() - vector.norm_squared()) == 0


def test_boost_from_velocity_matches_rapidity_boost() -> None:
    beta = sp.Rational(3, 5)  # gamma = 5/4
    by_velocity = boost_from_velocity((beta, 0, 0))
    by_rapidity = boost_along_axis(rapidity_from_velocity(beta), axis=1)
    assert _is_zero(by_velocity.matrix - by_rapidity.matrix)


def test_boost_from_rapidity_vector_matches_axis_boost() -> None:
    phi = sp.Symbol("phi", positive=True)
    general = boost_from_rapidity((phi, 0, 0))
    axis = boost_along_axis(phi, axis=1)
    assert _is_zero(general.matrix - axis.matrix)


def test_spatial_rotation_preserves_metric_and_leaves_time_fixed() -> None:
    theta = sp.Symbol("theta", real=True)
    rotation = spatial_rotation(theta, axes=(1, 2))
    assert rotation.preserves_metric()
    # Time component is untouched.
    assert rotation.matrix[0, 0] == 1
    assert rotation.matrix[0, 1] == 0 and rotation.matrix[1, 0] == 0


def test_compose_with_inverse_is_identity() -> None:
    phi = sp.Symbol("phi", real=True)
    boost = boost_along_axis(phi)
    product = boost @ boost.inverse()
    assert _is_zero(product.matrix - sp.eye(4))


def test_composition_of_boost_and_rotation_is_a_lorentz_transform() -> None:
    boost = boost_along_axis(sp.Rational(1, 2))
    rotation = spatial_rotation(sp.pi / 3, axes=(1, 2))
    combined = rotation @ boost
    assert combined.preserves_metric()


def test_rapidity_velocity_round_trip() -> None:
    beta = sp.Rational(2, 5)
    assert sp.simplify(velocity_from_rapidity(rapidity_from_velocity(beta)) - beta) == 0


def test_apply_to_covariant_vector_preserves_contraction() -> None:
    phi = sp.Symbol("phi", real=True)
    boost = boost_along_axis(phi)
    t, x, y, z = sp.symbols("t x y z", real=True)
    contravariant = FourVector((t, x, y, z))
    covariant = contravariant.lower()
    # The scalar a_mu b^mu is invariant under the transform.
    before = covariant.contract(contravariant)
    after = boost.apply(covariant).contract(boost.apply(contravariant))
    assert sp.simplify(after - before) == 0


def test_invalid_constructions_are_rejected() -> None:
    with pytest.raises(ValueError):
        LorentzTransform(sp.Matrix([[1, 0, 0]]))  # not square
    with pytest.raises(ValueError):
        boost_along_axis(0.5, axis=0)  # time index is not a spatial axis
    with pytest.raises(ValueError):
        spatial_rotation(0.5, axes=(1, 1))  # rotation axes must differ
