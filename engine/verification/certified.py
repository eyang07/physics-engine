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

from collections.abc import Sequence
from dataclasses import dataclass
from fractions import Fraction
from typing import Mapping

from engine.numerics.intervals import Interval
from engine.verification.enclosure import enclose_expression
from engine.verification.ir import (
    EnclosureStatusSpec,
    ExpressionSpec,
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


@dataclass(frozen=True)
class EnclosurePartition:
    """One branch box for a sound partitioned enclosure.

    The expression must be exact for, or a sound upper/lower enclosing expression
    of, the original obligation on this box. Coverage of the whole recorded box
    is a caller-supplied construction invariant and should be recorded in the
    status soundness assumptions.
    """

    label: str
    expression: ExpressionSpec
    box: Mapping[str, Interval]

    def __post_init__(self) -> None:
        if not self.label:
            raise ValueError("enclosure partition label must be non-empty")
        if not self.box:
            raise ValueError("enclosure partition box must be non-empty")


def partitioned_enclosure(partitions: Sequence[EnclosurePartition]) -> Interval:
    """Union exact interval enclosures over a finite branch partition."""

    if not partitions:
        raise ValueError("partitioned enclosure requires at least one partition")
    intervals = tuple(
        enclose_expression(partition.expression, partition.box)
        for partition in partitions
    )
    return Interval(
        min(interval.lower for interval in intervals),
        max(interval.upper for interval in intervals),
    )


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


def certified_partitioned_enclosure_status(
    *,
    id: str,
    obligation: ObligationSpec,
    box: Mapping[str, Interval],
    partitions: Sequence[EnclosurePartition],
    soundness_assumptions: tuple[str, ...] = (),
    region_id: str | None = None,
    note: str | None = None,
) -> EnclosureStatusSpec | None:
    """Emit a certified-numeric status from a finite branch partition.

    Returns ``None`` when the unioned enclosure does not close the obligation.
    This is still level 2 only: a sound enclosure over the stated box under the
    recorded branch-coverage assumptions, not a proof or safety certificate.
    """

    enclosure = partitioned_enclosure(partitions)
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
    partition_assumptions = tuple(
        f"Partition {partition.label!r} enclosed over "
        + ", ".join(
            f"{name} in [{interval.lower}, {interval.upper}]"
            for name, interval in sorted(partition.box.items())
        )
        for partition in partitions
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
        soundness_assumptions=tuple(soundness_assumptions) + partition_assumptions,
        **extra,
    )


__all__ = [
    "EnclosurePartition",
    "certified_enclosure_status",
    "certified_partitioned_enclosure_status",
    "partitioned_enclosure",
]
