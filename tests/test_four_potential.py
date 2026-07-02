from __future__ import annotations

import pytest
import sympy as sp

from engine.electrodynamics import FourPotential, four_potential


def test_field_strength_is_exterior_derivative_and_antisymmetric() -> None:
    t, x, y, z = sp.symbols("t x y z", real=True)
    potential = four_potential(
        (t, x, y, z),
        (
            x * y,
            t * y + z,
            x * z,
            t * x,
        ),
    )

    field = potential.field_strength()

    assert field.shape == (4, 4)
    assert sp.simplify(field + field.T) == sp.zeros(4, 4)
    assert field[0, 1] == sp.diff(t * y + z, t) - sp.diff(x * y, x)
    assert field[1, 3] == sp.diff(t * x, x) - sp.diff(t * y + z, z)


def test_gauge_transform_leaves_field_strength_invariant() -> None:
    t, x, y, z = sp.symbols("t x y z", real=True)
    alpha = sp.Symbol("alpha", real=True)
    potential = FourPotential(
        coordinates=(t, x, y, z),
        components=(x * y, t * y + z, x * z, t * x),
        parameters=(alpha,),
    )
    chi = alpha * t * x + sp.sin(y * z)

    transformed = potential.gauge_transform(chi)

    assert transformed.components != potential.components
    assert sp.simplify(
        transformed.field_strength() - potential.field_strength()
    ) == sp.zeros(4, 4)


def test_homogeneous_maxwell_identity_holds_symbolically() -> None:
    t, x, y, z = sp.symbols("t x y z", real=True)
    potential = four_potential(
        (t, x, y, z),
        (
            x**2 + y * z,
            t * y + sp.sin(z),
            x * z + t**2,
            t * x - y**2,
        ),
    )

    assert potential.homogeneous_maxwell_residuals() == (0, 0, 0, 0)


def test_gauge_transform_rejects_unresolved_symbols() -> None:
    t, x, y, z = sp.symbols("t x y z", real=True)
    beta = sp.Symbol("beta", real=True)
    potential = four_potential((t, x, y, z), (0, 0, 0, 0))

    with pytest.raises(ValueError, match="unresolved symbols: beta"):
        potential.gauge_transform(beta * t)


def test_four_potential_validates_shapes_and_symbols() -> None:
    t, x, y, z = sp.symbols("t x y z", real=True)
    beta = sp.Symbol("beta", real=True)

    with pytest.raises(ValueError, match="one component per coordinate"):
        four_potential((t, x, y, z), (0, 0, 0))
    with pytest.raises(ValueError, match="coordinates must be distinct"):
        four_potential((t, x, x, z), (0, 0, 0, 0))
    with pytest.raises(ValueError, match="unresolved symbols: beta"):
        four_potential((t, x, y, z), (beta, 0, 0, 0))
