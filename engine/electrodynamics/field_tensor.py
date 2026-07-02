"""Faraday electromagnetic field tensor and invariants.

The electrodynamics package follows the relativity package's mostly-plus
Minkowski convention ``(-, +, +, +)``. In geometrized units ``c = 1``, the
covariant field tensor built from spatial electric and magnetic components is

``F_0i = -E_i``, ``F_i0 = E_i``, and ``F_ij = -epsilon_ijk B_k``.

With that convention the scalar contraction is exactly
``F_mu_nu F^mu_nu = 2(B^2 - E^2)``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import sympy as sp

from engine.relativity import MinkowskiMetric


def _spatial_triplet(components: Sequence[object], name: str) -> tuple[sp.Expr, ...]:
    values = tuple(sp.sympify(component) for component in components)
    if len(values) != 3:
        raise ValueError(f"{name} must have exactly three spatial components")
    return values


@dataclass(frozen=True)
class FaradayTensor:
    """Electromagnetic field tensor ``F_mu_nu`` from spatial ``E`` and ``B``.

    Components are stored symbolically, so the same object supports exact
    invariant checks and numeric substitution.
    """

    electric: tuple[sp.Expr, sp.Expr, sp.Expr]
    magnetic: tuple[sp.Expr, sp.Expr, sp.Expr]

    def __post_init__(self) -> None:
        object.__setattr__(self, "electric", _spatial_triplet(self.electric, "electric"))
        object.__setattr__(self, "magnetic", _spatial_triplet(self.magnetic, "magnetic"))

    @property
    def metric(self) -> MinkowskiMetric:
        return MinkowskiMetric(dimension=4)

    def covariant_matrix(self) -> sp.Matrix:
        """Return ``F_mu_nu`` as a 4x4 covariant tensor matrix."""

        ex, ey, ez = self.electric
        bx, by, bz = self.magnetic
        return sp.Matrix(
            [
                [0, -ex, -ey, -ez],
                [ex, 0, -bz, by],
                [ey, bz, 0, -bx],
                [ez, -by, bx, 0],
            ]
        )

    def contravariant_matrix(self) -> sp.Matrix:
        """Return ``F^mu_nu`` with both tensor indices raised."""

        eta_inverse = self.metric.inverse_eta()
        return sp.simplify(eta_inverse * self.covariant_matrix() * eta_inverse)

    def scalar_invariant(self) -> sp.Expr:
        """Return ``F_mu_nu F^mu_nu = 2(B^2 - E^2)``."""

        covariant = self.covariant_matrix()
        contravariant = self.contravariant_matrix()
        contraction = sum(
            covariant[mu, nu] * contravariant[mu, nu]
            for mu in range(4)
            for nu in range(4)
        )
        return sp.factor(sp.simplify(contraction))

    def electric_magnetic_invariant(self) -> sp.Expr:
        """Return the pseudoscalar invariant in ``E . B`` normalization."""

        return sp.factor(
            sp.simplify(
                sum(
                    e_component * b_component
                    for e_component, b_component in zip(self.electric, self.magnetic)
                )
            )
        )

    def invariant_pair(self) -> tuple[sp.Expr, sp.Expr]:
        """Return ``(F_mu_nu F^mu_nu, E . B)``."""

        return (self.scalar_invariant(), self.electric_magnetic_invariant())


def faraday_tensor(
    electric: Sequence[object],
    magnetic: Sequence[object],
) -> FaradayTensor:
    """Build a :class:`FaradayTensor` from spatial electric and magnetic fields."""

    return FaradayTensor(
        electric=_spatial_triplet(electric, "electric"),
        magnetic=_spatial_triplet(magnetic, "magnetic"),
    )


def electromagnetic_invariants(
    electric: Sequence[object],
    magnetic: Sequence[object],
) -> tuple[sp.Expr, sp.Expr]:
    """Return ``(F_mu_nu F^mu_nu, E . B)`` for spatial ``E`` and ``B``."""

    return faraday_tensor(electric, magnetic).invariant_pair()


__all__ = [
    "FaradayTensor",
    "electromagnetic_invariants",
    "faraday_tensor",
]
