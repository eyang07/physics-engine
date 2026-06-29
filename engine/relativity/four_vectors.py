"""The four-vector value object.

A :class:`FourVector` is a thin, typed container for the components of a
relativistic four-vector together with its variance (contravariant ``v^mu`` or
covariant ``v_mu``). It exposes the Minkowski norm², index raising/lowering,
contraction with an opposite-variance vector, and the causal classification
(timelike / null / spacelike).

This is deliberately **not** a general tensor-calculus engine: it holds one
rank-1 object and reuses :class:`~engine.relativity.minkowski.MinkowskiMetric`
for every metric contraction, so the global mostly-plus signature ``(-,+,+,+)``
is the single source of truth.
"""

from __future__ import annotations

from dataclasses import dataclass

import sympy as sp

from engine.relativity.minkowski import MinkowskiMetric

CONTRAVARIANT = "contravariant"
COVARIANT = "covariant"
_VARIANCES = (CONTRAVARIANT, COVARIANT)


@dataclass(frozen=True)
class FourVector:
    """A rank-1 four-vector with an explicit variance.

    ``components`` are stored as SymPy expressions, so symbolic and numeric
    inputs share one code path; substitute numbers into a symbolic vector to
    recover the numeric result.
    """

    components: tuple[sp.Expr, ...]
    variance: str = CONTRAVARIANT

    def __post_init__(self) -> None:
        if self.variance not in _VARIANCES:
            raise ValueError(f"variance must be one of {_VARIANCES}")
        components = tuple(sp.sympify(component) for component in self.components)
        if len(components) < 2:
            raise ValueError("a four-vector needs at least 1+1 components")
        object.__setattr__(self, "components", components)

    @property
    def dimension(self) -> int:
        return len(self.components)

    @property
    def is_contravariant(self) -> bool:
        return self.variance == CONTRAVARIANT

    @property
    def is_covariant(self) -> bool:
        return self.variance == COVARIANT

    @property
    def metric(self) -> MinkowskiMetric:
        """The flat metric matching this vector's dimension."""

        return MinkowskiMetric(dimension=self.dimension)

    def lower(self) -> "FourVector":
        """Lower the index: ``v_mu = eta_{mu nu} v^nu`` (contravariant -> covariant)."""

        if self.is_covariant:
            raise ValueError("four-vector index is already covariant")
        lowered = self.metric.lower(self.components)
        return FourVector(components=tuple(lowered), variance=COVARIANT)

    def raise_index(self) -> "FourVector":
        """Raise the index: ``v^mu = eta^{mu nu} v_nu`` (covariant -> contravariant)."""

        if self.is_contravariant:
            raise ValueError("four-vector index is already contravariant")
        raised = self.metric.raise_index(self.components)
        return FourVector(components=tuple(raised), variance=CONTRAVARIANT)

    def norm_squared(self) -> sp.Expr:
        """Minkowski norm² using the global signature.

        For a contravariant vector this is ``eta_{mu nu} v^mu v^nu``; for a
        covariant vector it is ``eta^{mu nu} v_mu v_nu``. Both reduce to the
        contraction of the vector with its own lowered/raised partner.
        """

        if self.is_contravariant:
            return self.metric.norm_squared(self.components)
        column = sp.Matrix(self.components)
        return sp.simplify((column.T * self.metric.inverse_eta() * column)[0, 0])

    def contract(self, other: "FourVector") -> sp.Expr:
        """Contract with an opposite-variance four-vector: ``a_mu b^mu``.

        No metric is needed: an upper index contracts directly with a lower one
        as a component-wise sum.
        """

        if self.dimension != other.dimension:
            raise ValueError("four-vectors must share a dimension to contract")
        if self.variance == other.variance:
            raise ValueError(
                "contraction requires one covariant and one contravariant index"
            )
        return sp.simplify(
            sum(a * b for a, b in zip(self.components, other.components))
        )

    def classify(self) -> str:
        """Causal character from the sign of the (numeric) norm².

        ``"timelike"`` (norm² < 0), ``"null"`` (norm² == 0), or ``"spacelike"``
        (norm² > 0) under the mostly-plus signature.
        """

        contravariant = self if self.is_contravariant else self.raise_index()
        return self.metric.classify(contravariant.components)

    @property
    def is_timelike(self) -> bool:
        return self.classify() == "timelike"

    @property
    def is_null(self) -> bool:
        return self.classify() == "null"

    @property
    def is_spacelike(self) -> bool:
        return self.classify() == "spacelike"


__all__ = [
    "CONTRAVARIANT",
    "COVARIANT",
    "FourVector",
]
