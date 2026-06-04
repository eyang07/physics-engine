from __future__ import annotations

from typing import Sequence

import sympy as sp


def poisson_bracket(
    f: sp.Expr,
    g: sp.Expr,
    coordinates: Sequence[sp.Symbol],
    momenta: Sequence[sp.Symbol],
) -> sp.Expr:
    """Return the canonical Poisson bracket {f, g}.

    {f, g} = sum_i (df/dq_i dg/dp_i - df/dp_i dg/dq_i)
    """

    if len(coordinates) != len(momenta):
        raise ValueError("coordinates and momenta must have the same length")

    return sp.simplify(
        sum(
            sp.diff(f, q_i) * sp.diff(g, p_i)
            - sp.diff(f, p_i) * sp.diff(g, q_i)
            for q_i, p_i in zip(coordinates, momenta, strict=True)
        )
    )


def poisson_bracket_matrix(
    functions: Sequence[sp.Expr],
    coordinates: Sequence[sp.Symbol],
    momenta: Sequence[sp.Symbol],
) -> sp.Matrix:
    """Return the matrix with entries {f_i, f_j}."""

    return sp.Matrix(
        [
            [
                poisson_bracket(f_i, f_j, coordinates, momenta)
                for f_j in functions
            ]
            for f_i in functions
        ]
    )


def time_evolution(
    observable: sp.Expr,
    hamiltonian: sp.Expr,
    coordinates: Sequence[sp.Symbol],
    momenta: Sequence[sp.Symbol],
    *,
    time: sp.Symbol | None = None,
) -> sp.Expr:
    """Return d observable / dt = {observable, H} + partial_t observable."""

    explicit_time = sp.diff(observable, time) if time is not None else sp.Integer(0)
    return sp.simplify(
        poisson_bracket(observable, hamiltonian, coordinates, momenta) + explicit_time
    )


def is_conserved(
    observable: sp.Expr,
    hamiltonian: sp.Expr,
    coordinates: Sequence[sp.Symbol],
    momenta: Sequence[sp.Symbol],
    *,
    time: sp.Symbol | None = None,
) -> bool:
    return time_evolution(
        observable,
        hamiltonian,
        coordinates,
        momenta,
        time=time,
    ) == 0

