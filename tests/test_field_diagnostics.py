from __future__ import annotations

import numpy as np
import sympy as sp

from engine.fields import (
    VectorField,
    gauss_flux_check,
    measured_curl_grid,
    measured_divergence_grid,
    planar_stokes_check,
    sphere_surface_quadrature,
)


def test_measured_divergence_and_curl_grids_are_labeled_evidence() -> None:
    x, y, z = sp.symbols("x y z", real=True)
    field = VectorField((x, y, z), (x**2, y**2, z**2))
    axes = [np.linspace(-1.0, 1.0, 9)] * 3

    divergence = measured_divergence_grid(field, axes)
    curl = measured_curl_grid(field, axes)

    gx, gy, gz = np.meshgrid(*axes, indexing="ij")
    assert divergence.rigor == "measured"
    assert divergence.evaluation == "measured-finite-difference-grid"
    assert "proof" in divergence.note
    assert np.allclose(divergence.values, 2.0 * gx + 2.0 * gy + 2.0 * gz)

    assert curl.rigor == "measured"
    assert curl.operator == "curl"
    assert curl.values.shape == (9, 9, 9, 3)
    assert np.allclose(curl.values, 0.0)
    assert curl.to_dict()["rigor"] == "measured"


def test_gauss_flux_for_point_charge_matches_enclosed_charge_measured() -> None:
    x, y, z = sp.symbols("x y z", real=True)
    r3 = (x**2 + y**2 + z**2) ** sp.Rational(3, 2)
    field = VectorField(
        (x, y, z),
        (
            sp.Integer(3) * x / (8 * sp.pi * r3),
            sp.Integer(3) * y / (8 * sp.pi * r3),
            sp.Integer(3) * z / (8 * sp.pi * r3),
        ),
    )
    points, normals, weights = sphere_surface_quadrature(
        radius=1.7,
        theta_count=72,
        phi_count=144,
    )

    check = gauss_flux_check(
        field,
        points,
        normals,
        weights,
        enclosed_charge=3.0,
        epsilon0=2.0,
        tolerance=2e-4,
    )

    assert check.rigor == "measured"
    assert check.left.rigor == "measured"
    assert check.right.rigor == "measured"
    assert check.passed is True
    assert abs(check.left.value - 1.5) < 2e-4
    payload = check.to_dict()
    assert payload["law"] == "gauss"
    assert payload["passed"] is True
    assert "proof" in payload["note"]


def test_planar_stokes_circulation_matches_measured_curl_flux() -> None:
    x, y = sp.symbols("x y", real=True)
    field = VectorField((x, y), (-y / 2, x / 2))
    axes = [np.linspace(-1.5, 2.0, 41), np.linspace(-0.75, 1.25, 37)]

    curl = measured_curl_grid(field, axes)
    check = planar_stokes_check(field, axes, tolerance=1e-12)
    area = (axes[0][-1] - axes[0][0]) * (axes[1][-1] - axes[1][0])

    assert curl.rigor == "measured"
    assert curl.operator == "curl-z"
    assert np.allclose(curl.values, 1.0)
    assert check.rigor == "measured"
    assert check.left.quantity == "line-circulation"
    assert check.right.quantity == "curl-flux"
    assert check.passed is True
    assert abs(check.left.value - area) < 1e-12
    assert abs(check.right.value - area) < 1e-12
