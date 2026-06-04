from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

import sympy as sp

from engine.mechanics.lagrangian import LagrangianSystem, total_time_derivative


@dataclass(frozen=True)
class InfinitesimalSymmetry:
    """Infinitesimal transformation delta t = tau, delta q_i = eta_i."""

    eta: Mapping[sp.Symbol, sp.Expr]
    tau: sp.Expr = sp.Integer(0)
    gauge: sp.Expr = sp.Integer(0)

    @classmethod
    def vertical(
        cls,
        coordinates: Sequence[sp.Symbol],
        components: Sequence[sp.Expr],
        gauge: sp.Expr = sp.Integer(0),
    ) -> "InfinitesimalSymmetry":
        return cls(dict(zip(coordinates, components, strict=True)), sp.Integer(0), gauge)


def noether_residual(system: LagrangianSystem, symmetry: InfinitesimalSymmetry) -> sp.Expr:
    """Return pr(X)(L) + L D_t(tau) - D_t(F).

    A zero residual means the transformation is a variational symmetry with
    gauge term F.
    """

    tau_dt = total_time_derivative(symmetry.tau, system.q, system.qdot, system.time)
    result = symmetry.tau * sp.diff(system.lagrangian, system.time)
    result += system.lagrangian * tau_dt

    for q, v in zip(system.q, system.qdot, strict=True):
        eta = symmetry.eta.get(q, sp.Integer(0))
        eta_dt = total_time_derivative(eta, system.q, system.qdot, system.time)
        prolonged_velocity = eta_dt - v * tau_dt
        result += eta * sp.diff(system.lagrangian, q)
        result += prolonged_velocity * sp.diff(system.lagrangian, v)

    gauge_dt = total_time_derivative(symmetry.gauge, system.q, system.qdot, system.time)
    return sp.simplify(result - gauge_dt)


def is_variational_symmetry(system: LagrangianSystem, symmetry: InfinitesimalSymmetry) -> bool:
    return sp.simplify(noether_residual(system, symmetry)) == 0


def noether_charge(system: LagrangianSystem, symmetry: InfinitesimalSymmetry) -> sp.Expr:
    """Return Q = sum p_i eta_i - H tau - F."""

    energy = system.energy()
    momenta = system.generalized_momenta()
    charge = sum(
        p * symmetry.eta.get(q, sp.Integer(0))
        for q, p in zip(system.q, momenta, strict=True)
    )
    charge -= energy * symmetry.tau
    charge -= symmetry.gauge
    return sp.simplify(charge)

