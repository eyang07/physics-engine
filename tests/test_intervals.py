"""Tests for exact-rational interval arithmetic (BE-063).

The soundness contract is the enclosure property: for every supported
operation, the value at any concrete point inside the input intervals lies
inside the computed result interval. These tests verify that property by
sampling concrete rational points and comparing against an exact
``fractions.Fraction`` reference, with no floating point anywhere.
"""

from __future__ import annotations

import random
from fractions import Fraction

import pytest
import sympy as sp

from engine.numerics import Interval, interval_abs, interval_max, interval_min


def _frac(value: sp.Rational) -> Fraction:
    return Fraction(int(value.p), int(value.q))


def _sample(interval: Interval, rng: random.Random) -> Fraction:
    """A uniformly chosen rational point inside ``interval``."""

    lo = _frac(interval.lower)
    hi = _frac(interval.upper)
    t = Fraction(rng.randint(0, 1000), 1000)
    return lo + t * (hi - lo)


def _random_interval(rng: random.Random) -> Interval:
    a = Fraction(rng.randint(-40, 40), rng.randint(1, 12))
    b = Fraction(rng.randint(-40, 40), rng.randint(1, 12))
    lo, hi = (a, b) if a <= b else (b, a)
    return Interval(lo, hi)


# -- construction and validation -----------------------------------------


def test_endpoints_are_exact_rationals() -> None:
    iv = Interval(Fraction(1, 3), "5/2")
    assert isinstance(iv.lower, sp.Rational)
    assert isinstance(iv.upper, sp.Rational)
    assert iv.lower == sp.Rational(1, 3)
    assert iv.upper == sp.Rational(5, 2)
    assert iv.width == sp.Rational(5, 2) - sp.Rational(1, 3)


def test_floats_are_rejected() -> None:
    with pytest.raises(TypeError):
        Interval(0.1, 1)
    with pytest.raises(TypeError):
        Interval.point(0.2)


def test_bool_is_rejected() -> None:
    with pytest.raises(TypeError):
        Interval(True, 1)


def test_inverted_bounds_rejected() -> None:
    with pytest.raises(ValueError):
        Interval(2, 1)


def test_point_and_contains() -> None:
    p = Interval.point(Fraction(3, 4))
    assert p.lower == p.upper == sp.Rational(3, 4)
    iv = Interval(-1, 2)
    assert iv.contains(0)
    assert Fraction(3, 2) in iv
    assert not iv.contains(3)


def test_even_power_straddling_zero_encloses_to_zero_max() -> None:
    iv = Interval(-2, 3)
    sq = iv**2
    assert sq.lower == 0
    assert sq.upper == 9  # max(4, 9)
    quartic = Interval(-3, 2) ** 4
    assert quartic.lower == 0
    assert quartic.upper == 81  # max(81, 16)


def test_even_power_away_from_zero_is_tight() -> None:
    assert (Interval(2, 3) ** 2) == Interval(4, 9)
    assert (Interval(-3, -2) ** 2) == Interval(4, 9)


def test_odd_power_is_monotonic() -> None:
    assert (Interval(-2, 3) ** 3) == Interval(-8, 27)


def test_zero_power_is_unit() -> None:
    assert (Interval(-5, 7) ** 0) == Interval(1, 1)


def test_reciprocal_requires_nonzero() -> None:
    with pytest.raises(ZeroDivisionError):
        Interval(-1, 2).reciprocal()
    with pytest.raises(ZeroDivisionError):
        Interval(0, 2) ** -1
    assert Interval(1, 2).reciprocal() == Interval(sp.Rational(1, 2), 1)


def test_negative_power() -> None:
    assert (Interval(1, 2) ** -2) == Interval(sp.Rational(1, 4), 1)


def test_scalar_operands_are_coerced() -> None:
    assert (Interval(1, 2) + 3) == Interval(4, 5)
    assert (3 + Interval(1, 2)) == Interval(4, 5)
    assert (10 - Interval(1, 2)) == Interval(8, 9)
    assert (2 * Interval(1, 3)) == Interval(2, 6)


