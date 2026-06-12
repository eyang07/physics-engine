"""Candidate-certificate generation helpers.

Generators *propose* candidates from standard constructions: quadratic
Lyapunov functions from a Hurwitz linearization (via the Lyapunov equation
``A^T P + P A = -Q``) and sublevel barrier candidates from Lyapunov
candidates. Every output is a candidate carrying its proof obligations;
nothing here certifies, and level suggestions are measured evidence only.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

import numpy as np
import sympy as sp
from scipy.linalg import solve_continuous_lyapunov

from engine.dynamics.first_order import FirstOrderSystem
from engine.dynamics.safety import (
    BarrierCandidate,
    LyapunovCandidate,
    SublevelSet,
    _evaluator,
    grid_points,
)

_MEASURED_INFIMUM_NOTE = (
    "measured grid minimum only: a true infimum may be lower; "
    "use as a level suggestion, not a bound"
)


def quadratic_lyapunov_from_linearization(
    system: FirstOrderSystem,
    equilibrium: Sequence[float],
    *,
    substitutions: Mapping[sp.Symbol, float] | None = None,
    q: np.ndarray | Sequence[Sequence[float]] | None = None,
    domain: SublevelSet | None = None,
    name: str = "linearization-lyapunov",
    equilibrium_tolerance: float = 1e-9,
) -> LyapunovCandidate:
    """Propose ``V = (x - x*)^T P (x - x*)`` with ``A^T P + P A = -Q``.

    The construction is justified only near a Hurwitz equilibrium of the
    (closed-loop) system, so a non-equilibrium point or a linearization
    with an eigenvalue real part ``>= 0`` raises. The result is still a
    *candidate*: its obligations quantify over the full domain and require
    external discharge like any hand-written candidate.
    """

    if len(equilibrium) != len(system.state):
        raise ValueError("equilibrium must match the state dimension")
    equilibrium_values = tuple(float(value) for value in equilibrium)
    point = {
        symbol: sp.Float(value)
        for symbol, value in zip(system.state, equilibrium_values, strict=True)
    }

    replacements = {**dict(substitutions or {}), **point}
    for expression in system.rhs:
        resolved = sp.sympify(expression).subs(replacements)
        unresolved = resolved.free_symbols
        if unresolved:
            names = ", ".join(sorted(symbol.name for symbol in unresolved))
            raise ValueError(f"unresolved symbols at the equilibrium: {names}")
        if abs(float(resolved)) > equilibrium_tolerance:
            raise ValueError(
                f"point is not an equilibrium: |f| = {abs(float(resolved)):.3e}"
            )

    jacobian = system.linearization(point, substitutions)
    if jacobian.free_symbols:
        names = ", ".join(sorted(symbol.name for symbol in jacobian.free_symbols))
        raise ValueError(f"unresolved symbols in the linearization: {names}")
    a_matrix = np.array(jacobian, dtype=float)

    max_real_part = float(np.max(np.real(np.linalg.eigvals(a_matrix))))
    if max_real_part >= 0.0:
        raise ValueError(
            "linearization is not Hurwitz "
            f"(max eigenvalue real part = {max_real_part:.3e}); "
            "the quadratic construction is not justified"
        )

    dimension = len(system.state)
    if q is None:
        q_matrix = np.eye(dimension)
    else:
        q_matrix = np.asarray(q, dtype=float)
        if q_matrix.shape != (dimension, dimension):
            raise ValueError("q must be a square matrix over the state dimension")
        if not np.allclose(q_matrix, q_matrix.T):
            raise ValueError("q must be symmetric")
        try:
            np.linalg.cholesky(q_matrix)
        except np.linalg.LinAlgError as error:
            raise ValueError("q must be positive definite") from error

    p_matrix = solve_continuous_lyapunov(a_matrix.T, -q_matrix)
    p_matrix = (p_matrix + p_matrix.T) / 2.0
    try:
        np.linalg.cholesky(p_matrix)
    except np.linalg.LinAlgError as error:
        raise ValueError("solved P is not positive definite") from error

    deltas = tuple(
        symbol - sp.Float(value)
        for symbol, value in zip(system.state, equilibrium_values, strict=True)
    )
    function = sp.expand(
        sum(
            sp.Float(p_matrix[row, column]) * deltas[row] * deltas[column]
            for row in range(dimension)
            for column in range(dimension)
        )
    )

    return LyapunovCandidate(
        state=system.state,
        function=function,
        equilibrium=equilibrium_values,
        domain=domain,
        name=name,
    )


def barrier_from_lyapunov(
    candidate: LyapunovCandidate,
    level: float,
    *,
    name: str | None = None,
) -> BarrierCandidate:
    """Propose the sublevel barrier ``B = V - level`` from a Lyapunov candidate.

    The candidate-invariant region is ``{V <= level}``; ``level`` must be
    positive so the region contains the equilibrium where ``V`` vanishes.
    """

    if level <= 0.0:
        raise ValueError("level must be positive so the region contains the equilibrium")
    return BarrierCandidate(
        state=candidate.state,
        function=sp.sympify(candidate.function) - sp.Float(level),
        name=name or f"{candidate.name}:sublevel-barrier",
    )


@dataclass(frozen=True)
class MeasuredInfimum:
    """Grid minimum of a function over a region; measured evidence only."""

    value: float
    witness_point: tuple[float, ...]
    sample_count: int
    rigor: str = "measured"
    note: str = _MEASURED_INFIMUM_NOTE

    def __post_init__(self) -> None:
        if self.rigor != "measured":
            raise ValueError("grid minima are measured evidence only")


def measured_infimum_over_set(
    function: sp.Expr,
    region: SublevelSet,
    *,
    bounds: Sequence[tuple[float, float]],
    counts: Sequence[int],
    substitutions: Mapping[sp.Symbol, float] | None = None,
) -> MeasuredInfimum:
    """Measured minimum of ``function`` over grid samples inside ``region``.

    Intended for level suggestions: a barrier ``B = V - level`` with
    ``level`` below the measured infimum of ``V`` over an unsafe set keeps
    the unsafe-exclusion obligation satisfied *on these samples*. The true
    infimum may be lower; the obligation still requires external discharge.
    """

    points = grid_points(bounds, counts)
    inside = points[region.margin(points, substitutions) >= 0.0]
    if inside.shape[0] == 0:
        raise ValueError("no sample points fall inside the region")

    values = _evaluator(region.state, function, substitutions)(inside)
    worst_index = int(np.argmin(values))
    return MeasuredInfimum(
        value=float(values[worst_index]),
        witness_point=tuple(float(value) for value in inside[worst_index]),
        sample_count=int(inside.shape[0]),
    )
