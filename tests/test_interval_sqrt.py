"""Tests for the mpmath outward-rounded sqrt layer (BE-064).

The soundness contract for ``sqrt`` is the enclosure property, verified two
ways: (1) exact rational squared-bound checks (``lower**2 <= x <= upper**2``),
which need no floating point at all, and (2) sampling against a high-precision
mpmath reference. The rational core must stay exact, and irrational constants
must enclose strictly outward (never inward).
"""

from __future__ import annotations

import random
from fractions import Fraction

import mpmath
import pytest
import sympy as sp

from engine.numerics import Interval, interval_sqrt, rational_sqrt_interval


def _frac(value: sp.Rational) -> Fraction:
    return Fraction(int(value.p), int(value.q))


# -- exact behaviour on perfect squares ----------------------------------


def test_perfect_squares_are_exact() -> None:
    assert rational_sqrt_interval(4) == Interval(2, 2)
    assert rational_sqrt_interval(Fraction(9, 16)) == Interval(
        sp.Rational(3, 4), sp.Rational(3, 4)
    )
    assert rational_sqrt_interval(0) == Interval(0, 0)


def test_negative_argument_rejected() -> None:
    with pytest.raises(ValueError):
        rational_sqrt_interval(-1)
    with pytest.raises(ValueError):
        interval_sqrt(Interval(-1, 4))


def test_endpoints_are_exact_rationals() -> None:
    iv = rational_sqrt_interval(2)
    assert isinstance(iv.lower, sp.Rational)
    assert isinstance(iv.upper, sp.Rational)
    # exact squared bounds bracket the argument
    assert iv.lower * iv.lower <= 2 <= iv.upper * iv.upper
    # and the enclosure is non-degenerate for an irrational
    assert iv.width > 0


# -- irrational constants enclose strictly outward -----------------------


def test_sqrt2_encloses_outward() -> None:
    iv = rational_sqrt_interval(2)
    # squared bounds straddle 2 strictly outward, never inward
    assert iv.lower * iv.lower < 2
    assert iv.upper * iv.upper > 2
    # sanity against a high-precision reference
    with mpmath.workprec(400):
        ref = mpmath.sqrt(2)
        lo = mpmath.mpf(int(iv.lower.p)) / mpmath.mpf(int(iv.lower.q))
        hi = mpmath.mpf(int(iv.upper.p)) / mpmath.mpf(int(iv.upper.q))
        assert lo <= ref <= hi


def test_sqrt2_tightness_is_reasonable() -> None:
    iv = rational_sqrt_interval(2)
    # the verified-and-widened enclosure is tight (controlled by bits), not loose
    assert iv.width < sp.Rational(1, 10**30)


# -- enclosure property (exact squared-bound backstop) -------------------


def test_rational_sqrt_encloses_exactly() -> None:
    rng = random.Random(11)
    for _ in range(300):
        p = rng.randint(0, 5000)
        q = rng.randint(1, 50)
        x = Fraction(p, q)
        iv = rational_sqrt_interval(x)
        # exact, float-free soundness check
        assert iv.lower * iv.lower <= x <= iv.upper * iv.upper


def test_interval_sqrt_encloses_samples() -> None:
    rng = random.Random(12)
    for _ in range(200):
        a = Fraction(rng.randint(0, 4000), rng.randint(1, 30))
        b = a + Fraction(rng.randint(0, 4000), rng.randint(1, 30))
        box = Interval(a, b)
        result = interval_sqrt(box)
        for _ in range(40):
            t = Fraction(rng.randint(0, 1000), 1000)
            x = a + t * (b - a)
            # lower <= sqrt(x) <= upper  <=>  lower**2 <= x <= upper**2
            assert _frac(result.lower) ** 2 <= x <= _frac(result.upper) ** 2


def test_interval_sqrt_is_monotonic_endpoints() -> None:
    box = Interval(2, 8)
    result = interval_sqrt(box)
    assert result.lower * result.lower <= 2
    assert result.upper * result.upper >= 8


# -- composition with the exact rational core stays sound ----------------


def test_sqrt_composes_with_rational_core() -> None:
    """A distance-barrier-like form: sqrt((x)**2 + (y)**2) over a box."""

    rng = random.Random(13)
    for _ in range(150):
        ax = Fraction(rng.randint(-30, 30), rng.randint(1, 6))
        bx = ax + Fraction(rng.randint(0, 30), rng.randint(1, 6))
        ay = Fraction(rng.randint(-30, 30), rng.randint(1, 6))
        by = ay + Fraction(rng.randint(0, 30), rng.randint(1, 6))
        ix, iy = Interval(ax, bx), Interval(ay, by)
        radius = interval_sqrt(ix**2 + iy**2)
        for _ in range(30):
            tx = Fraction(rng.randint(0, 1000), 1000)
            ty = Fraction(rng.randint(0, 1000), 1000)
            x = ax + tx * (bx - ax)
            y = ay + ty * (by - ay)
            d2 = x * x + y * y
            assert _frac(radius.lower) ** 2 <= d2 <= _frac(radius.upper) ** 2
