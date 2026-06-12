"""Parameterized media models for cotangent Hamiltonian ray flow.

A *medium* turns spatially varying material data into the Hamiltonian
symbol of its ray flow on the cotangent bundle:

- scalar wave speed ``c(q)``: ``p(q, xi) = c(q)**2 * |xi|**2 / 2``;
- refractive index ``n(q)`` with reference speed ``c0``: the scalar-speed
  medium with ``c(q) = c0 / n(q)``;
- inverse-metric coefficients ``g^{ij}(q)``: the geodesic Hamiltonian
  ``p(q, xi) = xi^T g^{-1}(q) xi / 2``.

The scalar-speed case is the conformally flat special case
``g^{-1}(q) = c(q)**2 * I`` of the metric case. Each medium produces a
:class:`~engine.dynamics.cotangent.CotangentHamiltonianSystem`, so ray
integration, ray-bundle export, and Hamiltonian drift reporting apply
uniformly.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence

import sympy as sp

from engine.dynamics.cotangent import CotangentHamiltonianSystem


def _default_momenta(coordinates: Sequence[sp.Symbol]) -> tuple[sp.Symbol, ...]:
    return tuple(sp.Symbol(f"xi_{q.name}", real=True) for q in coordinates)


def _detected_parameters(
    expressions: Iterable[sp.Expr | float],
    coordinates: Sequence[sp.Symbol],
) -> tuple[sp.Symbol, ...]:
    free: set[sp.Symbol] = set()
    for expression in expressions:
        free |= sp.sympify(expression).free_symbols
    free -= set(coordinates)
    return tuple(sorted(free, key=lambda symbol: symbol.name))


def _validated_momenta(
    momenta: Sequence[sp.Symbol] | None,
    coordinates: Sequence[sp.Symbol],
) -> tuple[sp.Symbol, ...]:
    if momenta is None:
        return _default_momenta(coordinates)
    momenta = tuple(momenta)
    if len(momenta) != len(coordinates):
        raise ValueError("momenta must match coordinates in length")
    return momenta


def gaussian_lens_speed(
    coordinates: Sequence[sp.Expr],
    *,
    base_speed: sp.Expr | float,
    lens_strength: sp.Expr | float,
    lens_width: sp.Expr | float,
    center: Sequence[sp.Expr | float] | None = None,
) -> sp.Expr:
    """Scalar speed with a Gaussian slow-speed lens.

    ``c(q) = base_speed * (1 - lens_strength * exp(-|q - center|**2 / (2 * lens_width**2)))``
    """
    coordinates = tuple(coordinates)
    if center is None:
        center = (0,) * len(coordinates)
    radius_squared = sum(
        (q - q0) ** 2 for q, q0 in zip(coordinates, tuple(center), strict=True)
    )
    lens = lens_strength * sp.exp(-radius_squared / (2 * lens_width**2))
    return sp.simplify(base_speed * (1 - lens))


@dataclass(frozen=True)
class ScalarSpeedMedium:
    """An isotropic medium described by a scalar wave speed ``c(q) > 0``."""

    coordinates: tuple[sp.Symbol, ...]
    speed: sp.Expr
    parameters: tuple[sp.Symbol, ...] | None = None

    def __post_init__(self) -> None:
        if not self.coordinates:
            raise ValueError("coordinates must be non-empty")
        if self.parameters is None:
            object.__setattr__(
                self,
                "parameters",
                _detected_parameters([self.speed], self.coordinates),
            )

    def symbol(self, momenta: Sequence[sp.Symbol]) -> sp.Expr:
        momenta = _validated_momenta(momenta, self.coordinates)
        return sp.simplify(self.speed**2 * sum(m**2 for m in momenta) / 2)

    def to_system(
        self,
        momenta: Sequence[sp.Symbol] | None = None,
        time: sp.Symbol | None = None,
    ) -> CotangentHamiltonianSystem:
        momenta = _validated_momenta(momenta, self.coordinates)
        kwargs = {} if time is None else {"time": time}
        return CotangentHamiltonianSystem(
            coordinates=tuple(self.coordinates),
            momenta=momenta,
            symbol=self.symbol(momenta),
            parameters=tuple(self.parameters or ()),
            **kwargs,
        )


@dataclass(frozen=True)
class RefractiveIndexMedium:
    """An isotropic medium described by a refractive index ``n(q)``.

    The wave speed is ``c(q) = reference_speed / n(q)``; the ray flow is the
    scalar-speed flow of that speed.
    """

    coordinates: tuple[sp.Symbol, ...]
    index: sp.Expr
    reference_speed: sp.Expr | float = 1
    parameters: tuple[sp.Symbol, ...] | None = None

    def __post_init__(self) -> None:
        if not self.coordinates:
            raise ValueError("coordinates must be non-empty")
        if self.parameters is None:
            object.__setattr__(
                self,
                "parameters",
                _detected_parameters(
                    [self.index, self.reference_speed], self.coordinates
                ),
            )

    @property
    def speed(self) -> sp.Expr:
        return sp.simplify(sp.sympify(self.reference_speed) / self.index)

    def as_scalar_speed_medium(self) -> ScalarSpeedMedium:
        return ScalarSpeedMedium(
            coordinates=tuple(self.coordinates),
            speed=self.speed,
            parameters=tuple(self.parameters or ()),
        )

    def symbol(self, momenta: Sequence[sp.Symbol]) -> sp.Expr:
        return self.as_scalar_speed_medium().symbol(momenta)

    def to_system(
        self,
        momenta: Sequence[sp.Symbol] | None = None,
        time: sp.Symbol | None = None,
    ) -> CotangentHamiltonianSystem:
        return self.as_scalar_speed_medium().to_system(momenta=momenta, time=time)


@dataclass(frozen=True)
class InverseMetricMedium:
    """A medium given by inverse-metric coefficients ``g^{ij}(q)``.

    The symbol is the geodesic Hamiltonian ``p(q, xi) = xi^T g^{-1}(q) xi / 2``,
    so the ray flow is the cogeodesic flow of the metric ``g``.
    """

    coordinates: tuple[sp.Symbol, ...]
    inverse_metric: sp.Matrix
    parameters: tuple[sp.Symbol, ...] | None = None

    def __post_init__(self) -> None:
        if not self.coordinates:
            raise ValueError("coordinates must be non-empty")
        matrix = sp.Matrix(self.inverse_metric)
        object.__setattr__(self, "inverse_metric", matrix)
        dimension = len(self.coordinates)
        if matrix.shape != (dimension, dimension):
            raise ValueError(
                "inverse_metric must be a square matrix matching the coordinates"
            )
        if sp.simplify(matrix - matrix.T) != sp.zeros(dimension, dimension):
            raise ValueError("inverse_metric must be symmetric")
        if self.parameters is None:
            object.__setattr__(
                self,
                "parameters",
                _detected_parameters(matrix, self.coordinates),
            )

    @classmethod
    def from_metric(
        cls,
        coordinates: Sequence[sp.Symbol],
        metric: sp.Matrix,
        parameters: Sequence[sp.Symbol] | None = None,
    ) -> "InverseMetricMedium":
        inverse = sp.simplify(sp.Matrix(metric).inv())
        return cls(
            coordinates=tuple(coordinates),
            inverse_metric=inverse,
            parameters=None if parameters is None else tuple(parameters),
        )

    def symbol(self, momenta: Sequence[sp.Symbol]) -> sp.Expr:
        momenta = _validated_momenta(momenta, self.coordinates)
        xi = sp.Matrix(momenta)
        return sp.simplify((xi.T * self.inverse_metric * xi)[0, 0] / 2)

    def to_system(
        self,
        momenta: Sequence[sp.Symbol] | None = None,
        time: sp.Symbol | None = None,
    ) -> CotangentHamiltonianSystem:
        momenta = _validated_momenta(momenta, self.coordinates)
        kwargs = {} if time is None else {"time": time}
        return CotangentHamiltonianSystem(
            coordinates=tuple(self.coordinates),
            momenta=momenta,
            symbol=self.symbol(momenta),
            parameters=tuple(self.parameters or ()),
            **kwargs,
        )


__all__ = [
    "InverseMetricMedium",
    "RefractiveIndexMedium",
    "ScalarSpeedMedium",
    "gaussian_lens_speed",
]
