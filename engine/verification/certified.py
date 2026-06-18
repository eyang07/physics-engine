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

For constrained domains, the trusted producer still derives endpoints through
the same fail-closed evaluator: it combines the unconstrained lower endpoint
with a caller-supplied upper-bound expression whose soundness over
``box`` intersected with ``domain_constraints`` must be recorded in the status
assumptions. This is for monotone refinements such as a distance barrier over a
recorded standoff predicate; it is not a proof-discharge path.

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
    EnclosureDomainConstraintSpec,
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


def _serialized_box(box: Mapping[str, Interval]) -> tuple[tuple[str, str, str], ...]:
    return tuple(
        sorted(
            (name, str(interval.lower), str(interval.upper))
            for name, interval in box.items()
        )
    )


def _status_from_enclosure(
    *,
    id: str,
    obligation: ObligationSpec,
    box: Mapping[str, Interval],
    enclosure: Interval,
    soundness_assumptions: tuple[str, ...],
    region_id: str | None,
    note: str | None,
    domain_constraints: tuple[EnclosureDomainConstraintSpec, ...],
) -> EnclosureStatusSpec | None:
    rhs = Fraction(str(obligation.rhs))
    verdict = _verdict(obligation.comparison, enclosure, rhs)
    if verdict is None:
        return None

    extra = {} if note is None else {"note": note}
    return EnclosureStatusSpec(
        id=id,
        obligation_id=obligation.id,
        comparison=obligation.comparison,
        verdict=verdict,
        box=_serialized_box(box),
        enclosure_lower=str(enclosure.lower),
        enclosure_upper=str(enclosure.upper),
        rhs=obligation.rhs,
        region_id=region_id if region_id is not None else obligation.region_id,
        soundness_assumptions=tuple(soundness_assumptions),
        domain_constraints=domain_constraints,
        **extra,
    )


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
    domain_constraints: tuple[EnclosureDomainConstraintSpec, ...] = (),
) -> EnclosureStatusSpec | None:
    """Emit a certified-numeric status for ``obligation`` over ``box``.

    Returns ``None`` when the sound enclosure does not close the obligation over
    the box — the obligation then stays measured-only, never downgraded to a
    fabricated certified verdict.
    """

    enclosure = enclose_expression(obligation.expression, box)
    return _status_from_enclosure(
        id=id,
        obligation=obligation,
        enclosure=enclosure,
        box=box,
        region_id=region_id,
        soundness_assumptions=tuple(soundness_assumptions),
        domain_constraints=domain_constraints,
        note=note,
    )


def certified_constrained_upper_refinement_status(
    *,
    id: str,
    obligation: ObligationSpec,
    box: Mapping[str, Interval],
    upper_bound: ExpressionSpec,
    domain_constraints: tuple[EnclosureDomainConstraintSpec, ...],
    soundness_assumptions: tuple[str, ...] = (),
    region_id: str | None = None,
    note: str | None = None,
) -> EnclosureStatusSpec | None:
    """Emit a constrained-domain status from a sound upper refinement.

    The recorded claim is over ``box`` intersected with
    ``domain_constraints``. The lower endpoint is the fail-closed enclosure of
    the original obligation over the full box; the upper endpoint is the
    fail-closed enclosure of ``upper_bound`` over the same box. Callers must
    record why ``upper_bound`` encloses the original obligation on the
    constrained domain. If the refined interval still does not close the
    obligation, ``None`` is returned.

    This helper is intentionally only for ``<=``/``<`` obligations, where an
    upper bound can establish the holds verdict. It never proves or externally
    certifies an obligation.
    """

    if obligation.comparison not in ("<=", "<"):
        raise ValueError(
            "constrained upper refinement only supports <= and < obligations"
        )
    if not domain_constraints:
        raise ValueError(
            "constrained upper refinement requires recorded domain constraints"
        )

    unconstrained = enclose_expression(obligation.expression, box)
    upper_enclosure = enclose_expression(upper_bound, box)
    enclosure = Interval(unconstrained.lower, upper_enclosure.upper)
    return _status_from_enclosure(
        id=id,
        obligation=obligation,
        box=box,
        enclosure=enclosure,
        soundness_assumptions=soundness_assumptions,
        region_id=region_id,
        note=note,
        domain_constraints=domain_constraints,
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
    domain_constraints: tuple[EnclosureDomainConstraintSpec, ...] = (),
) -> EnclosureStatusSpec | None:
    """Emit a certified-numeric status from a finite branch partition.

    Returns ``None`` when the unioned enclosure does not close the obligation.
    This is still level 2 only: a sound enclosure over the stated box under the
    recorded branch-coverage assumptions, not a proof or safety certificate.
    """

    enclosure = partitioned_enclosure(partitions)
    partition_assumptions = tuple(
        f"Partition {partition.label!r} enclosed over "
        + ", ".join(
            f"{name} in [{interval.lower}, {interval.upper}]"
            for name, interval in sorted(partition.box.items())
        )
        for partition in partitions
    )
    return _status_from_enclosure(
        id=id,
        obligation=obligation,
        enclosure=enclosure,
        box=box,
        region_id=region_id,
        soundness_assumptions=tuple(soundness_assumptions) + partition_assumptions,
        domain_constraints=domain_constraints,
        note=note,
    )


__all__ = [
    "EnclosurePartition",
    "certified_constrained_upper_refinement_status",
    "certified_enclosure_status",
    "certified_partitioned_enclosure_status",
    "partitioned_enclosure",
]
