from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import sympy as sp

from engine.fields import ScalarField, VectorField


def _coordinate_tuple(coordinates: Sequence[sp.Symbol]) -> tuple[sp.Symbol, sp.Symbol]:
    coords = tuple(coordinates)
    if len(coords) != 2:
        raise ValueError("the electromagnetic field gallery system uses a 2D slice")
    return coords


def _squared_distance(
    coordinates: tuple[sp.Symbol, sp.Symbol],
    position: tuple[sp.Expr, sp.Expr],
) -> sp.Expr:
    return sum((coordinate - center) ** 2 for coordinate, center in zip(coordinates, position))


def _parameters_for(
    expressions: Sequence[sp.Expr],
    coordinates: tuple[sp.Symbol, ...],
) -> tuple[sp.Symbol, ...]:
    free_symbols: set[sp.Symbol] = set()
    for expression in expressions:
        free_symbols.update(sp.sympify(expression).free_symbols)
    return tuple(sorted(free_symbols - set(coordinates), key=lambda symbol: symbol.name))


def point_charge_potential(
    coordinates: Sequence[sp.Symbol],
    *,
    charge: sp.Expr,
    position: tuple[sp.Expr, sp.Expr],
    epsilon0: sp.Expr,
) -> ScalarField:
    """Electrostatic potential of a point charge in a planar cross-section."""

    coords = _coordinate_tuple(coordinates)
    r = sp.sqrt(_squared_distance(coords, position))
    expression = sp.sympify(charge) / (4 * sp.pi * sp.sympify(epsilon0) * r)
    return ScalarField(coords, expression, parameters=_parameters_for((expression,), coords))


def point_charge_electric_field(
    coordinates: Sequence[sp.Symbol],
    *,
    charge: sp.Expr,
    position: tuple[sp.Expr, sp.Expr],
    epsilon0: sp.Expr,
) -> VectorField:
    """Coulomb field of a point charge, restricted to a planar cross-section."""

    coords = _coordinate_tuple(coordinates)
    r2 = _squared_distance(coords, position)
    r3 = r2 ** sp.Rational(3, 2)
    components = tuple(
        sp.sympify(charge) * (coordinate - center) / (4 * sp.pi * sp.sympify(epsilon0) * r3)
        for coordinate, center in zip(coords, position)
    )
    return VectorField(coords, components, parameters=_parameters_for(components, coords))


def electric_dipole_potential(
    coordinates: Sequence[sp.Symbol],
    *,
    charge: sp.Expr,
    separation: sp.Expr,
    epsilon0: sp.Expr,
) -> ScalarField:
    """Potential of equal opposite charges on the x-axis."""

    coords = _coordinate_tuple(coordinates)
    positive = (-separation / 2, sp.Integer(0))
    negative = (separation / 2, sp.Integer(0))
    potential = (
        point_charge_potential(
            coords, charge=charge, position=positive, epsilon0=epsilon0
        ).expression
        + point_charge_potential(
            coords, charge=-charge, position=negative, epsilon0=epsilon0
        ).expression
    )
    expression = sp.simplify(potential)
    return ScalarField(coords, expression, parameters=_parameters_for((expression,), coords))


def electric_dipole_field(
    coordinates: Sequence[sp.Symbol],
    *,
    charge: sp.Expr,
    separation: sp.Expr,
    epsilon0: sp.Expr,
) -> VectorField:
    """Electric field of the dipole used for the gallery export."""

    coords = _coordinate_tuple(coordinates)
    positive = (-separation / 2, sp.Integer(0))
    negative = (separation / 2, sp.Integer(0))
    positive_field = point_charge_electric_field(
        coords, charge=charge, position=positive, epsilon0=epsilon0
    )
    negative_field = point_charge_electric_field(
        coords, charge=-charge, position=negative, epsilon0=epsilon0
    )
    components = tuple(
        sp.simplify(left + right)
        for left, right in zip(positive_field.components, negative_field.components)
    )
    return VectorField(coords, components, parameters=_parameters_for(components, coords))


