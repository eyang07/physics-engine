"""Trusted producer of level-2 certified-numeric enclosure statuses.

This is the *only* path that emits an
:class:`~engine.verification.ir.EnclosureStatusSpec`. Given an obligation and a
box of exact-rational symbol intervals, it computes a sound enclosure of the
obligation expression through the fail-closed evaluator
(:func:`~engine.verification.enclosure.enclose_expression`) and emits a
certified-numeric status *only* when that enclosure closes the obligation over
the whole box. When the enclosure does not close it, the obligation stays
measured-only (an honest "not certified"), so ``None`` is returned rather than a
weaker or fabricated status.

A certified-numeric enclosure is rigor level 2: sound over the stated box under
the recorded assumptions. It is never a proof or external certificate; the
obligation still requires external discharge to be proved.
"""

from __future__ import annotations

from fractions import Fraction
from typing import Mapping

from engine.numerics.intervals import Interval
from engine.verification.enclosure import enclose_expression
from engine.verification.ir import (
    EnclosureStatusSpec,
    ObligationSpec,
    _enclosure_holds,
    _enclosure_violated,
)


def _fraction(value) -> Fraction:
    return Fraction(int(value.p), int(value.q))


def _verdict(comparison: str, enclosure: Interval, rhs: Fraction) -> str | None:
    lower = _fraction(enclosure.lower)
    upper = _fraction(enclosure.upper)
    if _enclosure_holds(comparison, lower, upper, rhs):
        return "certified-holds"
    if _enclosure_violated(comparison, lower, upper, rhs):
        return "certified-violated"
    return None


def certified_enclosure_status(
    *,
    id: str,
    obligation: ObligationSpec,
    box: Mapping[str, Interval],
    soundness_assumptions: tuple[str, ...] = (),
    region_id: str | None = None,
    note: str | None = None,
) -> EnclosureStatusSpec | None:
    """Emit a certified-numeric status for ``obligation`` over ``box``.

    Returns ``None`` when the sound enclosure does not close the obligation over
    the box — the obligation then stays measured-only, never downgraded to a
    fabricated certified verdict.
    """

    enclosure = enclose_expression(obligation.expression, box)
    rhs = Fraction(str(obligation.rhs))
    verdict = _verdict(obligation.comparison, enclosure, rhs)
    if verdict is None:
        return None

    serialized_box = tuple(
        sorted(
            (name, str(interval.lower), str(interval.upper))
            for name, interval in box.items()
        )
    )
    extra = {} if note is None else {"note": note}
    return EnclosureStatusSpec(
        id=id,
        obligation_id=obligation.id,
        comparison=obligation.comparison,
        verdict=verdict,
        box=serialized_box,
        enclosure_lower=str(enclosure.lower),
        enclosure_upper=str(enclosure.upper),
        rhs=obligation.rhs,
        region_id=region_id if region_id is not None else obligation.region_id,
        soundness_assumptions=tuple(soundness_assumptions),
        **extra,
    )


__all__ = ["certified_enclosure_status"]