def test_exponent_must_be_plain_int() -> None:
    with pytest.raises(TypeError):
        Interval(1, 2) ** 1.5  # type: ignore[operator]
    with pytest.raises(TypeError):
        Interval(1, 2) ** True


# -- enclosure property tests (the backstop) -----------------------------

_SAMPLES_PER_OP = 60
_TRIALS = 200


def test_add_encloses() -> None:
    rng = random.Random(1)
    for _ in range(_TRIALS):
        a, b = _random_interval(rng), _random_interval(rng)
        result = a + b
        for _ in range(_SAMPLES_PER_OP):
            x, y = _sample(a, rng), _sample(b, rng)
            value = x + y
            assert _frac(result.lower) <= value <= _frac(result.upper)


def test_sub_encloses() -> None:
    rng = random.Random(2)
    for _ in range(_TRIALS):
        a, b = _random_interval(rng), _random_interval(rng)
        result = a - b
        for _ in range(_SAMPLES_PER_OP):
            x, y = _sample(a, rng), _sample(b, rng)
            value = x - y
            assert _frac(result.lower) <= value <= _frac(result.upper)


def test_mul_encloses() -> None:
    rng = random.Random(3)
    for _ in range(_TRIALS):
        a, b = _random_interval(rng), _random_interval(rng)
        result = a * b
        for _ in range(_SAMPLES_PER_OP):
            x, y = _sample(a, rng), _sample(b, rng)
            value = x * y
            assert _frac(result.lower) <= value <= _frac(result.upper)


def test_pow_encloses() -> None:
    rng = random.Random(4)
    for exponent in range(0, 6):
        for _ in range(_TRIALS):
            a = _random_interval(rng)
            result = a**exponent
            for _ in range(_SAMPLES_PER_OP):
                x = _sample(a, rng)
                value = x**exponent
                assert _frac(result.lower) <= value <= _frac(result.upper)


def test_negative_pow_encloses() -> None:
    rng = random.Random(5)
    for exponent in (-1, -2, -3):
        for _ in range(_TRIALS):
            # build an interval that avoids zero
            lo = Fraction(rng.randint(1, 30), rng.randint(1, 8))
            hi = lo + Fraction(rng.randint(0, 30), rng.randint(1, 8))
            a = Interval(lo, hi)
            if rng.random() < 0.5:
                a = -a
            result = a**exponent
            for _ in range(_SAMPLES_PER_OP):
                x = _sample(a, rng)
                value = x**exponent
                assert _frac(result.lower) <= value <= _frac(result.upper)


def test_abs_encloses() -> None:
    rng = random.Random(6)
    for _ in range(_TRIALS):
        a = _random_interval(rng)
        result = interval_abs(a)
        assert result == abs(a)
        for _ in range(_SAMPLES_PER_OP):
            x = _sample(a, rng)
            value = abs(x)
            assert _frac(result.lower) <= value <= _frac(result.upper)


def test_max_min_enclose() -> None:
    rng = random.Random(7)
    for _ in range(_TRIALS):
        a, b, c = (_random_interval(rng) for _ in range(3))
        mx = interval_max(a, b, c)
        mn = interval_min(a, b, c)
        for _ in range(_SAMPLES_PER_OP):
            x, y, z = _sample(a, rng), _sample(b, rng), _sample(c, rng)
            assert _frac(mn.lower) <= min(x, y, z) <= _frac(mn.upper)
            assert _frac(mx.lower) <= max(x, y, z) <= _frac(mx.upper)


def test_compound_expression_encloses() -> None:
    """A small obligation-like polynomial: (x - y)**2 + 3*x*y - |x|."""

    rng = random.Random(8)
    for _ in range(_TRIALS):
        a, b = _random_interval(rng), _random_interval(rng)
        result = (a - b) ** 2 + 3 * (a * b) - interval_abs(a)
        for _ in range(_SAMPLES_PER_OP):
            x, y = _sample(a, rng), _sample(b, rng)
            value = (x - y) ** 2 + 3 * x * y - abs(x)
            assert _frac(result.lower) <= value <= _frac(result.upper)


def test_max_min_require_arguments() -> None:
    with pytest.raises(ValueError):
        interval_max()
    with pytest.raises(ValueError):
        interval_min()
