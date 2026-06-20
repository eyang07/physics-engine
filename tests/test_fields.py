from __future__ import annotations

import numpy as np
import pytest
import sympy as sp

from engine.fields import (
    ScalarField,
    VectorField,
    curl,
    divergence,
    gradient,
    laplacian,
)


def _xyz() -> tuple[sp.Symbol, sp.Symbol, sp.Symbol]:
    return sp.symbols("x y z", real=True)


def test_gradient_and_laplacian_match_closed_forms() -> None:
    x, y, z = _xyz()
    field = ScalarField((x, y, z), x**2 + y**2 + z**2)

    grad = field.gradient()
    assert grad.components == (2 * x, 2 * y, 2 * z)
    assert sp.simplify(field.laplacian().expression - 6) == 0


def test_curl_of_gradient_is_zero() -> None:
    x, y, z = _xyz()
    field = ScalarField((x, y, z), sp.sin(x * y) + z**3 * x - sp.cos(y * z))

    curled = curl(gradient(field))
    assert all(sp.simplify(component) == 0 for component in curled.components)


def test_divergence_of_curl_is_zero() -> None:
    x, y, z = _xyz()
    vector = VectorField(
        (x, y, z),
        (x**2 * y, sp.sin(z) * x, y * z**2 + sp.exp(x)),
    )

    result = divergence(curl(vector))
    assert sp.simplify(result.expression) == 0


def test_laplacian_of_harmonic_function_vanishes() -> None:
    x, y, z = _xyz()
    harmonic = ScalarField((x, y, z), x**2 + y**2 - 2 * z**2)
    assert sp.simplify(laplacian(harmonic).expression) == 0

    # div(grad f) equals the Laplacian for an arbitrary scalar field.
    field = ScalarField((x, y, z), x**3 * y - sp.sin(z) * x)
    assert sp.simplify(divergence(gradient(field)).expression - field.laplacian().expression) == 0


def test_curl_requires_three_dimensions() -> None:
    x, y = sp.symbols("x y", real=True)
    planar = VectorField((x, y), (-y, x))
    with pytest.raises(ValueError, match="three-dimensional"):
        planar.curl()
    # The 2D divergence is still well defined.
    assert sp.simplify(planar.divergence().expression) == 0


def test_unresolved_symbols_are_rejected() -> None:
    x, y = sp.symbols("x y", real=True)
    stray = sp.Symbol("q")
    with pytest.raises(ValueError, match="unresolved symbols"):
        ScalarField((x, y), x + stray)
    # Declaring it as a parameter resolves it.
    field = ScalarField((x, y), x + stray, parameters=(stray,))
    assert field.parameters == (stray,)


def test_scalar_sampling_matches_numpy_and_is_deterministic() -> None:
    x, y = sp.symbols("x y", real=True)
    field = ScalarField((x, y), x**2 + y)
    axes = [np.linspace(-1.0, 1.0, 5), np.linspace(0.0, 2.0, 4)]

    sampled = field.sample(axes)
    gx, gy = np.meshgrid(axes[0], axes[1], indexing="ij")
    assert sampled.shape == (5, 4)
    assert np.allclose(sampled, gx**2 + gy)
    assert np.array_equal(sampled, field.sample(axes))


def test_vector_sampling_includes_parameters_and_component_axis() -> None:
    x, y = sp.symbols("x y", real=True)
    a = sp.Symbol("a")
    field = VectorField((x, y), (a * x, -y), parameters=(a,))
    axes = [np.linspace(0.0, 1.0, 3), np.linspace(0.0, 1.0, 3)]

    sampled = field.sample(axes, parameter_values={"a": 2.0})
    gx, gy = np.meshgrid(axes[0], axes[1], indexing="ij")
    assert sampled.shape == (3, 3, 2)
    assert np.allclose(sampled[..., 0], 2.0 * gx)
    assert np.allclose(sampled[..., 1], -gy)

    with pytest.raises(ValueError, match="missing parameter values"):
        field.sample(axes)
