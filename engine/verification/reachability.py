"""One-step image enclosure of a discrete map.

The set-propagation primitive of the level-2 (certified-numeric) reachability
lane. Given a discrete map ``x_{k+1} = F(x_k)`` — a
:class:`~engine.dynamics.discrete.DiscreteSystem` or open-loop
:class:`~engine.dynamics.discrete.ControlledDiscreteSystem` — and a *box*
assigning every free symbol an :class:`~engine.numerics.intervals.Interval`,
:func:`one_step_image` returns an interval box that soundly **over-approximates
the image** of the map: every concrete next state reachable from a state in the
box lies inside the returned box.

Each update component is lowered through the fail-closed enclosure evaluator
(:func:`~engine.verification.enclosure.enclose_expression`), so the soundness
discipline carries over unchanged: the polynomial path stays exact-rational,
only ``sqrt`` touches mpmath, and any non-whitelisted node aborts rather than
risk an unsound result.

**Bounded inputs as interval parameters.** Carrying a control, disturbance, or
velocity as a *bounded interval* — rather than substituting a feedback law — is
how the closed-loop reachable set is over-approximated soundly: if the true law
keeps the input inside the interval (e.g. a guard-band controller whose output
always lies in ``[-thrust, thrust]``), the open-loop image over that interval
contains every closed-loop successor. The guard-band closed loop itself carries
a ``Piecewise`` switch, which the whitelist refuses; enclosing the open-loop map
over the input interval is the sound way to bound it without branch handling.

Nothing here claims proof or certification. It computes a sound enclosure of the
reachable image under stated assumptions; external backends dispose.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any, Mapping

import sympy as sp

from engine.dynamics.discrete import ControlledDiscreteSystem, DiscreteSystem
from engine.numerics.intervals import Interval
from engine.verification.enclosure import enclose_expression
from engine.verification.ir import (
    DynamicsSpec,
    EnclosureDomainConstraintSpec,
    ObligationSpec,
    VerificationProblem,
)

REACHABILITY_HANDOFF_SCHEMA_VERSION = "verification-reachability-handoff/v1"
REACHABILITY_HANDOFF_INDEX_SCHEMA_VERSION = "verification-reachability-handoff-index/v1"
REACHABILITY_HANDOFF_INDEX_FILENAME = "index.json"
REACHABILITY_HANDOFF_KIND = "reachability"

_HANDOFF_NOTE = (
    "Non-discharging reachability handoff. This artifact packages dynamics, a "
    "recorded box, and an obligation for an external validated-numerics backend; "
    "it records no proof result and discharges nothing."
)


def _free_symbol_names(expressions: tuple[sp.Expr, ...]) -> set[str]:
    names: set[str] = set()
    for expression in expressions:
        names |= {symbol.name for symbol in sp.sympify(expression).free_symbols}
    return names


def one_step_image(
    system: DiscreteSystem | ControlledDiscreteSystem,
    box: Mapping[str, Interval],
) -> dict[str, Interval]:
    """Over-approximate the one-step image of ``system`` over ``box``.

    ``box`` maps symbol names — states plus any bounded controls, disturbances,
    or parameters appearing in the update — to intervals. The result maps each
    state component name to an interval enclosing its successor over the whole
    box. Missing symbols raise, fail closed, before any partial evaluation.
    """

    required = _free_symbol_names(system.update)
    missing = sorted(required - set(box))
    if missing:
        raise ValueError(
            "box is missing intervals for symbols: " + ", ".join(missing)
        )

    image: dict[str, Interval] = {}
    for symbol, update in zip(system.state, system.update, strict=True):
        image[symbol.name] = enclose_expression(update, box)
    return image


def _dump_json(payload: Any) -> str:
    return json.dumps(payload, indent=2) + "\n"


@dataclass(frozen=True)
class ReachabilityHandoffArtifact:
    """One non-discharging reachability problem for an external backend."""

    id: str
    problem_id: str
    obligation_id: str
    enclosure_status_id: str
    dynamics: DynamicsSpec
    obligation: ObligationSpec
    box: tuple[tuple[str, str, str], ...]
    domain_constraints: tuple[EnclosureDomainConstraintSpec, ...] = ()
    adapter_category: str = REACHABILITY_HANDOFF_KIND
    discharges: bool = False
    external_status: str = "external-required"
    note: str = _HANDOFF_NOTE
    schema_version: str = REACHABILITY_HANDOFF_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != REACHABILITY_HANDOFF_SCHEMA_VERSION:
            raise ValueError(
                "reachability handoff schema_version must be "
                f"{REACHABILITY_HANDOFF_SCHEMA_VERSION!r}"
            )
        for label, value in (
            ("id", self.id),
            ("problem_id", self.problem_id),
            ("obligation_id", self.obligation_id),
            ("enclosure_status_id", self.enclosure_status_id),
        ):
            if not isinstance(value, str) or not value:
                raise ValueError(f"reachability handoff {label} must be non-empty")
        if self.adapter_category != REACHABILITY_HANDOFF_KIND:
            raise ValueError("reachability handoff adapter_category must be reachability")
        if self.discharges:
            raise ValueError("reachability handoff artifacts never discharge")
        if self.external_status != "external-required":
            raise ValueError(
                "reachability handoff external_status must stay external-required"
            )
        if not self.box:
            raise ValueError("reachability handoff must record a non-empty box")
        names = [name for name, _, _ in self.box]
        if len(names) != len(set(names)):
            raise ValueError("reachability handoff box variables must be unique")

    @property
    def filename(self) -> str:
        return f"{self.obligation_id}.reachability.json"

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schemaVersion": self.schema_version,
            "id": self.id,
            "adapterCategory": self.adapter_category,
            "problemId": self.problem_id,
            "obligationId": self.obligation_id,
            "enclosureStatusId": self.enclosure_status_id,
            "dynamics": self.dynamics.to_dict(),
            "obligation": self.obligation.to_dict(),
            "box": {name: [lower, upper] for name, lower, upper in self.box},
            "discharges": self.discharges,
            "externalStatus": self.external_status,
            "note": self.note,
        }
        if self.domain_constraints:
            payload["domainConstraints"] = [
                constraint.to_dict() for constraint in self.domain_constraints
            ]
        return payload

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "ReachabilityHandoffArtifact":
        box_data = data.get("box")
        if not isinstance(box_data, Mapping):
            raise ValueError("reachability handoff box must be a mapping")
        return cls(
            id=_string(data, "id"),
            problem_id=_string(data, "problemId"),
            obligation_id=_string(data, "obligationId"),
            enclosure_status_id=_string(data, "enclosureStatusId"),
            dynamics=DynamicsSpec.from_dict(_mapping(data, "dynamics")),
            obligation=ObligationSpec.from_dict(_mapping(data, "obligation")),
            box=tuple(
                sorted(
                    (name, str(bounds[0]), str(bounds[1]))
                    for name, bounds in box_data.items()
                )
            ),
            domain_constraints=tuple(
                EnclosureDomainConstraintSpec.from_dict(item)
                for item in data.get("domainConstraints", ())
            ),
            adapter_category=data.get("adapterCategory", REACHABILITY_HANDOFF_KIND),
            discharges=bool(data.get("discharges", False)),
            external_status=data.get("externalStatus", "external-required"),
            note=data.get("note", _HANDOFF_NOTE),
            schema_version=data.get(
                "schemaVersion", REACHABILITY_HANDOFF_SCHEMA_VERSION
            ),
        )


@dataclass(frozen=True)
class ReachabilityHandoffIndex:
    """Index of non-discharging reachability handoff files for one problem."""

    problem_id: str
    artifacts: tuple[tuple[str, str], ...]
    discharges: bool = False
    schema_version: str = REACHABILITY_HANDOFF_INDEX_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != REACHABILITY_HANDOFF_INDEX_SCHEMA_VERSION:
            raise ValueError(
                "reachability handoff index schema_version must be "
                f"{REACHABILITY_HANDOFF_INDEX_SCHEMA_VERSION!r}"
            )
        if not self.problem_id:
            raise ValueError("reachability handoff index problem_id must be non-empty")
        if self.discharges:
            raise ValueError("reachability handoff index never discharges")
        obligation_ids = [obligation_id for obligation_id, _ in self.artifacts]
        if len(obligation_ids) != len(set(obligation_ids)):
            raise ValueError("reachability handoff index obligation ids must be unique")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schemaVersion": self.schema_version,
            "problemId": self.problem_id,
            "artifactCount": len(self.artifacts),
            "discharges": self.discharges,
            "artifacts": [
                {"obligationId": obligation_id, "path": path}
                for obligation_id, path in self.artifacts
            ],
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "ReachabilityHandoffIndex":
        artifacts = data.get("artifacts")
        if not isinstance(artifacts, list):
            raise ValueError("reachability handoff index artifacts must be a list")
        index = cls(
            problem_id=_string(data, "problemId"),
            artifacts=tuple(
                (_string(item, "obligationId"), _string(item, "path"))
                for item in artifacts
            ),
            discharges=bool(data.get("discharges", False)),
            schema_version=data.get(
                "schemaVersion", REACHABILITY_HANDOFF_INDEX_SCHEMA_VERSION
            ),
        )
        if int(data.get("artifactCount", len(index.artifacts))) != len(index.artifacts):
            raise ValueError("reachability handoff index artifactCount mismatch")
        return index


def _string(data: Mapping[str, Any], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(f"reachability handoff {key} is invalid")
    return value


def _mapping(data: Mapping[str, Any], key: str) -> Mapping[str, Any]:
    value = data.get(key)
    if not isinstance(value, Mapping):
        raise ValueError(f"reachability handoff {key} must be a mapping")
    return value


def _is_one_step_obligation(obligation: ObligationSpec) -> bool:
    text = f"{obligation.id} {obligation.name} {obligation.description}".lower()
    return (
        "one-step" in text
        or "forward-invariance" in text
        or "non-increase" in text
    )


def reachability_handoff_artifacts(
    problem: VerificationProblem,
) -> tuple[ReachabilityHandoffArtifact, ...]:
    """Build non-discharging reachability handoff artifacts for ``problem``.

    The current handoff is grounded in recorded certified-numeric enclosure
    statuses: each artifact carries the discrete dynamics, the obligation, and
    the exact-rational box/domain constraints from the enclosure status. It
    does not run an external backend and cannot discharge anything.
    """

    if problem.dynamics is None or problem.dynamics.kind != "discrete":
        return ()

    obligations = {obligation.id: obligation for obligation in problem.obligations}
    artifacts: list[ReachabilityHandoffArtifact] = []
    seen: set[str] = set()
    for status in problem.enclosure_statuses:
        if status.obligation_id in seen:
            continue
        obligation = obligations[status.obligation_id]
        if not _is_one_step_obligation(obligation):
            continue
        seen.add(obligation.id)
        artifacts.append(
            ReachabilityHandoffArtifact(
                id=f"{problem.id}:{obligation.id}:reachability",
                problem_id=problem.id,
                obligation_id=obligation.id,
                enclosure_status_id=status.id,
                dynamics=problem.dynamics,
                obligation=obligation,
                box=status.box,
                domain_constraints=status.domain_constraints,
            )
        )
    return tuple(artifacts)


def write_reachability_handoff(
    problem: VerificationProblem,
    directory: str | Path,
) -> ReachabilityHandoffIndex:
    """Write one reachability handoff file per exported artifact."""

    output_dir = Path(directory)
    output_dir.mkdir(parents=True, exist_ok=True)
    artifacts = reachability_handoff_artifacts(problem)
    index = ReachabilityHandoffIndex(
        problem_id=problem.id,
        artifacts=tuple((artifact.obligation_id, artifact.filename) for artifact in artifacts),
    )
    for artifact in artifacts:
        (output_dir / artifact.filename).write_text(
            _dump_json(artifact.to_dict()), encoding="utf-8"
        )
    (output_dir / REACHABILITY_HANDOFF_INDEX_FILENAME).write_text(
        _dump_json(index.to_dict()), encoding="utf-8"
    )
    return index


def read_reachability_handoff(
    directory: str | Path,
) -> tuple[ReachabilityHandoffArtifact, ...]:
    """Read reachability handoff artifacts written by ``write_reachability_handoff``."""

    input_dir = Path(directory)
    index_path = input_dir / REACHABILITY_HANDOFF_INDEX_FILENAME
    if not index_path.is_file():
        raise ValueError(
            f"reachability handoff missing {REACHABILITY_HANDOFF_INDEX_FILENAME}"
        )
    index = ReachabilityHandoffIndex.from_dict(
        json.loads(index_path.read_text(encoding="utf-8"))
    )
    artifacts = tuple(
        ReachabilityHandoffArtifact.from_dict(
            json.loads((input_dir / path).read_text(encoding="utf-8"))
        )
        for _, path in index.artifacts
    )
    if tuple(artifact.obligation_id for artifact in artifacts) != tuple(
        obligation_id for obligation_id, _ in index.artifacts
    ):
        raise ValueError("reachability handoff artifact order/id mismatch")
    return artifacts


__all__ = [
    "REACHABILITY_HANDOFF_INDEX_FILENAME",
    "REACHABILITY_HANDOFF_INDEX_SCHEMA_VERSION",
    "REACHABILITY_HANDOFF_KIND",
    "REACHABILITY_HANDOFF_SCHEMA_VERSION",
    "ReachabilityHandoffArtifact",
    "ReachabilityHandoffIndex",
    "one_step_image",
    "reachability_handoff_artifacts",
    "read_reachability_handoff",
    "write_reachability_handoff",
]
