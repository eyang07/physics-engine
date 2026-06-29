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

import numpy as np
import sympy as sp

from engine.dynamics.first_order import FirstOrderSystem
from engine.mechanics.coordinates import momentum_symbol, velocity_symbol
from engine.relativity.four_vectors import CONTRAVARIANT, FourVector
from engine.relativity.minkowski import MinkowskiMetric
from engine.verification.ir import AssumptionSpec
from engine.verification.sympy_codec import expression_spec


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

    @property
    def four_momentum_symbols(self) -> tuple[sp.Symbol, ...]:
        """Four-momentum component symbols ``p^mu``."""

        return tuple(momentum_symbol(coordinate) for coordinate in self.coordinates)

    def four_velocity(self) -> FourVector:
        """The four-velocity ``u^mu`` as a contravariant :class:`FourVector` of symbols."""

        return FourVector(self.four_velocity_symbols, variance=CONTRAVARIANT)

    def four_momentum(self) -> FourVector:
        """The four-momentum ``p^mu = m u^mu`` as a contravariant :class:`FourVector`."""

        return FourVector(
            tuple(self.mass * u for u in self.four_velocity_symbols),
            variance=CONTRAVARIANT,
        )

    def symbolic_four_momentum(self) -> FourVector:
        """The symbolic state momentum ``p^mu`` as a contravariant four-vector."""

        return FourVector(self.four_momentum_symbols, variance=CONTRAVARIANT)

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
        if spatial.shape[0] != self.dimension - 1:
            raise ValueError(
                f"velocity must have {self.dimension - 1} spatial components"
            )
        speed_squared = (spatial.T * spatial)[0, 0]
        return 1 / sp.sqrt(1 - speed_squared / self.light_speed**2)

    def mass_shell_expression(
        self,
        momentum: Sequence[sp.Expr | float] | FourVector | None = None,
    ) -> sp.Expr:
        """Return ``p^mu p_mu + m^2 c^2`` for the supplied or symbolic momentum."""

        if momentum is None:
            vector = self.symbolic_four_momentum()
        elif isinstance(momentum, FourVector):
            vector = momentum
            if vector.dimension != self.dimension:
                raise ValueError("four-momentum dimension must match the worldline")
            if not vector.is_contravariant:
                vector = vector.raise_index()
        else:
            components = tuple(sp.sympify(component) for component in momentum)
            if len(components) != self.dimension:
                raise ValueError(
                    f"four-momentum must have {self.dimension} components"
                )
            vector = FourVector(components, variance=CONTRAVARIANT)
        return sp.simplify(vector.norm_squared() + (self.mass * self.light_speed) ** 2)

    def mass_shell_assumption(self) -> AssumptionSpec:
        """Record the mass shell as an external verifier assumption."""

        expression = self.mass_shell_expression()
        return AssumptionSpec(
            id="mass-shell",
            name="Mass shell",
            expression=expression_spec(expression),
            comparison="=",
            rhs=0.0,
            variables=tuple(
                symbol.name for symbol in sorted(expression.free_symbols, key=lambda s: s.name)
            ),
            role="model",
            description=(
                "Relativistic on-shell condition p^mu p_mu + m^2 c^2 = 0; "
                "recorded as an assumption for external discharge, not proved by rollout."
            ),
        )

    def mass_shell_series(
        self,
        states: Sequence[Sequence[float]],
        *,
        mass: float | None = None,
        light_speed: float | None = None,
    ) -> list[float]:
        """Sample ``p^mu p_mu + m^2 c^2`` from ``(x^mu, p^mu)`` states."""

        state_array = np.asarray(states, dtype=float)
        if state_array.ndim != 2 or state_array.shape[1] != 2 * self.dimension:
            raise ValueError(
                f"states must have shape (sample_count, {2 * self.dimension})"
            )
        mass_value = float(sp.N(self.mass if mass is None else mass))
        light_speed_value = float(sp.N(self.light_speed if light_speed is None else light_speed))
        momenta = state_array[:, self.dimension:]
        values = (
            -momenta[:, 0] ** 2
            + np.sum(momenta[:, 1:] ** 2, axis=1)
            + (mass_value * light_speed_value) ** 2
        )
        return values.astype(float).tolist()

    def four_force_from_spatial_force(
        self,
        velocity: Sequence[sp.Expr | float],
        spatial_force: Sequence[sp.Expr | float],
    ) -> FourVector:
        """Build the four-force from a coordinate spatial force ``F = dp/dt``.

        With ``x^0 = c t`` the components are
        ``f^0 = gamma (F . v) / c`` and ``f^i = gamma F^i``. The resulting
        four-force is orthogonal to the four-velocity, so it preserves the mass
        shell when integrated exactly.
        """

        spatial_velocity = sp.Matrix(list(velocity))
        force = sp.Matrix(list(spatial_force))
        if spatial_velocity.shape[0] != self.dimension - 1:
            raise ValueError(
                f"velocity must have {self.dimension - 1} spatial components"
            )
        if force.shape[0] != self.dimension - 1:
            raise ValueError(
                f"spatial_force must have {self.dimension - 1} components"
            )
        gamma = self.lorentz_factor(tuple(spatial_velocity))
        power = (force.T * spatial_velocity)[0, 0]
        components = (
            sp.simplify(gamma * power / self.light_speed),
            *(sp.simplify(gamma * force[index]) for index in range(force.shape[0])),
        )
        return FourVector(components, variance=CONTRAVARIANT)

    def coordinate_momentum_derivative_from_four_force(
        self,
        velocity: Sequence[sp.Expr | float],
        four_force: Sequence[sp.Expr | float] | FourVector,
    ) -> tuple[sp.Expr, ...]:
        """Convert ``dp^mu/dtau = f^mu`` to spatial ``dp^i/dt`` components."""

        force = four_force if isinstance(four_force, FourVector) else FourVector(
            tuple(sp.sympify(component) for component in four_force),
            variance=CONTRAVARIANT,
        )
        if force.dimension != self.dimension:
            raise ValueError("four-force dimension must match the worldline")
        gamma = self.lorentz_factor(velocity)
        return tuple(sp.simplify(component / gamma) for component in force.components[1:])

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

    def momentum_dynamics(
        self,
        four_force: Sequence[sp.Expr | float] | FourVector,
    ) -> FirstOrderSystem:
        """Return proper-time dynamics ``dx^mu/dtau = p^mu/m``, ``dp^mu/dtau = f^mu``."""

        if isinstance(four_force, FourVector):
            if four_force.dimension != self.dimension:
                raise ValueError("four-force dimension must match the worldline")
            if not four_force.is_contravariant:
                four_force = four_force.raise_index()
            force = four_force.components
        else:
            force = tuple(sp.sympify(component) for component in four_force)
            if len(force) != self.dimension:
                raise ValueError(f"four_force must have {self.dimension} components")

        coordinates = self.coordinates
        momenta = self.four_momentum_symbols
        mass = sp.sympify(self.mass)
        state = (*coordinates, *momenta)
        rhs = (*(sp.simplify(momentum / mass) for momentum in momenta), *force)
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
