from __future__ import annotations

import numpy as np
import pytest
import sympy as sp

from engine.fieldtheory import (
    LagrangianFieldDensity,
    measured_stress_energy_conservation_residual,
    stress_energy_tensor,
)


def _klein_gordon_density() -> tuple[
    tuple[sp.Symbol, sp.Symbol],
    sp.Expr,
    sp.Symbol,
    LagrangianFieldDensity,
]:
    t, x = sp.symbols("t x")
    m = sp.Symbol("m")
    phi = sp.Function("phi")(t, x)
    density = (
        sp.Rational(1, 2) * sp.diff(phi, t) ** 2
        - sp.Rational(1, 2) * sp.diff(phi, x) ** 2
        - sp.Rational(1, 2) * m**2 * phi**2
    )
    return (t, x), phi, m, LagrangianFieldDensity((t, x), phi, density, parameters=(m,))


def test_klein_gordon_euler_lagrange_expression_matches_by_hand() -> None:
    (t, x), phi, m, field_density = _klein_gordon_density()

    expected = sp.diff(phi, t, 2) - sp.diff(phi, x, 2) + m**2 * phi
    assert sp.simplify(field_density.euler_lagrange_expression() - expected) == 0
    assert field_density.euler_lagrange_equation() == sp.Eq(expected, 0)


def test_canonical_momenta_are_density_derivatives_in_coordinate_order() -> None:
    (t, x), phi, _, field_density = _klein_gordon_density()

    assert field_density.field_derivatives == (sp.diff(phi, t), sp.diff(phi, x))
    assert field_density.canonical_momenta() == (sp.diff(phi, t), -sp.diff(phi, x))


def test_klein_gordon_stress_energy_tensor_is_symmetric() -> None:
    (t, x), phi, m, field_density = _klein_gordon_density()

    tensor = field_density.stress_energy_tensor()

    expected = sp.Matrix(
        [
            [
                sp.Rational(1, 2) * sp.diff(phi, t) ** 2
                + sp.Rational(1, 2) * sp.diff(phi, x) ** 2
                + sp.Rational(1, 2) * m**2 * phi**2,
                sp.diff(phi, t) * sp.diff(phi, x),
            ],
            [
                sp.diff(phi, t) * sp.diff(phi, x),
                sp.Rational(1, 2) * sp.diff(phi, t) ** 2
                + sp.Rational(1, 2) * sp.diff(phi, x) ** 2
                - sp.Rational(1, 2) * m**2 * phi**2,
            ],
        ]
    )
    assert tensor == tensor.T
    assert sp.simplify(tensor - expected) == sp.zeros(2, 2)
    assert sp.simplify(stress_energy_tensor(field_density) - expected) == sp.zeros(2, 2)


def test_stress_energy_divergence_is_euler_lagrange_on_shell_residual() -> None:
    (t, x), phi, _, field_density = _klein_gordon_density()

    divergence = field_density.stress_energy_divergence()
    euler_lagrange = field_density.euler_lagrange_expression()

    assert sp.simplify(divergence[0] + sp.diff(phi, t) * euler_lagrange) == 0
    assert sp.simplify(divergence[1] + sp.diff(phi, x) * euler_lagrange) == 0


def test_measured_stress_energy_conservation_residual_is_labeled_evidence() -> None:
    (t, x), _, _, field_density = _klein_gordon_density()
    axes = (np.linspace(0.0, 2.0 * np.pi, 9), np.linspace(-1.0, 1.0, 7))

    residual = field_density.measured_stress_energy_conservation_residual(
        sp.sin(t),
        axes,
        parameter_values={"m": 1.0},
    )

    assert residual.rigor == "measured"
    assert residual.evaluation == "measured-finite-difference-grid"
    assert residual.operator == "stress-energy-divergence"
    assert residual.values.shape == (9, 7, 2)
    assert np.max(np.abs(residual.values)) < 1e-12
    assert "proof" in residual.note
    payload = residual.to_dict()
    assert payload["rigor"] == "measured"
    assert payload["operator"] == "stress-energy-divergence"

    free_function_residual = measured_stress_energy_conservation_residual(
        field_density,
        sp.sin(t),
        axes,
        parameter_values={"m": 1.0},
    )
    assert np.allclose(free_function_residual.values, residual.values)


def test_measured_stress_energy_residual_validates_configuration_symbols() -> None:
    (t, _), _, _, field_density = _klein_gordon_density()
    stray = sp.Symbol("stray")

    with pytest.raises(ValueError, match="field configuration has unresolved symbols: stray"):
        field_density.measured_stress_energy_conservation_residual(
            sp.sin(t) + stray,
            (np.linspace(0.0, 1.0, 3), np.linspace(0.0, 1.0, 3)),
            parameter_values={"m": 1.0},
        )


def test_stress_energy_validates_metric_shape_and_symmetry() -> None:
    _, _, _, field_density = _klein_gordon_density()

    with pytest.raises(ValueError, match="metric must have shape"):
        field_density.stress_energy_tensor(sp.eye(3))

    with pytest.raises(ValueError, match="metric must be symmetric"):
        field_density.stress_energy_tensor(sp.Matrix([[1, 1], [0, 1]]))


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
