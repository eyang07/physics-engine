"""Covariant Lorentz-force dynamics for charged particles."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import sympy as sp

from engine.dynamics import FirstOrderSystem
from engine.relativity import CONTRAVARIANT, FourVector, ProperTimeWorldline


def _spatial_triplet(components: Sequence[object], name: str) -> tuple[sp.Expr, ...]:
    values = tuple(sp.sympify(component) for component in components)
    if len(values) != 3:
        raise ValueError(f"{name} must have exactly three spatial components")
    return values


@dataclass(frozen=True)
class CovariantLorentzForce:
    """Uniform electromagnetic Lorentz force in flat spacetime.

    The state-space form is proper-time parameterized:
    ``dx^mu/dtau = p^mu / m`` and
    ``dp^mu/dtau = (q / m) F^mu_nu p^nu``. The mixed field operator is written
    in the physical convention whose coordinate-time, low-velocity spatial
    limit is ``q(E + v x B)``.
    """

    electric: tuple[sp.Expr, sp.Expr, sp.Expr]
    magnetic: tuple[sp.Expr, sp.Expr, sp.Expr]
    charge: sp.Expr = sp.Symbol("q", real=True)
    mass: sp.Expr = sp.Symbol("m", positive=True)
    light_speed: sp.Expr = sp.Integer(1)

    def __post_init__(self) -> None:
        object.__setattr__(self, "electric", _spatial_triplet(self.electric, "electric"))
        object.__setattr__(self, "magnetic", _spatial_triplet(self.magnetic, "magnetic"))
        object.__setattr__(self, "charge", sp.sympify(self.charge))
        object.__setattr__(self, "mass", sp.sympify(self.mass))
        object.__setattr__(self, "light_speed", sp.sympify(self.light_speed))

    @property
    def worldline(self) -> ProperTimeWorldline:
        return ProperTimeWorldline(
            dimension=4,
            mass=self.mass,
            light_speed=self.light_speed,
        )

    def mixed_field_operator(self) -> sp.Matrix:
        """Return the mixed operator ``F^mu_nu`` used by the force law."""

        ex, ey, ez = (sp.simplify(component / self.light_speed) for component in self.electric)
        bx, by, bz = self.magnetic
        return sp.Matrix(
            [
                [0, ex, ey, ez],
                [ex, 0, bz, -by],
                [ey, -bz, 0, bx],
                [ez, by, -bx, 0],
            ]
        )

    def four_force(
        self,
        momentum: Sequence[object] | FourVector | None = None,
    ) -> FourVector:
        """Return ``dp^mu/dtau = (q / m) F^mu_nu p^nu``."""

        if momentum is None:
            components = self.worldline.four_momentum_symbols
        elif isinstance(momentum, FourVector):
            vector = momentum if momentum.is_contravariant else momentum.raise_index()
            if vector.dimension != 4:
                raise ValueError("momentum must be a four-vector")
            components = vector.components
        else:
            components = tuple(sp.sympify(component) for component in momentum)
            if len(components) != 4:
                raise ValueError("momentum must have four components")

        force = sp.simplify(
            (self.charge / self.mass)
            * self.mixed_field_operator()
            * sp.Matrix(components)
        )
        return FourVector(tuple(force), variance=CONTRAVARIANT)

    def first_order_system(self) -> FirstOrderSystem:
        """Return the proper-time charged-particle dynamics."""

        return self.worldline.momentum_dynamics(self.four_force())


def lorentz_force_operator(
    electric: Sequence[object],
    magnetic: Sequence[object],
) -> sp.Matrix:
    """Return the mixed field operator that contracts with ``p^nu``."""

    return CovariantLorentzForce(
        electric=_spatial_triplet(electric, "electric"),
        magnetic=_spatial_triplet(magnetic, "magnetic"),
    ).mixed_field_operator()


def lorentz_four_force(
    electric: Sequence[object],
    magnetic: Sequence[object],
    momentum: Sequence[object] | FourVector,
    *,
    charge: object = sp.Symbol("q", real=True),
    mass: object = sp.Symbol("m", positive=True),
    light_speed: object = sp.Integer(1),
) -> FourVector:
    """Return the covariant Lorentz four-force for a supplied momentum."""

    return CovariantLorentzForce(
        electric=_spatial_triplet(electric, "electric"),
        magnetic=_spatial_triplet(magnetic, "magnetic"),
        charge=sp.sympify(charge),
        mass=sp.sympify(mass),
        light_speed=sp.sympify(light_speed),
    ).four_force(momentum)


def lorentz_force_system(
    electric: Sequence[object],
    magnetic: Sequence[object],
    *,
    charge: object = sp.Symbol("q", real=True),
    mass: object = sp.Symbol("m", positive=True),
    light_speed: object = sp.Integer(1),
) -> FirstOrderSystem:
    """Build a proper-time first-order system for a charged particle."""

    return CovariantLorentzForce(
        electric=_spatial_triplet(electric, "electric"),
        magnetic=_spatial_triplet(magnetic, "magnetic"),
        charge=sp.sympify(charge),
        mass=sp.sympify(mass),
        light_speed=sp.sympify(light_speed),
    ).first_order_system()


__all__ = [
    "CovariantLorentzForce",
    "lorentz_force_operator",
    "lorentz_force_system",
    "lorentz_four_force",
]
