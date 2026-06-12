"""SymPy expression encoding for the verification IR."""

from __future__ import annotations

import sympy as sp

from engine.verification.ir import ExpressionSpec

SYMPY_SREPR_FORMAT = "sympy-srepr"


def expression_spec(expression: sp.Expr) -> ExpressionSpec:
    expr = sp.sympify(expression)
    return ExpressionSpec(
        format=SYMPY_SREPR_FORMAT,
        source=sp.srepr(expr),
        display=str(expr),
        latex=sp.latex(expr),
    )
