from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

import sympy as sp

from engine.mechanics.coordinates import velocity_symbol
from engine.mechanics.lagrangian import LagrangianSystem, total_time_derivative


@dataclass(frozen=True)
class CoordinateMap:
    """A coordinate substitution from old coordinates into new coordinates."""

    mapping: Mapping[sp.Symbol, sp.Expr]
    new_coordinates: tuple[sp.Symbol, ...]
    time: sp.Symbol = sp.Symbol("t", real=True)
    new_velocities: tuple[sp.Symbol, ...] | None = None

    @property
    def qdot_new(self) -> tuple[sp.Symbol, ...]:
        if self.new_velocities is None:
            return tuple(velocity_symbol(q) for q in self.new_coordinates)
        return self.new_velocities


def pushforward_velocities(
    old_coordinates: Sequence[sp.Symbol],
    new_coordinates: Sequence[sp.Symbol],
    coordinate_map: Mapping[sp.Symbol, sp.Expr],
    *,
    time: sp.Symbol = sp.Symbol("t", real=True),
    old_velocities: Sequence[sp.Symbol] | None = None,
    new_velocities: Sequence[sp.Symbol] | None = None,
) -> dict[sp.Symbol, sp.Expr]:
    """Return the tangent map components old_qdot = D_t(old_q(new_q, t))."""

    old_velocities = tuple(old_velocities or tuple(velocity_symbol(q) for q in old_coordinates))
    new_coordinates = tuple(new_coordinates)
    new_velocities = tuple(new_velocities or tuple(velocity_symbol(q) for q in new_coordinates))

    pushforward: dict[sp.Symbol, sp.Expr] = {}
    for old_q, old_v in zip(old_coordinates, old_velocities, strict=True):
        if old_q not in coordinate_map:
            raise KeyError(f"missing coordinate map for {old_q}")
        pushforward[old_v] = total_time_derivative(
            coordinate_map[old_q],
            new_coordinates,
            new_velocities,
            time,
        )
    return pushforward


def pullback_momenta(
    old_momenta: Sequence[sp.Symbol],
    old_coordinates: Sequence[sp.Symbol],
    new_coordinates: Sequence[sp.Symbol],
    coordinate_map: Mapping[sp.Symbol, sp.Expr],
) -> tuple[sp.Expr, ...]:
    """Pull back covector components under old_q = f(new_q).

    If alpha = sum_i p_i d old_q_i, then the pulled-back components are
    P_a = sum_i p_i partial(old_q_i) / partial(new_q_a).
    """

    if len(old_momenta) != len(old_coordinates):
        raise ValueError("old_momenta must match old_coordinates")

    return tuple(
        sp.simplify(
            sum(
                old_p * sp.diff(coordinate_map[old_q], new_q)
                for old_p, old_q in zip(old_momenta, old_coordinates, strict=True)
            )
        )
        for new_q in new_coordinates
    )


def pullback_lagrangian(
    lagrangian: sp.Expr,
    old_coordinates: Sequence[sp.Symbol],
    new_coordinates: Sequence[sp.Symbol],
    coordinate_map: Mapping[sp.Symbol, sp.Expr],
    *,
    time: sp.Symbol = sp.Symbol("t", real=True),
    old_velocities: Sequence[sp.Symbol] | None = None,
    new_velocities: Sequence[sp.Symbol] | None = None,
) -> sp.Expr:
    """Rewrite L(old q, old qdot, t) in new coordinates.

    Velocities are transformed by the chain rule:
    old_qdot_i = D_t(old_q_i(new_q, t)).
    """

    old_velocities = tuple(old_velocities or tuple(velocity_symbol(q) for q in old_coordinates))
    new_coordinates = tuple(new_coordinates)
    new_velocities = tuple(new_velocities or tuple(velocity_symbol(q) for q in new_coordinates))

    substitutions: dict[sp.Symbol, sp.Expr] = {}
    for old_q in old_coordinates:
        if old_q not in coordinate_map:
            raise KeyError(f"missing coordinate map for {old_q}")
        substitutions[old_q] = coordinate_map[old_q]

    substitutions.update(
        pushforward_velocities(
            old_coordinates,
            new_coordinates,
            coordinate_map,
            time=time,
            old_velocities=old_velocities,
            new_velocities=new_velocities,
        )
    )

    return sp.simplify(lagrangian.subs(substitutions))


def transform_system(
    system: LagrangianSystem,
    new_coordinates: Sequence[sp.Symbol],
    coordinate_map: Mapping[sp.Symbol, sp.Expr],
    *,
    new_velocities: Sequence[sp.Symbol] | None = None,
) -> LagrangianSystem:
    pulled_back = pullback_lagrangian(
        system.lagrangian,
        system.q,
        tuple(new_coordinates),
        coordinate_map,
        time=system.time,
        old_velocities=system.qdot,
        new_velocities=new_velocities,
    )
    return LagrangianSystem(
        coordinates=tuple(new_coordinates),
        velocities=tuple(new_velocities) if new_velocities is not None else None,
        lagrangian=pulled_back,
        time=system.time,
    )
