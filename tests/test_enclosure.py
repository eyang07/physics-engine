"""Tests for fail-closed IR expression enclosure (BE-065).

The contract is the containment property: for any concrete point inside the
box, the expression's value lies inside the computed enclosure. These tests
verify that by sampling obligation-like expressions over their boxes and
comparing against an exact ``Fraction`` reference (float-free), plus the
fail-closed behaviour: unsupported nodes, unknown symbols, and float literals
all raise.
"""

from __future__ import annotations

import random
from fractions import Fraction

import pytest
import sympy as sp

from engine.numerics import Interval
from engine.verification import (
    UnsupportedExpressionError,
    enclose_expression,
    expression_spec,
)


def _frac(value: sp.Rational) -> Fraction:
    return Fraction(int(value.p), int(value.q))


def _sample(interval: Interval, rng: random.Random) -> Fraction:
    lo, hi = _frac(interval.lower), _frac(interval.upper)
    t = Fraction(rng.randint(0, 1000), 1000)
    return lo + t * (hi - lo)


# -- decoding and basic enclosure ----------------------------------------


def test_round_trips_through_expression_spec() -> None:
    x, y = sp.symbols("x y", real=True)
    spec = expression_spec(x**2 + 3 * x * y)
    box = {"x": Interval(1, 2), "y": Interval(-1, 1)}
    result = enclose_expression(spec, box)
    # x**2 in [1,4]; 3xy in [-6,6] -> [-5, 10]
    assert result == Interval(-5, 10)


def test_accepts_decoded_sympy_expression() -> None:
    x = sp.Symbol("x", real=True)
    result = enclose_expression(x + 1, {"x": Interval(0, 2)})
    assert result == Interval(1, 3)


def test_whitelisted_nodes_lower() -> None:
    x, y = sp.symbols("x y", real=True)
    box = {"x": Interval(-2, 3), "y": Interval(1, 4)}
    # exercise Add, Mul, Pow[int], Abs, Max, Min, sqrt, Rational
    expr = sp.Max(sp.Abs(x), y) - sp.Min(x, y) + sp.Rational(1, 2)
    enclose_expression(expr, box)  # must not raise
    sqrt_expr = sp.sqrt(x**2 + y**2)
    radius = enclose_expression(sqrt_expr, box)
    assert radius.lower * radius.lower <= 1  # min of x^2+y^2 is >=1 (y>=1)


# -- fail-closed behaviour -----------------------------------------------


def test_unsupported_function_raises() -> None:
    x = sp.Symbol("x", real=True)
    with pytest.raises(UnsupportedExpressionError):
        enclose_expression(sp.sin(x), {"x": Interval(0, 1)})


def test_unknown_symbol_raises() -> None:
    x, y = sp.symbols("x y", real=True)
    with pytest.raises(UnsupportedExpressionError):
        enclose_expression(x + y, {"x": Interval(0, 1)})


def test_float_literal_raises() -> None:
    x = sp.Symbol("x", real=True)
    with pytest.raises(UnsupportedExpressionError):
        enclose_expression(sp.Float("0.5") * x, {"x": Interval(0, 1)})


def test_symbolic_exponent_raises() -> None:
    x, n = sp.symbols("x n", real=True)
    with pytest.raises(UnsupportedExpressionError):
        enclose_expression(x**n, {"x": Interval(1, 2), "n": Interval(1, 2)})


def test_non_srepr_format_raises() -> None:
    from engine.verification.ir import ExpressionSpec

    spec = ExpressionSpec(format="latex", source="x", display="x", latex="x")
    with pytest.raises(UnsupportedExpressionError):
        enclose_expression(spec, {"x": Interval(0, 1)})


# -- containment property tests (the backstop) ---------------------------


def _eval_reference(
    expr: sp.Expr, point: dict[str, Fraction]
) -> Fraction:
    """Evaluate a polynomial expression exactly in Fraction arithmetic."""

    if isinstance(expr, sp.Symbol):
        return point[expr.name]
    if isinstance(expr, sp.Rational):
        return Fraction(int(expr.p), int(expr.q))
    if isinstance(expr, sp.Add):
        total = Fraction(0)
        for arg in expr.args:
            total += _eval_reference(arg, point)
        return total
    if isinstance(expr, sp.Mul):
        prod = Fraction(1)
        for arg in expr.args:
            prod *= _eval_reference(arg, point)
        return prod
    if isinstance(expr, sp.Pow):
        base, exp = expr.args
        return _eval_reference(base, point) ** int(exp)
    if isinstance(expr, sp.Abs):
        return abs(_eval_reference(expr.args[0], point))
    if isinstance(expr, sp.Max):
        return max(_eval_reference(a, point) for a in expr.args)
    if isinstance(expr, sp.Min):
        return min(_eval_reference(a, point) for a in expr.args)
    raise AssertionError(f"reference cannot evaluate {expr!r}")


def test_polynomial_obligation_encloses_samples() -> None:
    """Geofence-like one-step obligation forms over a box (no sqrt)."""

    x, v, dt = sp.symbols("x v dt", real=True)
    obligations = [
        # forward-invariance margin: qmax - (x + dt*v)
        sp.Rational(5) - (x + dt * v),
        # velocity bound margin: vmax**2 - v**2
        sp.Rational(9) - v**2,
        # signed margin with Abs and Max
        sp.Max(sp.Abs(x + dt * v), v) - sp.Rational(1, 2),
    ]
    rng = random.Random(21)
    boxes = [
        {"x": Interval(-4, 4), "v": Interval(-3, 3), "dt": Interval(sp.Rational(1, 10), sp.Rational(1, 10))},
        {"x": Interval(-2, 2), "v": Interval(-2, 5), "dt": Interval(0, sp.Rational(1, 4))},
    ]
    for expr in obligations:
        for base_box in boxes:
            box = {name: iv for name, iv in base_box.items() if sp.Symbol(name, real=True) in expr.free_symbols}
            result = enclose_expression(expr, box)
            # endpoints stay exact rational (no float crept in)
            assert isinstance(result.lower, sp.Rational)
            assert isinstance(result.upper, sp.Rational)
            for _ in range(80):
                point = {name: _sample(iv, rng) for name, iv in box.items()}
                value = _eval_reference(expr, point)
                assert _frac(result.lower) <= value <= _frac(result.upper)


def test_sqrt_obligation_encloses_samples() -> None:
    """A keep-out distance barrier rho - sqrt((x-cx)**2 + (y-cy)**2)."""

    x, y = sp.symbols("x y", real=True)
    expr = sp.Rational(2) - sp.sqrt((x - 1) ** 2 + (y - 1) ** 2)
    box = {"x": Interval(-3, 5), "y": Interval(-3, 5)}
    result = enclose_expression(expr, box)
    rng = random.Random(22)
    for _ in range(200):
        px, py = _sample(box["x"], rng), _sample(box["y"], rng)
        d2 = (px - 1) ** 2 + (py - 1) ** 2
        # value = 2 - sqrt(d2). Containment lower <= value <= upper is, since
        # sqrt(d2) >= 0, equivalent to:  2 - upper <= sqrt(d2) <= 2 - lower.
        lower_sqrt = 2 - _frac(result.upper)
        upper_sqrt = 2 - _frac(result.lower)
        # upper side: sqrt(d2) <= upper_sqrt  <=>  d2 <= upper_sqrt**2 (and >=0)
        assert upper_sqrt >= 0 and d2 <= upper_sqrt**2
        # lower side: sqrt(d2) >= lower_sqrt; trivially true when lower_sqrt <= 0
        if lower_sqrt > 0:
            assert d2 >= lower_sqrt**2
