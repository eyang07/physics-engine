"""Exact-rational interval arithmetic.

The level-2 (certified-numeric) reachability lane rests on *sound* interval
enclosures of one-step obligation expressions. This module provides the
foundation: an :class:`Interval` whose endpoints are exact rationals
(``sympy.Rational``), so the enclosure property holds **by construction** —
rational arithmetic has no rounding at all, so the result of every supported
operation is the exact range of the underlying real function over the input
box (or, for the straddling-zero even-power case, a sound super-set of it).

Soundness, not tightness, is the contract here. Every operation returns an
interval that *contains* the true image; some operations (notably even powers
straddling zero) are not the tightest possible enclosure but are always
enclosing. Floating-point inputs are rejected rather than silently rounded:
the credibility-critical failure mode of this lane is an unsound endpoint, so
only exact rational inputs are admitted.

Irrational operations — ``sqrt`` and irrational constants such as ``sqrt(2)``
— are the only places the flagship needs floating point. They live in a thin
outward-rounded layer (:func:`rational_sqrt_interval` / :func:`interval_sqrt`)
that uses mpmath only to *propose* a candidate enclosure and then verifies and
widens it with exact rational arithmetic, so the enclosing endpoints are exact
rationals and soundness never depends on trusting mpmath's rounding. The
rational core above stays exact; only the ``sqrt`` candidate touches mpmath.

Nothing in this module claims proof or certification. It computes sound
enclosures under stated assumptions; external backends dispose.
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction

import mpmath
import sympy as sp

Rational = sp.Rational

# Default mpmath working precision (bits) for proposing sqrt candidates. The
# candidate is exactly verified and widened afterwards, so this controls only
# enclosure tightness, never soundness.
_DEFAULT_SQRT_BITS = 200


def _as_rational(value: object) -> sp.Rational:
    """Coerce ``value`` to an exact ``sympy.Rational``.

    Integers, :class:`fractions.Fraction`, exact strings (e.g. ``"1/3"``), and
    SymPy rationals are accepted. Floats are rejected: admitting a binary float
    would silently introduce a rounded endpoint and break the by-construction
    soundness of the rational core.
    """

    if isinstance(value, bool):  # bool is an int subclass; refuse it explicitly
        raise TypeError("interval endpoints must be exact rationals, not bool")
    if isinstance(value, float):
        raise TypeError(
            "interval endpoints must be exact rationals; a float would be "
            "silently rounded. Pass an int, Fraction, exact string, or "
            "sympy.Rational instead."
        )
    if isinstance(value, sp.Rational):
        return value
    if isinstance(value, int):
        return sp.Integer(value)
    if isinstance(value, Fraction):
        return sp.Rational(value.numerator, value.denominator)
    if isinstance(value, str):
        rational = sp.Rational(value)
        if not isinstance(rational, sp.Rational):
            raise TypeError(f"{value!r} is not an exact rational")
        return rational
    if isinstance(value, sp.Expr) and value.is_Rational:
        return value
    raise TypeError(f"cannot interpret {value!r} as an exact rational")


@dataclass(frozen=True)
class Interval:
    """A closed interval ``[lower, upper]`` with exact rational endpoints.

    Operations return sound enclosures of the corresponding real function over
    the input intervals. Because the endpoints are exact rationals there is no
    rounding, so the enclosure property holds by construction.
    """

    lower: sp.Rational
    upper: sp.Rational

    def __post_init__(self) -> None:
        object.__setattr__(self, "lower", _as_rational(self.lower))
        object.__setattr__(self, "upper", _as_rational(self.upper))
        if self.lower > self.upper:
            raise ValueError(
                f"interval lower bound {self.lower} exceeds upper bound "
                f"{self.upper}"
            )

    # -- constructors -----------------------------------------------------
    @classmethod
    def point(cls, value: object) -> "Interval":
        """A degenerate interval ``[value, value]``."""

        rational = _as_rational(value)
        return cls(rational, rational)

    @classmethod
    def _coerce(cls, value: object) -> "Interval":
        if isinstance(value, Interval):
            return value
        return cls.point(value)

    # -- queries ----------------------------------------------------------
    @property
    def width(self) -> sp.Rational:
        return self.upper - self.lower

    def contains(self, value: object) -> bool:
        rational = _as_rational(value)
        return self.lower <= rational <= self.upper

    def __contains__(self, value: object) -> bool:
        return self.contains(value)

    # -- arithmetic -------------------------------------------------------
    def __add__(self, other: object) -> "Interval":
        o = self._coerce(other)
        return Interval(self.lower + o.lower, self.upper + o.upper)

    __radd__ = __add__

    def __neg__(self) -> "Interval":
        return Interval(-self.upper, -self.lower)

    def __sub__(self, other: object) -> "Interval":
        return self + (-self._coerce(other))

    def __rsub__(self, other: object) -> "Interval":
        return self._coerce(other) - self

    def __mul__(self, other: object) -> "Interval":
        o = self._coerce(other)
        products = (
            self.lower * o.lower,
            self.lower * o.upper,
            self.upper * o.lower,
            self.upper * o.upper,
        )
        return Interval(min(products), max(products))

    __rmul__ = __mul__

    def reciprocal(self) -> "Interval":
        """Enclose ``1 / x`` for ``x`` in this interval.

        Raises if the interval contains zero, where ``1 / x`` is unbounded and
        no finite enclosure exists.
        """

        if self.lower <= 0 <= self.upper:
            raise ZeroDivisionError(
                "reciprocal of an interval containing zero is unbounded"
            )
        return Interval(1 / self.upper, 1 / self.lower)

    def __pow__(self, exponent: int) -> "Interval":
        if not isinstance(exponent, int) or isinstance(exponent, bool):
            raise TypeError("interval exponent must be a plain integer")
        if exponent == 0:
            return Interval(sp.Integer(1), sp.Integer(1))
        if exponent < 0:
            return self.reciprocal() ** (-exponent)

        if exponent % 2 == 1:  # odd power is monotonic increasing
            return Interval(self.lower**exponent, self.upper**exponent)

        # even power: the parabola x**exponent
        if self.lower >= 0:
            return Interval(self.lower**exponent, self.upper**exponent)
        if self.upper <= 0:
            return Interval(self.upper**exponent, self.lower**exponent)
        # straddles zero: minimum is 0 (sound enclosure of the image)
        return Interval(
            sp.Integer(0),
            max(self.lower**exponent, self.upper**exponent),
        )

    # -- elementwise functions -------------------------------------------
    def __abs__(self) -> "Interval":
        if self.lower >= 0:
            return Interval(self.lower, self.upper)
        if self.upper <= 0:
            return Interval(-self.upper, -self.lower)
        return Interval(sp.Integer(0), max(-self.lower, self.upper))


def interval_abs(value: Interval) -> Interval:
    """Enclose ``Abs(x)`` over the interval — the IR-facing ``Abs`` handler."""

    return abs(value)


def interval_max(*values: Interval | object) -> Interval:
    """Enclose ``Max(...)`` componentwise over the given intervals/points."""

    if not values:
        raise ValueError("interval_max requires at least one argument")
    intervals = [Interval._coerce(v) for v in values]
    lower = max(i.lower for i in intervals)
    upper = max(i.upper for i in intervals)
    return Interval(lower, upper)


def interval_min(*values: Interval | object) -> Interval:
    """Enclose ``Min(...)`` componentwise over the given intervals/points."""

    if not values:
        raise ValueError("interval_min requires at least one argument")
    intervals = [Interval._coerce(v) for v in values]
    lower = min(i.lower for i in intervals)
    upper = min(i.upper for i in intervals)
    return Interval(lower, upper)


# -- irrational layer: outward-rounded sqrt ------------------------------


def _mpf_to_rational(value: mpmath.mpf) -> sp.Rational:
    """Exactly convert a finite mpmath float to a ``sympy.Rational``.

    An ``mpf`` is a dyadic rational ``(-1)**sign * man * 2**exp``, so this
    conversion is exact — no rounding is introduced.
    """

    sign, man, exp, _bc = value._mpf_
    if exp >= 0:
        rational = sp.Rational(int(man) * (1 << exp))
    else:
        rational = sp.Rational(int(man), 1 << (-exp))
    return -rational if sign else rational


def rational_sqrt_interval(
    value: object, *, bits: int = _DEFAULT_SQRT_BITS
) -> "Interval":
    """Enclose ``sqrt(value)`` for an exact nonnegative rational ``value``.

    mpmath proposes a candidate square root at ``bits`` of precision; the
    candidate is then verified and, if necessary, widened using exact rational
    arithmetic so the returned endpoints satisfy ``lower**2 <= value`` and
    ``upper**2 >= value`` exactly. Soundness therefore holds independently of
    mpmath's internal rounding. Perfect rational squares return a degenerate
    (exact) interval.
    """

    x = _as_rational(value)
    if x < 0:
        raise ValueError(f"sqrt of a negative quantity {x} is out of domain")
    if x == 0:
        return Interval(sp.Integer(0), sp.Integer(0))

    exact = sp.sqrt(x)
    if exact.is_Rational:
        return Interval(exact, exact)

    with mpmath.workprec(bits):
        candidate_mpf = mpmath.sqrt(mpmath.mpf(int(x.p)) / mpmath.mpf(int(x.q)))
    candidate = _mpf_to_rational(candidate_mpf)

    # Widen outward with exact rational checks until both squared bounds hold.
    step = (abs(candidate) + 1) * sp.Rational(1, 1 << max(bits - 8, 1))
    lower = candidate
    delta = step
    while lower * lower > x:
        lower -= delta
        delta *= 2
    if lower < 0:
        lower = sp.Integer(0)
    upper = candidate
    delta = step
    while upper * upper < x:
        upper += delta
        delta *= 2

    # Exact soundness assertions: the lane lives or dies on these holding.
    assert lower * lower <= x <= upper * upper
    return Interval(lower, upper)


def interval_sqrt(value: object, *, bits: int = _DEFAULT_SQRT_BITS) -> "Interval":
    """Enclose ``sqrt`` over an interval (or rational point).

    ``sqrt`` is monotonically increasing on ``[0, inf)``, so the enclosure is
    ``[sqrt_lower(a), sqrt_upper(b)]`` for ``[a, b]``. A negative lower bound is
    rejected as out of domain rather than silently clamped.
    """

    iv = Interval._coerce(value)
    if iv.lower < 0:
        raise ValueError(
            f"sqrt of an interval with negative lower bound {iv.lower} is out "
            "of domain"
        )
    lower = rational_sqrt_interval(iv.lower, bits=bits).lower
    upper = rational_sqrt_interval(iv.upper, bits=bits).upper
    return Interval(lower, upper)


__all__ = [
    "Interval",
    "interval_abs",
    "interval_max",
    "interval_min",
    "interval_sqrt",
    "rational_sqrt_interval",
]