def magnetic_dipole_field(
    coordinates: Sequence[sp.Symbol],
    *,
    moment: sp.Expr,
    mu0: sp.Expr,
) -> VectorField:
    """Magnetic dipole field in the z=0 plane for a dipole moment along +y."""

    x, y = _coordinate_tuple(coordinates)
    r2 = x**2 + y**2
    r5 = r2 ** sp.Rational(5, 2)
    prefactor = sp.sympify(mu0) / (4 * sp.pi)
    components = (
        prefactor * 3 * sp.sympify(moment) * x * y / r5,
        prefactor * sp.sympify(moment) * (3 * y**2 - r2) / r5,
    )
    simplified = tuple(sp.simplify(component) for component in components)
    return VectorField((x, y), simplified, parameters=_parameters_for(simplified, (x, y)))


def current_loop_axis_field(
    z: sp.Expr,
    *,
    current: sp.Expr,
    radius: sp.Expr,
    mu0: sp.Expr,
) -> sp.Expr:
    """Magnetic field magnitude on the symmetry axis of a circular current loop."""

    return sp.simplify(mu0 * current * radius**2 / (2 * (radius**2 + z**2) ** sp.Rational(3, 2)))


@dataclass(frozen=True)
class ElectromagneticFieldSystem:
    coordinates: tuple[sp.Symbol, sp.Symbol]
    electric_potential: ScalarField
    electric_field: VectorField
    magnetic_field: VectorField
    current_loop_axis_b: sp.Expr
    source_separation: sp.Expr

    def __post_init__(self) -> None:
        if self.electric_potential.dimension != 2:
            raise ValueError("electric potential must be defined on a 2D slice")
        if self.electric_field.dimension != 2 or self.magnetic_field.dimension != 2:
            raise ValueError("electric and magnetic fields must be planar vector fields")

    def manifest_metadata(self) -> dict[str, object]:
        x, y = self.coordinates
        return {
            "kind": "electromagnetic-static",
            "coordinates": [x.name, y.name],
            "sources": [
                {
                    "kind": "point-charge",
                    "charge": "+q",
                    "positionLatex": [sp.latex(-self.source_separation / 2), "0"],
                },
                {
                    "kind": "point-charge",
                    "charge": "-q",
                    "positionLatex": [sp.latex(self.source_separation / 2), "0"],
                },
                {
                    "kind": "magnetic-dipole",
                    "momentDirection": "+y",
                    "positionLatex": ["0", "0"],
                },
                {
                    "kind": "current-loop-reference",
                    "axisFieldLatex": sp.latex(self.current_loop_axis_b),
                },
            ],
        }


def build_system(
    *,
    charge: sp.Expr | float | None = None,
    separation: sp.Expr | float | None = None,
    epsilon0: sp.Expr | float | None = None,
    magnetic_moment: sp.Expr | float | None = None,
    mu0: sp.Expr | float | None = None,
    loop_current: sp.Expr | float | None = None,
    loop_radius: sp.Expr | float | None = None,
) -> ElectromagneticFieldSystem:
    x, y = sp.symbols("x y", real=True)
    z = sp.Symbol("z", real=True)
    q = sp.Symbol("q", real=True) if charge is None else charge
    d = sp.Symbol("d", positive=True) if separation is None else separation
    eps = sp.Symbol("epsilon0", positive=True) if epsilon0 is None else epsilon0
    moment = sp.Symbol("m_dipole", real=True) if magnetic_moment is None else magnetic_moment
    permeability = sp.Symbol("mu0", positive=True) if mu0 is None else mu0
    current = sp.Symbol("I", real=True) if loop_current is None else loop_current
    radius = sp.Symbol("a", positive=True) if loop_radius is None else loop_radius

    coordinates = (x, y)
    return ElectromagneticFieldSystem(
        coordinates=coordinates,
        electric_potential=electric_dipole_potential(
            coordinates, charge=q, separation=d, epsilon0=eps
        ),
        electric_field=electric_dipole_field(
            coordinates, charge=q, separation=d, epsilon0=eps
        ),
        magnetic_field=magnetic_dipole_field(
            coordinates, moment=moment, mu0=permeability
        ),
        current_loop_axis_b=current_loop_axis_field(
            z, current=current, radius=radius, mu0=permeability
        ),
        source_separation=d,
    )


system = build_system()
