from __future__ import annotations

import pytest
import sympy as sp

from engine.fieldtheory import LagrangianFieldDensity


def test_klein_gordon_euler_lagrange_expression_matches_by_hand() -> None:
    t, x = sp.symbols("t x")
    m = sp.Symbol("m")
    phi = sp.Function("phi")(t, x)
    density = (
        sp.Rational(1, 2) * sp.diff(phi, t) ** 2
        - sp.Rational(1, 2) * sp.diff(phi, x) ** 2
        - sp.Rational(1, 2) * m**2 * phi**2
    )

    field_density = LagrangianFieldDensity((t, x), phi, density, parameters=(m,))

    expected = sp.diff(phi, t, 2) - sp.diff(phi, x, 2) + m**2 * phi
    assert sp.simplify(field_density.euler_lagrange_expression() - expected) == 0
    assert field_density.euler_lagrange_equation() == sp.Eq(expected, 0)


def test_canonical_momenta_are_density_derivatives_in_coordinate_order() -> None:
    t, x = sp.symbols("t x")
    m = sp.Symbol("m")
    phi = sp.Function("phi")(t, x)
    density = (
        sp.Rational(1, 2) * sp.diff(phi, t) ** 2
        - sp.Rational(1, 2) * sp.diff(phi, x) ** 2
        - sp.Rational(1, 2) * m**2 * phi**2
    )

    field_density = LagrangianFieldDensity((t, x), phi, density, parameters=(m,))

    assert field_density.field_derivatives == (sp.diff(phi, t), sp.diff(phi, x))
    assert field_density.canonical_momenta() == (sp.diff(phi, t), -sp.diff(phi, x))


def test_field_density_validates_free_symbols_like_fields() -> None:
    t, x = sp.symbols("t x")
    m, stray = sp.symbols("m stray")
    phi = sp.Function("phi")(t, x)
    density = sp.Rational(1, 2) * sp.diff(phi, t) ** 2 - stray * phi

    with pytest.raises(ValueError, match="unresolved symbols: stray"):
        LagrangianFieldDensity((t, x), phi, density, parameters=(m,))

    allowed = LagrangianFieldDensity((t, x), phi, density, parameters=(stray,))
    assert stray in allowed.parameters


def test_field_density_rejects_more_than_one_scalar_field() -> None:
    t, x = sp.symbols("t x")
    phi = sp.Function("phi")(t, x)
    psi = sp.Function("psi")(t, x)

    with pytest.raises(ValueError, match="exactly one scalar field"):
        LagrangianFieldDensity((t, x), phi, sp.diff(phi, t) ** 2 + psi)


def test_field_density_validates_coordinates_parameters_and_field_arguments() -> None:
    t, x = sp.symbols("t x")
    phi = sp.Function("phi")(t, x)

    with pytest.raises(ValueError, match="coordinates must be distinct"):
        LagrangianFieldDensity((t, t), sp.Function("phi")(t, t), phi)

    with pytest.raises(ValueError, match="parameters must not overlap coordinates: x"):
        LagrangianFieldDensity((t, x), phi, phi, parameters=(x,))

    with pytest.raises(ValueError, match="field arguments must match coordinates"):
        LagrangianFieldDensity((t, x), sp.Function("phi")(x, t), phi)

    with pytest.raises(ValueError, match="field must be an applied scalar function"):
        LagrangianFieldDensity((t, x), sp.Symbol("phi"), sp.Symbol("phi"))
