from __future__ import annotations

import math

import pytest

from engine.dynamics import invariant_residuals


def test_invariant_residuals_exact_conservation() -> None:
    residual = invariant_residuals({"H": [2.5, 2.5, 2.5]})["H"]

    assert residual.name == "H"
    assert residual.reference == 2.5
    assert residual.max_abs == 0.0
    assert residual.rms == 0.0
    assert residual.max_relative == 0.0
    assert residual.scale == 2.5


def test_invariant_residuals_zero_reference_has_no_relative_error() -> None:
    residual = invariant_residuals({"ell": [0.0, 0.0, 0.0]})["ell"]

    assert residual.reference == 0.0
    assert residual.max_abs == 0.0
    assert residual.rms == 0.0
    assert residual.max_relative is None
    assert residual.scale == 1e-12


def test_invariant_residuals_closed_form_residual() -> None:
    delta = 1e-9
    residual = invariant_residuals({"H": [1.0, 1.0, 1.0 + delta]})["H"]

    assert residual.reference == 1.0
    assert residual.max_abs == pytest.approx(delta)
    assert residual.rms == pytest.approx(math.sqrt(delta**2 / 3.0))
    assert residual.max_relative == pytest.approx(delta / 1.0)
    assert residual.scale == pytest.approx(1.0 + delta)


def test_invariant_residuals_near_zero_guard() -> None:
    residual = invariant_residuals({"ell": [1e-14, 2e-14, -1e-14]})["ell"]

    assert residual.max_relative is None
    assert math.isfinite(residual.max_abs)
    assert residual.max_abs >= 0.0
    assert math.isfinite(residual.rms)
    assert residual.rms >= 0.0


def test_invariant_residuals_are_deterministic() -> None:
    series = {"H": [1.0, 1.000000001, 0.999999999]}

    assert invariant_residuals(series) == invariant_residuals(series)


def test_invariant_residuals_validate_sample_count() -> None:
    with pytest.raises(ValueError, match="at least two samples"):
        invariant_residuals({"H": []})

    with pytest.raises(ValueError, match="at least two samples"):
        invariant_residuals({"H": [1.0]})


def test_invariant_residuals_validate_reference_kind() -> None:
    with pytest.raises(ValueError, match="reference must be 'initial'"):
        invariant_residuals({"H": [1.0, 1.0]}, reference="mean")
