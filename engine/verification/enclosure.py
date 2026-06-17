"""Fail-closed interval enclosure of verification-IR expressions.

This is the symbolic-to-interval lowering step of the level-2 (certified-numeric)
reachability lane. Given an IR :class:`~engine.verification.ir.ExpressionSpec`
(or a decoded SymPy expression) and a *box* assigning each free symbol an
:class:`~engine.numerics.intervals.Interval`, it returns a sound enclosure of
the expression over that box.

Soundness rests on two disciplines:

- **Whitelisted nodes only.** Each handled node type has a proven-enclosing
  interval handler (``Add`` / ``Mul`` / ``Pow`` with an integer or ``1/2``
  exponent / ``Rational`` / ``Integer`` / ``Abs`` / ``Max`` / ``Min``). Any
  other node — a transcendental function, a symbolic exponent, an unknown
  symbol, or a floating-point literal — raises
  :class:`UnsupportedExpressionError` rather than returning a possibly-unsound
  value. *Fail closed.*
- **Exact rational core, mpmath only at ``sqrt``.** Polynomial obligations stay
  in exact rational interval arithmetic with no rounding; only the ``sqrt``
  node (``Pow`` with exponent ``1/2``) touches the outward-rounded mpmath
  layer. Floating-point literals are rejected so no silent rounding enters.

The evaluator computes sound enclosures under stated assumptions; it never
claims proof or certification.
"""

from __future__ import annotations

from typing import Mapping

import sympy as sp

from engine.numerics.intervals import (
    Interval,
    interval_abs,
    interval_max,
    interval_min,
    interval_sqrt,
)
from engine.verification.ir import ExpressionSpec
from engine.verification.sympy_codec import SYMPY_SREPR_FORMAT

_HALF = sp.Rational(1, 2)


class UnsupportedExpressionError(TypeError):
    """Raised when an expression node has no proven-enclosing handler.

    The lane fails closed: an unsupported node aborts the enclosure rather than
    risking an unsound result.
    """


def decode_expression(spec: ExpressionSpec) -> sp.Expr:
    """Decode an :class:`ExpressionSpec` back into a SymPy expression.

    Only the ``sympy-srepr`` transport format is accepted; any other format
    raises rather than guessing how to parse it.
    """

    if spec.format != SYMPY_SREPR_FORMAT:
        raise UnsupportedExpressionError(
            f"cannot decode expression format {spec.format!r}; expected "
            f"{SYMPY_SREPR_FORMAT!r}"
        )
    return sp.sympify(spec.source)


def enclose_expression(
    expression: ExpressionSpec | sp.Expr,
    box: Mapping[str, Interval],
) -> Interval:
    """Enclose ``expression`` over ``box`` (symbol name -> Interval).

    Raises :class:`UnsupportedExpressionError` on any non-whitelisted node or
    any free symbol absent from ``box``.
    """

    if isinstance(expression, ExpressionSpec):
        node = decode_expression(expression)
    else:
        node = sp.sympify(expression)
    return _enclose(node, box)


def _enclose(node: sp.Expr, box: Mapping[str, Interval]) -> Interval:
    if isinstance(node, sp.Symbol):
        if node.name not in box:
            raise UnsupportedExpressionError(
                f"no interval supplied for symbol {node.name!r}"
            )
        return Interval._coerce(box[node.name])

    # Rational covers Integer, Half, Zero, One, NegativeOne, ...
    if isinstance(node, sp.Rational):
        return Interval.point(node)

    # Floats would require silent rounding; the exact-rational core forbids it.
    if isinstance(node, sp.Float):
        raise UnsupportedExpressionError(
            f"floating-point literal {node!r} is not allowed; the enclosure "
            "core is exact-rational"
        )

    if isinstance(node, sp.Add):
        result = Interval.point(0)
        for arg in node.args:
            result = result + _enclose(arg, box)
        return result

    if isinstance(node, sp.Mul):
        result = Interval.point(1)
        for arg in node.args:
            result = result * _enclose(arg, box)
        return result

    if isinstance(node, sp.Pow):
        base, exponent = node.args
        base_interval = _enclose(base, box)
        if isinstance(exponent, sp.Integer):
            return base_interval ** int(exponent)
        if exponent == _HALF:
            return interval_sqrt(base_interval)
        raise UnsupportedExpressionError(
            f"unsupported exponent {exponent!r}; only integer powers and the "
            "1/2 (sqrt) exponent are handled"
        )

    if isinstance(node, sp.Abs):
        return interval_abs(_enclose(node.args[0], box))

    if isinstance(node, sp.Max):
        return interval_max(*(_enclose(arg, box) for arg in node.args))

    if isinstance(node, sp.Min):
        return interval_min(*(_enclose(arg, box) for arg in node.args))

    raise UnsupportedExpressionError(
        f"unsupported expression node {type(node).__name__}: {node!r}"
    )


__all__ = [
    "UnsupportedExpressionError",
    "decode_expression",
    "enclose_expression",
]
