from __future__ import annotations

import pytest
import sympy as sp

from engine.relativity import (
    SIGNATURE,
    SIGNATURE_NAME,
    MinkowskiMetric,
    minkowski_eta,
)


def test_eta_has_mostly_plus_signature() -> None:
    eta = minkowski_eta(4)

    assert SIGNATURE_NAME == "(-,+,+,+)"
    assert SIGNATURE[0] == -1
    assert eta == sp.diag(-1, 1, 1, 1)
    assert eta[0, 0] == -1
    for spatial in range(1, 4):
        assert eta[spatial, spatial] == 1
    # No off-diagonal mixing.
    assert eta == sp.diag(*[eta[i, i] for i in range(4)])


def test_eta_supports_lower_dimensions() -> None:
    assert minkowski_eta(2) == sp.diag(-1, 1)
    assert minkowski_eta(3) == sp.diag(-1, 1, 1)
    with pytest.raises(ValueError):
        minkowski_eta(1)


def test_inverse_eta_equals_eta() -> None:
    metric = MinkowskiMetric()
    # Mostly-plus eta is its own inverse; this also exercises the reuse of
    # MetricGeometry.inverse_metric().
    assert metric.inverse_eta() == metric.eta


def test_backing_geometry_is_flat() -> None:
    # Reusing MetricGeometry: a constant metric has a vanishing Levi-Civita
    # connection, confirming Minkowski space is flat.
    metric = MinkowskiMetric()
    gamma = metric.geometry.christoffel_symbols()
    for k in range(4):
        for i in range(4):
            for j in range(4):
                assert gamma[k, i, j] == 0


def test_raise_then_lower_is_identity() -> None:
    metric = MinkowskiMetric()
    a, b, c, d = sp.symbols("a b c d", real=True)
    vector = sp.Matrix([a, b, c, d])

    lowered = metric.lower(vector)
    recovered = metric.raise_index(lowered)
    assert sp.simplify(recovered - vector) == sp.zeros(4, 1)

    # And the other order: raise then lower.
    raised = metric.raise_index(vector)
    relowered = metric.lower(raised)
    assert sp.simplify(relowered - vector) == sp.zeros(4, 1)


def test_lower_flips_only_the_time_component() -> None:
    metric = MinkowskiMetric()
    lowered = metric.lower([2, 3, 5, 7])
    assert lowered == sp.Matrix([-2, 3, 5, 7])


def test_interval_of_known_separations_matches_by_hand() -> None:
    metric = MinkowskiMetric()

    # Timelike: dt = 2, dx = 1 -> s^2 = -4 + 1 = -3.
    timelike = [2, 1, 0, 0]
    assert metric.interval_squared(timelike) == -3
    assert metric.classify(timelike) == "timelike"

    # Spacelike: dt = 1, dx = 2 -> s^2 = -1 + 4 = 3.
    spacelike = [1, 2, 0, 0]
    assert metric.interval_squared(spacelike) == 3
    assert metric.classify(spacelike) == "spacelike"

    # Null: dt = 1, dx = 1 -> s^2 = -1 + 1 = 0.
    null = [1, 1, 0, 0]
    assert metric.interval_squared(null) == 0
    assert metric.classify(null) == "null"

    # A full 3-space separation: dt = 5, (dx, dy, dz) = (3, 0, 0) -> -16.
    full = [5, 3, 0, 0]
    assert metric.interval_squared(full) == -16
    assert metric.classify(full) == "timelike"


def test_inner_product_is_symmetric_and_matches_norm() -> None:
    metric = MinkowskiMetric()
    u = [1, 2, 3, 4]
    v = [4, 3, 2, 1]

    assert metric.inner_product(u, v) == metric.inner_product(v, u)
    # eta_{mu nu} u^mu v^nu = -1*4 + 2*3 + 3*2 + 4*1 = 12.
    assert metric.inner_product(u, v) == 12
    assert metric.norm_squared(u) == metric.inner_product(u, u)


def test_row_and_column_inputs_are_accepted() -> None:
    metric = MinkowskiMetric()
    row = sp.Matrix([[2, 1, 0, 0]])
    column = sp.Matrix([2, 1, 0, 0])
    assert metric.interval_squared(row) == metric.interval_squared(column) == -3


def test_wrong_length_vector_is_rejected() -> None:
    metric = MinkowskiMetric()
    with pytest.raises(ValueError):
        metric.norm_squared([1, 2, 3])


def test_dimension_must_be_at_least_two() -> None:
    with pytest.raises(ValueError):
        MinkowskiMetric(dimension=1)


def test_classify_requires_numeric_separation() -> None:
    metric = MinkowskiMetric()
    a = sp.Symbol("a", real=True)
    with pytest.raises(ValueError):
        metric.classify([a, 0, 0, 0])
