"""Lorentz transformations: boosts, spatial rotations, and their composition.

A :class:`LorentzTransform` wraps a transformation matrix ``Lambda`` acting on
contravariant four-vector components, ``v'^mu = Lambda^mu_nu v^nu``. Constructors
build boosts (by rapidity along an axis, or by a velocity / rapidity vector in a
general direction) and spatial rotations; transforms compose with ``@`` and
invert. Every constructed transform preserves the Minkowski metric,
``Lambda^T eta Lambda == eta``, which is the defining property of the Lorentz
group.

Geometrized units ``c = 1`` are used throughout (consistent with
:mod:`engine.relativity.minkowski`), so velocities are dimensionless and the
collinear velocity-addition law is ``(u + v) / (1 + u v)``. The signature is the
global mostly-plus ``(-,+,+,+)``; the lone minus sign sits on the time component,
so the time index is ``0`` and spatial indices run ``1 .. dimension - 1``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import sympy as sp

from engine.relativity.four_vectors import CONTRAVARIANT, FourVector
from engine.relativity.minkowski import MinkowskiMetric


def _simplify(expression: sp.Matrix | sp.Expr) -> sp.Matrix | sp.Expr:
    """Simplification strong enough to cancel hyperbolic/trig combinations."""

    return sp.simplify(sp.expand_trig(expression))


@dataclass(frozen=True)
class LorentzTransform:
    """A Lorentz transformation acting on contravariant four-vector components."""

    matrix: sp.Matrix

    def __post_init__(self) -> None:
        matrix = sp.Matrix(self.matrix)
        rows, cols = matrix.shape
        if rows != cols:
            raise ValueError("a Lorentz transformation must be a square matrix")
        if rows < 2:
            raise ValueError("a Lorentz transformation needs at least 1+1 dimensions")
        object.__setattr__(self, "matrix", matrix)

    @property
    def dimension(self) -> int:
        return self.matrix.shape[0]

    @property
    def metric(self) -> MinkowskiMetric:
        return MinkowskiMetric(dimension=self.dimension)

    def preserves_metric(self) -> bool:
        """Whether ``Lambda^T eta Lambda == eta`` (the Lorentz condition)."""

        eta = self.metric.eta
        residual = _simplify(self.matrix.T * eta * self.matrix - eta)
        return residual == sp.zeros(self.dimension, self.dimension)

    def apply(self, four_vector: FourVector) -> FourVector:
        """Transform a four-vector's components.

        Contravariant components transform with ``Lambda``; covariant components
        transform with the inverse transpose ``(Lambda^{-1})^T``, so the
        contraction of a vector with its dual is preserved.
        """

        if four_vector.dimension != self.dimension:
            raise ValueError("four-vector dimension must match the transformation")
        column = sp.Matrix(four_vector.components)
        if four_vector.variance == CONTRAVARIANT:
            transformed = self.matrix * column
        else:
            transformed = self.matrix.inv().T * column
        return FourVector(
            components=tuple(_simplify(transformed)),
            variance=four_vector.variance,
        )

    def compose(self, other: "LorentzTransform") -> "LorentzTransform":
        """Compose transformations: ``(self.compose(other))`` applies ``other`` first."""

        if self.dimension != other.dimension:
            raise ValueError("cannot compose transformations of different dimensions")
        return LorentzTransform(_simplify(self.matrix * other.matrix))

    def __matmul__(self, other: "LorentzTransform") -> "LorentzTransform":
        return self.compose(other)

    def inverse(self) -> "LorentzTransform":
        return LorentzTransform(_simplify(self.matrix.inv()))

    @classmethod
    def identity(cls, dimension: int = 4) -> "LorentzTransform":
        return cls(sp.eye(dimension))


def _check_spatial_axis(axis: int, dimension: int) -> None:
    if not 1 <= axis <= dimension - 1:
        raise ValueError(
            f"spatial axis must be in 1..{dimension - 1} (0 is the time index)"
        )


def boost_along_axis(
    rapidity: sp.Expr | float,
    axis: int = 1,
    dimension: int = 4,
) -> LorentzTransform:
    """Boost by ``rapidity`` along a single spatial coordinate ``axis``.

    The rapidity ``phi`` relates to the boost velocity by ``beta = tanh(phi)``,
    ``gamma = cosh(phi)``. Collinear boosts add rapidities.
    """

    _check_spatial_axis(axis, dimension)
    cosh = sp.cosh(rapidity)
    sinh = sp.sinh(rapidity)
    matrix = sp.eye(dimension)
    matrix[0, 0] = cosh
    matrix[axis, axis] = cosh
    matrix[0, axis] = -sinh
    matrix[axis, 0] = -sinh
    return LorentzTransform(matrix)


def boost_from_velocity(velocity: Sequence[sp.Expr | float]) -> LorentzTransform:
    """General boost specified by a spatial velocity vector (``c = 1``).

    ``velocity`` has ``dimension - 1`` spatial components; the spacetime
    dimension is inferred as ``len(velocity) + 1``.
    """

    spatial = sp.Matrix(list(velocity))
    spatial_dim = spatial.shape[0]
    if spatial_dim < 1:
        raise ValueError("velocity must have at least one spatial component")
    dimension = spatial_dim + 1
    speed_squared = (spatial.T * spatial)[0, 0]
    gamma = 1 / sp.sqrt(1 - speed_squared)
    matrix = sp.zeros(dimension, dimension)
    matrix[0, 0] = gamma
    for i in range(spatial_dim):
        matrix[0, i + 1] = -gamma * spatial[i]
        matrix[i + 1, 0] = -gamma * spatial[i]
    for i in range(spatial_dim):
        for j in range(spatial_dim):
            kronecker = 1 if i == j else 0
            matrix[i + 1, j + 1] = (
                kronecker + (gamma - 1) * spatial[i] * spatial[j] / speed_squared
            )
    return LorentzTransform(_simplify(matrix))


def boost_from_rapidity(
    rapidity_vector: Sequence[sp.Expr | float],
) -> LorentzTransform:
    """General boost specified by a rapidity vector (direction + magnitude).

    The magnitude ``phi = |rapidity_vector|`` is the rapidity along the unit
    direction; equivalent to :func:`boost_from_velocity` with
    ``velocity = tanh(phi) * direction``.
    """

    vector = sp.Matrix(list(rapidity_vector))
    spatial_dim = vector.shape[0]
    if spatial_dim < 1:
        raise ValueError("rapidity vector must have at least one spatial component")
    dimension = spatial_dim + 1
    magnitude = sp.sqrt((vector.T * vector)[0, 0])
    cosh = sp.cosh(magnitude)
    sinh = sp.sinh(magnitude)
    direction = vector / magnitude
    matrix = sp.zeros(dimension, dimension)
    matrix[0, 0] = cosh
    for i in range(spatial_dim):
        matrix[0, i + 1] = -sinh * direction[i]
        matrix[i + 1, 0] = -sinh * direction[i]
    for i in range(spatial_dim):
        for j in range(spatial_dim):
            kronecker = 1 if i == j else 0
            matrix[i + 1, j + 1] = kronecker + (cosh - 1) * direction[i] * direction[j]
    return LorentzTransform(_simplify(matrix))


def spatial_rotation(
    angle: sp.Expr | float,
    axes: tuple[int, int] = (1, 2),
    dimension: int = 4,
) -> LorentzTransform:
    """Rotation by ``angle`` in the spatial plane spanned by ``axes``.

    ``axes`` are spatial coordinate indices (``>= 1``); the time component is
    left fixed, so a spatial rotation is automatically a Lorentz transformation.
    """

    first, second = axes
    if first == second:
        raise ValueError("rotation axes must be distinct")
    _check_spatial_axis(first, dimension)
    _check_spatial_axis(second, dimension)
    cos = sp.cos(angle)
    sin = sp.sin(angle)
    matrix = sp.eye(dimension)
    matrix[first, first] = cos
    matrix[second, second] = cos
    matrix[first, second] = -sin
    matrix[second, first] = sin
    return LorentzTransform(matrix)


def velocity_addition(
    u: sp.Expr | float,
    v: sp.Expr | float,
) -> sp.Expr:
    """Collinear relativistic velocity addition ``(u + v) / (1 + u v)`` (``c = 1``)."""

    return (sp.sympify(u) + sp.sympify(v)) / (1 + sp.sympify(u) * sp.sympify(v))


def rapidity_from_velocity(velocity: sp.Expr | float) -> sp.Expr:
    """Rapidity ``phi = atanh(beta)`` for a collinear velocity (``c = 1``)."""

    return sp.atanh(velocity)


def velocity_from_rapidity(rapidity: sp.Expr | float) -> sp.Expr:
    """Velocity ``beta = tanh(phi)`` for a rapidity (``c = 1``)."""

    return sp.tanh(rapidity)


__all__ = [
    "LorentzTransform",
    "boost_along_axis",
    "boost_from_velocity",
    "boost_from_rapidity",
    "spatial_rotation",
    "velocity_addition",
    "rapidity_from_velocity",
    "velocity_from_rapidity",
]
