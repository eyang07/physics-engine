"""Adapter capability checks and obligation target classification."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from engine.verification.ir import ObligationSpec, VerificationProblem

OBLIGATION_TARGETS = (
    "continuous-lyapunov",
    "discrete-lyapunov",
    "continuous-barrier",
    "discrete-barrier",
    "generic-continuous",
    "generic-discrete",
    "candidate-without-dynamics",
    "obligation-only",
    "mixed-candidate",
)
MALFORMED_OBLIGATION_TARGETS = (
    "candidate-without-dynamics",
    "mixed-candidate",
)
DYNAMICS_KINDS = ("continuous", "discrete")
CANDIDATE_KINDS = ("lyapunov", "barrier")
OBLIGATION_SHAPE_FEATURES = (
    "region-scoped",
    "excluded-points",
    "assumptions",
    "strict-comparison",
    "nonzero-rhs",
)


@dataclass(frozen=True)
class ObligationClassification:
    """Derived target information for one verification obligation."""

    obligation_id: str
    target: str
    dynamics_kind: str | None
    candidate_kind: str | None
    required_capability: str
    shape_features: tuple[str, ...] = ()
    malformed_reason: str | None = None

    def __post_init__(self) -> None:
        if self.target not in OBLIGATION_TARGETS:
            raise ValueError(f"unknown obligation target: {self.target!r}")
        if self.dynamics_kind not in (None, *DYNAMICS_KINDS):
            raise ValueError("dynamics_kind must be continuous, discrete, or None")
        if self.candidate_kind not in (None, *CANDIDATE_KINDS, "mixed"):
            raise ValueError("candidate_kind must be lyapunov, barrier, mixed, or None")
        if not self.required_capability:
            raise ValueError("required_capability must be non-empty")
        unknown_shapes = set(self.shape_features) - set(OBLIGATION_SHAPE_FEATURES)
        if unknown_shapes:
            raise ValueError(f"unknown obligation shape features: {sorted(unknown_shapes)}")
        if len(self.shape_features) != len(set(self.shape_features)):
            raise ValueError("obligation shape features must be unique")
        if self.target in MALFORMED_OBLIGATION_TARGETS and not self.malformed_reason:
            raise ValueError("malformed targets must include a reason")
        if self.target not in MALFORMED_OBLIGATION_TARGETS and self.malformed_reason:
            raise ValueError("well-formed targets must not include a malformed reason")

    def to_dict(self) -> dict[str, object]:
        payload = {
            "obligationId": self.obligation_id,
            "target": self.target,
            "dynamicsKind": self.dynamics_kind,
            "candidateKind": self.candidate_kind,
            "requiredCapability": self.required_capability,
            "shapeFeatures": list(self.shape_features),
        }
        if self.malformed_reason is not None:
            payload["malformedReason"] = self.malformed_reason
        return payload


@dataclass(frozen=True)
class CapabilityAssessment:
    """Machine-readable explanation of adapter support for one obligation."""

    adapter: str
    supports_discharge: bool
    target_supported: bool
    dynamics_kind_supported: bool
    candidate_kind_supported: bool
    unsupported_shape_features: tuple[str, ...]

    def __post_init__(self) -> None:
        unknown_shapes = set(self.unsupported_shape_features) - set(OBLIGATION_SHAPE_FEATURES)
        if unknown_shapes:
            raise ValueError(f"unknown unsupported obligation shapes: {sorted(unknown_shapes)}")

    @property
    def supported(self) -> bool:
        return (
            self.supports_discharge
            and self.target_supported
            and self.dynamics_kind_supported
            and self.candidate_kind_supported
            and not self.unsupported_shape_features
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "adapter": self.adapter,
            "supportsDischarge": self.supports_discharge,
            "targetSupported": self.target_supported,
            "dynamicsKindSupported": self.dynamics_kind_supported,
            "candidateKindSupported": self.candidate_kind_supported,
            "unsupportedShapeFeatures": list(self.unsupported_shape_features),
            "supported": self.supported,
        }


@dataclass(frozen=True)
class AdapterCapabilities:
    """Static discharge capabilities advertised by a verification adapter."""

    adapter: str
    supported_targets: tuple[str, ...] = ()
    supports_discharge: bool = False
    supported_dynamics_kinds: tuple[str, ...] = DYNAMICS_KINDS
    supported_candidate_kinds: tuple[str, ...] = CANDIDATE_KINDS
    supported_obligation_shapes: tuple[str, ...] = OBLIGATION_SHAPE_FEATURES

    def __post_init__(self) -> None:
        if not self.adapter:
            raise ValueError("adapter name must be non-empty")
        unknown = set(self.supported_targets) - set(OBLIGATION_TARGETS)
        if unknown:
            raise ValueError(f"unknown supported obligation targets: {sorted(unknown)}")
        malformed = set(self.supported_targets) & set(MALFORMED_OBLIGATION_TARGETS)
        if malformed:
            raise ValueError(f"malformed targets cannot be supported: {sorted(malformed)}")
        unknown_dynamics = set(self.supported_dynamics_kinds) - set(DYNAMICS_KINDS)
        if unknown_dynamics:
            raise ValueError(f"unknown supported dynamics kinds: {sorted(unknown_dynamics)}")
        unknown_candidates = set(self.supported_candidate_kinds) - set(CANDIDATE_KINDS)
        if unknown_candidates:
            raise ValueError(
                f"unknown supported candidate kinds: {sorted(unknown_candidates)}"
            )
        unknown_shapes = set(self.supported_obligation_shapes) - set(OBLIGATION_SHAPE_FEATURES)
        if unknown_shapes:
            raise ValueError(
                f"unknown supported obligation shapes: {sorted(unknown_shapes)}"
            )
        if self.supported_targets and not self.supports_discharge:
            raise ValueError("non-discharging adapters must not advertise targets")

    def supports(self, classification: ObligationClassification) -> bool:
        return self.assess(classification).supported

    def assess(self, classification: ObligationClassification) -> CapabilityAssessment:
        return CapabilityAssessment(
            adapter=self.adapter,
            supports_discharge=self.supports_discharge,
            target_supported=(
                classification.malformed_reason is None
                and classification.target in self.supported_targets
            ),
            dynamics_kind_supported=(
                classification.dynamics_kind is None
                or classification.dynamics_kind in self.supported_dynamics_kinds
            ),
            candidate_kind_supported=(
                classification.candidate_kind is None
                or classification.candidate_kind in self.supported_candidate_kinds
            ),
            unsupported_shape_features=tuple(
                feature
                for feature in classification.shape_features
                if feature not in self.supported_obligation_shapes
            ),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "adapter": self.adapter,
            "supportsDischarge": self.supports_discharge,
            "supportedTargets": list(self.supported_targets),
            "supportedDynamicsKinds": list(self.supported_dynamics_kinds),
            "supportedCandidateKinds": list(self.supported_candidate_kinds),
            "supportedObligationShapes": list(self.supported_obligation_shapes),
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
            obligation=obligation,
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
    obligation: ObligationSpec,
    dynamics_kind: str | None,
    candidate_kinds: set[str],
) -> ObligationClassification:
    shape_features = _shape_features(obligation)
    if len(candidate_kinds) > 1:
        return ObligationClassification(
            obligation_id=obligation.id,
            target="mixed-candidate",
            dynamics_kind=dynamics_kind,
            candidate_kind="mixed",
            required_capability="discharge:mixed-candidate",
            shape_features=shape_features,
            malformed_reason=(
                "Obligation is linked to multiple candidate kinds; split or "
                "disambiguate candidate ownership before discharge."
            ),
        )

    candidate_kind = next(iter(candidate_kinds), None)
    if dynamics_kind is None:
        if candidate_kind is not None:
            return ObligationClassification(
                obligation_id=obligation.id,
                target="candidate-without-dynamics",
                dynamics_kind=None,
                candidate_kind=candidate_kind,
                required_capability="discharge:candidate-without-dynamics",
                shape_features=shape_features,
                malformed_reason=(
                    "Candidate obligation has no dynamics model; certificate "
                    "discharge requires the model used to derive it."
                ),
            )
        return ObligationClassification(
            obligation_id=obligation.id,
            target="obligation-only",
            dynamics_kind=None,
            candidate_kind=candidate_kind,
            required_capability="discharge:obligation-only",
            shape_features=shape_features,
        )

    if candidate_kind in ("lyapunov", "barrier"):
        target = f"{dynamics_kind}-{candidate_kind}"
    else:
        target = f"generic-{dynamics_kind}"
    return ObligationClassification(
        obligation_id=obligation.id,
        target=target,
        dynamics_kind=dynamics_kind,
        candidate_kind=candidate_kind,
        required_capability=f"discharge:{target}",
        shape_features=shape_features,
    )


def _shape_features(obligation: ObligationSpec) -> tuple[str, ...]:
    features: list[str] = []
    if obligation.region_id is not None:
        features.append("region-scoped")
    if obligation.excluded_points:
        features.append("excluded-points")
    if obligation.assumption_ids:
        features.append("assumptions")
    if obligation.comparison in ("<", ">"):
        features.append("strict-comparison")
    if float(obligation.rhs) != 0.0:
        features.append("nonzero-rhs")
    return tuple(features)
