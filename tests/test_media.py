from __future__ import annotations

import numpy as np
import pytest
import sympy as sp

from engine.dynamics import (
    InverseMetricMedium,
    RefractiveIndexMedium,
    ScalarSpeedMedium,
    gaussian_lens_speed,
    integrate_ray_bundle,
)
from systems.variable_speed_wavefront import build_system, wave_speed


def test_scalar_speed_medium_symbol_and_system() -> None:
    x, y = sp.symbols("x y", real=True)
    xi, eta = sp.symbols("xi eta", real=True)
    c0 = sp.Symbol("c0", positive=True)
    speed = c0 * (1 + x**2 + y**2)

    medium = ScalarSpeedMedium(coordinates=(x, y), speed=speed)
    system = medium.to_system(momenta=(xi, eta))

    assert medium.parameters == (c0,)
    assert system.coordinates == (x, y)
    assert system.momenta == (xi, eta)
    assert system.parameters == (c0,)
    assert sp.simplify(system.symbol - speed**2 * (xi**2 + eta**2) / 2) == 0
    assert sp.simplify(system.rhs()[0] - speed**2 * xi) == 0
    assert sp.simplify(system.rhs()[1] - speed**2 * eta) == 0


def test_scalar_speed_medium_default_momenta_and_parameter_override() -> None:
    x, y = sp.symbols("x y", real=True)
    a, b = sp.symbols("a b", positive=True)

    detected = ScalarSpeedMedium(coordinates=(x, y), speed=b + a * x)
    assert detected.parameters == (a, b)

    explicit = ScalarSpeedMedium(coordinates=(x, y), speed=b + a * x, parameters=(b, a))
    assert explicit.parameters == (b, a)

    system = detected.to_system()
    assert tuple(momentum.name for momentum in system.momenta) == ("xi_x", "xi_y")


def test_refractive_index_medium_matches_scalar_speed_medium() -> None:
    x, y = sp.symbols("x y", real=True)
    xi, eta = sp.symbols("xi eta", real=True)
    c0 = sp.Symbol("c0", positive=True)
    n = 1 + sp.exp(-(x**2 + y**2))

    refractive = RefractiveIndexMedium(coordinates=(x, y), index=n, reference_speed=c0)
    scalar = ScalarSpeedMedium(coordinates=(x, y), speed=c0 / n)

    assert sp.simplify(refractive.speed - c0 / n) == 0
    assert sp.simplify(refractive.symbol((xi, eta)) - scalar.symbol((xi, eta))) == 0
    assert refractive.parameters == (c0,)


def test_conformal_inverse_metric_reduces_to_scalar_speed() -> None:
    x, y = sp.symbols("x y", real=True)
    xi, eta = sp.symbols("xi eta", real=True)
    c0, alpha, sigma = sp.symbols("c0 alpha sigma", positive=True)

    speed = gaussian_lens_speed(
        (x, y), base_speed=c0, lens_strength=alpha, lens_width=sigma
    )
    conformal = InverseMetricMedium(
        coordinates=(x, y),
        inverse_metric=speed**2 * sp.eye(2),
    )
    scalar = ScalarSpeedMedium(coordinates=(x, y), speed=speed)

    assert sp.simplify(conformal.symbol((xi, eta)) - scalar.symbol((xi, eta))) == 0


def test_inverse_metric_from_metric_gives_cogeodesic_hamiltonian() -> None:
    r, theta = sp.symbols("r theta", positive=True)
    p_r, p_theta = sp.symbols("p_r p_theta", real=True)

    flat_polar = sp.diag(1, r**2)
    medium = InverseMetricMedium.from_metric((r, theta), flat_polar)

    assert sp.simplify(medium.inverse_metric * flat_polar) == sp.eye(2)
    expected = (p_r**2 + p_theta**2 / r**2) / 2
    assert sp.simplify(medium.symbol((p_r, p_theta)) - expected) == 0

    system = medium.to_system(momenta=(p_r, p_theta))
    # p_theta is cyclic for the flat polar metric, so its momentum is conserved.
    assert sp.simplify(system.rhs()[3]) == 0


def test_inverse_metric_medium_validation() -> None:
    x, y = sp.symbols("x y", real=True)

    with pytest.raises(ValueError, match="square"):
        InverseMetricMedium(coordinates=(x, y), inverse_metric=sp.eye(3))
    with pytest.raises(ValueError, match="symmetric"):
        InverseMetricMedium(
            coordinates=(x, y),
            inverse_metric=sp.Matrix([[1, x], [0, 1]]),
        )


def test_homogeneous_medium_rays_are_straight_lines() -> None:
    x, y = sp.symbols("x y", real=True)
    medium = ScalarSpeedMedium(coordinates=(x, y), speed=sp.Integer(2))
    system = medium.to_system()

    bundle = integrate_ray_bundle(
        system,
        [[0.0, 0.0, 0.5, 0.0], [0.0, 1.0, 0.0, 0.25]],
        t_span=(0.0, 1.0),
        dt=0.1,
        state_names=["x", "y", "xi_x", "xi_y"],
    )

    # q_dot = c**2 * xi with constant c=2, so positions are linear in time.
    expected_x = 4.0 * 0.5 * bundle.time
    assert np.allclose(bundle.rays[0, :, 0], expected_x, atol=1e-12)
    assert np.allclose(bundle.rays[0, :, 1], 0.0, atol=1e-12)
    assert np.allclose(bundle.rays[1, :, 1], 1.0 + bundle.time, atol=1e-12)
    assert bundle.max_hamiltonian_drift < 1e-12


def test_gaussian_lens_speed_center_shift_and_wavefront_delegation() -> None:
    x, y = sp.symbols("x y", real=True)
    c0, alpha, sigma = sp.symbols("c0 alpha sigma", positive=True)

    centered = gaussian_lens_speed(
        (x, y), base_speed=c0, lens_strength=alpha, lens_width=sigma
    )
    shifted = gaussian_lens_speed(
        (x, y),
        base_speed=c0,
        lens_strength=alpha,
        lens_width=sigma,
        center=(1, 0),
    )
    assert sp.simplify(shifted.subs(x, x + 1) - centered) == 0

    # The registered wavefront system is the centered Gaussian-lens medium.
    legacy = wave_speed(x, y, base_speed=c0, lens_strength=alpha, lens_width=sigma)
    assert sp.simplify(legacy - centered) == 0

    system = build_system(base_speed=c0, lens_strength=alpha, lens_width=sigma)
    xi, eta = system.momenta
    assert sp.simplify(system.symbol - centered**2 * (xi**2 + eta**2) / 2) == 0
