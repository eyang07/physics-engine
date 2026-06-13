"""Adapter capability checks and obligation target classification."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from engine.verification.ir import VerificationProblem

OBLIGATION_TARGETS = (
    "continuous-lyapunov",
    "discrete-lyapunov",
    "continuous-barrier",
    "discrete-barrier",
    "generic-continuous",
    "generic-discrete",
    "obligation-only",
    "mixed-candidate",
)


@dataclass(frozen=True)
class ObligationClassification:
    """Derived target information for one verification obligation."""

    obligation_id: str
    target: str
    dynamics_kind: str | None
    candidate_kind: str | None
    required_capability: str

    def __post_init__(self) -> None:
        if self.target not in OBLIGATION_TARGETS:
            raise ValueError(f"unknown obligation target: {self.target!r}")
        if self.dynamics_kind not in (None, "continuous", "discrete"):
            raise ValueError("dynamics_kind must be continuous, discrete, or None")
        if self.candidate_kind not in (None, "lyapunov", "barrier", "mixed"):
            raise ValueError("candidate_kind must be lyapunov, barrier, mixed, or None")
        if not self.required_capability:
            raise ValueError("required_capability must be non-empty")

    def to_dict(self) -> dict[str, str | None]:
        return {
            "obligationId": self.obligation_id,
            "target": self.target,
            "dynamicsKind": self.dynamics_kind,
            "candidateKind": self.candidate_kind,
            "requiredCapability": self.required_capability,
        }


@dataclass(frozen=True)
class AdapterCapabilities:
    """Static discharge capabilities advertised by a verification adapter."""

    adapter: str
    supported_targets: tuple[str, ...] = ()
    supports_discharge: bool = False

    def __post_init__(self) -> None:
        if not self.adapter:
            raise ValueError("adapter name must be non-empty")
        unknown = set(self.supported_targets) - set(OBLIGATION_TARGETS)
        if unknown:
            raise ValueError(f"unknown supported obligation targets: {sorted(unknown)}")
        if self.supported_targets and not self.supports_discharge:
            raise ValueError("non-discharging adapters must not advertise targets")

    def supports(self, classification: ObligationClassification) -> bool:
        return (
            self.supports_discharge
            and classification.target in self.supported_targets
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "adapter": self.adapter,
            "supportsDischarge": self.supports_discharge,
            "supportedTargets": list(self.supported_targets),
        }


def obligation_classifications(
    problem: VerificationProblem,
) -> tuple[ObligationClassification, ...]:
    """Classify obligations into target families for adapter selection."""

    candidate_kinds_by_obligation: dict[str, set[str]] = {
        obligation.id: set() for obligation in problem.obligations
    }
    for candidate in problem.candidates:
        for obligation_id in candidate.obligation_ids:
            candidate_kinds_by_obligation[obligation_id].add(candidate.kind)

    dynamics_kind = None if problem.dynamics is None else problem.dynamics.kind
    return tuple(
        _classify_obligation(
            obligation_id=obligation.id,
            dynamics_kind=dynamics_kind,
            candidate_kinds=candidate_kinds_by_obligation[obligation.id],
        )
        for obligation in problem.obligations
    )


def classifications_by_obligation(
    problem: VerificationProblem,
) -> Mapping[str, ObligationClassification]:
    """Return classifications keyed by obligation id."""

    return {
        classification.obligation_id: classification
        for classification in obligation_classifications(problem)
    }


def _classify_obligation(
    *,
    obligation_id: str,
    dynamics_kind: str | None,
    candidate_kinds: set[str],
) -> ObligationClassification:
    if len(candidate_kinds) > 1:
        return ObligationClassification(
            obligation_id=obligation_id,
            target="mixed-candidate",
            dynamics_kind=dynamics_kind,
            candidate_kind="mixed",
            required_capability="discharge:mixed-candidate",
        )

    candidate_kind = next(iter(candidate_kinds), None)
    if dynamics_kind is None:
        return ObligationClassification(
            obligation_id=obligation_id,
            target="obligation-only",
            dynamics_kind=None,
            candidate_kind=candidate_kind,
            required_capability="discharge:obligation-only",
        )

    if candidate_kind in ("lyapunov", "barrier"):
        target = f"{dynamics_kind}-{candidate_kind}"
    else:
        target = f"generic-{dynamics_kind}"
    return ObligationClassification(
        obligation_id=obligation_id,
        target=target,
        dynamics_kind=dynamics_kind,
        candidate_kind=candidate_kind,
        required_capability=f"discharge:{target}",
    )
