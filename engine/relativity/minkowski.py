"""Minkowski spacetime: the flat Lorentzian metric and its inner product.

This module fixes the single global signature convention used throughout
``engine.relativity`` — the **mostly-plus** signature ``(-, +, +, +)`` — and
provides a thin Lorentzian metric object built on
:class:`~engine.dynamics.metric.MetricGeometry`. Minkowski space is a constant
Lorentzian metric, so index raising/lowering, the Minkowski inner product, and
the invariant interval reuse the existing metric machinery rather than
re-deriving tensor algebra.

Geometrized units ``c = 1`` are the default, consistent with the geometrized
Schwarzschild metric in :mod:`engine.dynamics.metric`. The metric ``eta`` is
therefore the dimensionless signature matrix ``diag(-1, 1, 1, 1)``: in these
units the invariant interval is

``s^2 = eta_{mu nu} dx^mu dx^nu = -dt^2 + dx^2 + dy^2 + dz^2``,

which is negative for timelike separations, zero for null separations, and
positive for spacelike separations.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import sympy as sp

from engine.dynamics.metric import MetricGeometry

#: Global signature convention for ``engine.relativity``: mostly-plus, with the
#: time component carrying the minus sign.
SIGNATURE = (-1, 1, 1, 1)
SIGNATURE_NAME = "(-,+,+,+)"

#: Tolerance below which a numeric interval is treated as null (lightlike).
_NULL_TOLERANCE = 1e-12


def _coordinate_symbols(dimension: int) -> tuple[sp.Symbol, ...]:
    """Real coordinate symbols ``(t, x, y, z, ...)`` for the given dimension."""

    names = ("t", "x", "y", "z")
    if dimension <= len(names):
        chosen: tuple[str, ...] = names[:dimension]
    else:
        chosen = ("t",) + tuple(f"x{index}" for index in range(1, dimension))
    return tuple(sp.Symbol(name, real=True) for name in chosen)


def minkowski_eta(dimension: int = 4) -> sp.Matrix:
    """The flat metric ``eta`` with mostly-plus signature ``(-,+,...,+)``.

    The time component carries the lone minus sign; every spatial component is
    ``+1``. Defaults to 1+3 dimensions.
    """

    if dimension < 2:
        raise ValueError("Minkowski spacetime needs at least 1+1 dimensions")
    diagonal = [SIGNATURE[0]] + [1] * (dimension - 1)
    return sp.diag(*diagonal)


@dataclass(frozen=True)
class MinkowskiMetric:
    """Flat Lorentzian metric of dimension ``1 + (dimension - 1)``.

    Wraps a :class:`~engine.dynamics.metric.MetricGeometry` built from the
    constant signature matrix :func:`minkowski_eta`, and exposes the index
    raise/lower maps, the Minkowski inner product, and the invariant interval.
    Coordinate separations and four-vectors may be supplied as plain sequences,
    SymPy matrices, or row/column vectors of length :attr:`dimension`.
    """

    dimension: int = 4

    def __post_init__(self) -> None:
        if self.dimension < 2:
            raise ValueError("Minkowski spacetime needs at least 1+1 dimensions")

    @property
    def coordinates(self) -> tuple[sp.Symbol, ...]:
        """Spacetime coordinate symbols ``(t, x, y, z, ...)``."""

        return _coordinate_symbols(self.dimension)

    @property
    def eta(self) -> sp.Matrix:
        """The covariant metric ``eta_{mu nu}`` with signature ``(-,+,+,+)``."""

        return minkowski_eta(self.dimension)

    @property
    def geometry(self) -> MetricGeometry:
        """The flat :class:`MetricGeometry` backing this metric (constant ``eta``)."""

        return MetricGeometry(
            coordinates=self.coordinates,
            metric=self.eta,
            parameters=(),
        )

    def inverse_eta(self) -> sp.Matrix:
        """The contravariant metric ``eta^{mu nu}`` (reuses ``MetricGeometry``).

        For the mostly-plus signature ``eta^{mu nu} == eta_{mu nu}``.
        """

        return self.geometry.inverse_metric()

    def _column(self, vector: Sequence[object] | sp.Matrix) -> sp.Matrix:
        column = sp.Matrix(vector)
        if column.shape == (1, self.dimension):
            column = column.T
        if column.shape != (self.dimension, 1):
            raise ValueError(
                f"expected a {self.dimension}-component four-vector, got shape {column.shape}"
            )
        return column

    def lower(self, vector: Sequence[object] | sp.Matrix) -> sp.Matrix:
        """Lower an index: ``v_mu = eta_{mu nu} v^nu`` (contravariant -> covariant)."""

        return sp.simplify(self.eta * self._column(vector))

    def raise_index(self, covector: Sequence[object] | sp.Matrix) -> sp.Matrix:
        """Raise an index: ``v^mu = eta^{mu nu} v_nu`` (covariant -> contravariant)."""

        return sp.simplify(self.inverse_eta() * self._column(covector))

    def inner_product(
        self,
        u: Sequence[object] | sp.Matrix,
        v: Sequence[object] | sp.Matrix,
    ) -> sp.Expr:
        """Minkowski inner product ``eta_{mu nu} u^mu v^nu`` of two four-vectors."""

        u_col = self._column(u)
        v_col = self._column(v)
        return sp.simplify((u_col.T * self.eta * v_col)[0, 0])

    def norm_squared(self, vector: Sequence[object] | sp.Matrix) -> sp.Expr:
        """Minkowski norm² ``eta_{mu nu} v^mu v^nu`` of a four-vector."""

        return self.inner_product(vector, vector)

    def interval_squared(self, separation: Sequence[object] | sp.Matrix) -> sp.Expr:
        """Invariant interval ``s^2 = eta_{mu nu} dx^mu dx^nu`` of a separation.

        Negative for timelike, zero for null, positive for spacelike
        separations in the mostly-plus signature.
        """

        return self.norm_squared(separation)

    def classify(self, separation: Sequence[object] | sp.Matrix) -> str:
        """Causal character of a numeric coordinate separation.

        Returns ``"timelike"`` (``s^2 < 0``), ``"null"`` (``s^2 == 0``), or
        ``"spacelike"`` (``s^2 > 0``) under the mostly-plus signature.
        """

        squared = self.interval_squared(separation)
        if not squared.is_number:
            raise ValueError("classification requires a numeric separation")
        value = float(squared)
        if abs(value) <= _NULL_TOLERANCE:
            return "null"
        return "timelike" if value < 0.0 else "spacelike"


__all__ = [
    "SIGNATURE",
    "SIGNATURE_NAME",
    "MinkowskiMetric",
    "minkowski_eta",
]
