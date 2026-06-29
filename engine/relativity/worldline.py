"""Proper-time worldlines, four-velocity, and four-momentum.

A :class:`ProperTimeWorldline` describes a particle worldline ``x^mu(tau)``
parameterized by **proper time** ``tau`` in flat Minkowski spacetime, and
reduces to a :class:`~engine.dynamics.first_order.FirstOrderSystem` in the state
``(x^mu, u^mu)`` so the existing integrators apply directly.

Parameterization / unit convention (the single source of truth for this module)
--------------------------------------------------------------------------------
- The signature is the global mostly-plus ``(-,+,+,+)`` from
  :mod:`engine.relativity.minkowski`, so the metric is the *bare* ``eta``.
- The time coordinate carries an explicit factor of ``c``: ``x^0 = c t`` (it has
  the same length dimension as the spatial coordinates). Recover coordinate time
  as ``t = x^0 / c``.
- **Proper time** ``tau`` is the affine parameter, defined by
  ``c^2 dtau^2 = -eta_{mu nu} dx^mu dx^nu`` (positive for a timelike worldline,
  since ``eta dx dx < 0`` there).
- The **four-velocity** is ``u^mu = dx^mu / dtau``. With ``x^0 = c t`` and the
  coordinate 3-velocity ``v = dx/dt`` this is ``u^mu = gamma (c, v)`` where
  ``gamma = 1 / sqrt(1 - |v|^2 / c^2)``, and it is normalized to

      ``u^mu u_mu = -c^2``   (timelike, future-directed).

- The **four-momentum** is ``p^mu = m u^mu``; on shell ``p^mu p_mu = -(m c)^2``.

The free particle (zero four-acceleration) is a straight Minkowski geodesic;
:meth:`ProperTimeWorldline.first_order_system` accepts an optional four-
acceleration so later work (external four-forces) reuses the same reduction.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence

import sympy as sp

from engine.dynamics.first_order import FirstOrderSystem
from engine.mechanics.coordinates import velocity_symbol
from engine.relativity.four_vectors import CONTRAVARIANT, FourVector
from engine.relativity.minkowski import MinkowskiMetric


def _coordinate_symbols(dimension: int) -> tuple[sp.Symbol, ...]:
    """Spacetime coordinate symbols ``(x0, x1, ...)`` with ``x0 = c t``."""

    return tuple(sp.Symbol(f"x{index}", real=True) for index in range(dimension))


@dataclass(frozen=True)
class ProperTimeWorldline:
    """A proper-time-parameterized worldline in flat spacetime."""

    dimension: int = 4
    mass: sp.Expr = field(default_factory=lambda: sp.Symbol("m", positive=True))
    light_speed: sp.Expr = field(default_factory=lambda: sp.Symbol("c", positive=True))
    proper_time: sp.Symbol = field(default_factory=lambda: sp.Symbol("tau", real=True))

    def __post_init__(self) -> None:
        if self.dimension < 2:
            raise ValueError("a worldline needs at least 1+1 spacetime dimensions")

    @property
    def metric(self) -> MinkowskiMetric:
        return MinkowskiMetric(dimension=self.dimension)

    @property
    def coordinates(self) -> tuple[sp.Symbol, ...]:
        """Spacetime coordinate symbols ``x^mu`` with ``x^0 = c t``."""

        return _coordinate_symbols(self.dimension)

    @property
    def four_velocity_symbols(self) -> tuple[sp.Symbol, ...]:
        """Four-velocity component symbols ``u^mu = dx^mu / dtau``."""

        return tuple(velocity_symbol(coordinate) for coordinate in self.coordinates)

    def four_velocity(self) -> FourVector:
        """The four-velocity ``u^mu`` as a contravariant :class:`FourVector` of symbols."""

        return FourVector(self.four_velocity_symbols, variance=CONTRAVARIANT)

    def four_momentum(self) -> FourVector:
        """The four-momentum ``p^mu = m u^mu`` as a contravariant :class:`FourVector`."""

        return FourVector(
            tuple(self.mass * u for u in self.four_velocity_symbols),
            variance=CONTRAVARIANT,
        )

    def four_velocity_from_velocity(
        self,
        velocity: Sequence[sp.Expr | float],
    ) -> FourVector:
        """Physical four-velocity ``gamma (c, v)`` from a coordinate 3-velocity ``v``.

        ``velocity`` carries ``dimension - 1`` spatial components ``dx^i / dt``.
        The result is normalized: its Minkowski norm² is ``-c^2``.
        """

        spatial = sp.Matrix(list(velocity))
        if spatial.shape[0] != self.dimension - 1:
            raise ValueError(
                f"velocity must have {self.dimension - 1} spatial components"
            )
        c = self.light_speed
        speed_squared = (spatial.T * spatial)[0, 0]
        gamma = 1 / sp.sqrt(1 - speed_squared / c**2)
        components = (gamma * c, *(gamma * spatial[i] for i in range(spatial.shape[0])))
        return FourVector(components, variance=CONTRAVARIANT)

    def four_momentum_from_velocity(
        self,
        velocity: Sequence[sp.Expr | float],
    ) -> FourVector:
        """Physical four-momentum ``p^mu = m gamma (c, v)``; on shell ``p.p = -(m c)^2``."""

        four_velocity = self.four_velocity_from_velocity(velocity)
        return FourVector(
            tuple(self.mass * component for component in four_velocity.components),
            variance=CONTRAVARIANT,
        )

    def lorentz_factor(self, velocity: Sequence[sp.Expr | float]) -> sp.Expr:
        """The Lorentz factor ``gamma = 1 / sqrt(1 - |v|^2 / c^2)``."""

        spatial = sp.Matrix(list(velocity))
        speed_squared = (spatial.T * spatial)[0, 0]
        return 1 / sp.sqrt(1 - speed_squared / self.light_speed**2)

    def first_order_system(
        self,
        four_acceleration: Sequence[sp.Expr | float] | None = None,
    ) -> FirstOrderSystem:
        """Reduce the worldline to a first-order system in ``(x^mu, u^mu)``.

        The independent variable is the proper time ``tau``:
        ``dx^mu/dtau = u^mu`` and ``du^mu/dtau = a^mu``. With
        ``four_acceleration=None`` the particle is free (``a^mu = 0``, a straight
        Minkowski geodesic).
        """

        dimension = self.dimension
        coordinates = self.coordinates
        velocities = self.four_velocity_symbols
        if four_acceleration is None:
            acceleration: tuple[sp.Expr, ...] = tuple(
                sp.Integer(0) for _ in range(dimension)
            )
        else:
            acceleration = tuple(sp.sympify(component) for component in four_acceleration)
            if len(acceleration) != dimension:
                raise ValueError(
                    f"four_acceleration must have {dimension} components"
                )
        state = (*coordinates, *velocities)
        rhs = (*velocities, *acceleration)
        allowed = {self.proper_time, *state}
        free_symbols: set[sp.Symbol] = set().union(
            *(expression.free_symbols for expression in rhs)
        )
        parameters = tuple(
            sorted(free_symbols - allowed, key=lambda symbol: symbol.name)
        )
        return FirstOrderSystem(
            state=state,
            rhs=rhs,
            parameters=parameters,
            time=self.proper_time,
        )


__all__ = [
    "ProperTimeWorldline",
]
