"""Non-discharging adapter-stub descriptors for external backend categories.

These descriptors say how an external backend *category* — reachability /
forward-invariance analysis, sum-of-squares certificate synthesis, or deductive
theorem proving — would consume each verification obligation: the target it
would classify the obligation as, the obligation shape it would have to handle,
and what shape of (externally produced) result it would yield.

They are tool-agnostic pointers of target and required shape only. No stub
attempts, records, or claims discharge; every obligation it touches stays
``rigor="external-required"``. The descriptors are derived deterministically
from the problem's obligation classifications (see
:mod:`engine.verification.capabilities`).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from engine.verification.capabilities import (
    MALFORMED_OBLIGATION_TARGETS,
    OBLIGATION_SHAPE_FEATURES,
    OBLIGATION_TARGETS,
    classifications_by_obligation,
)
from engine.verification.ir import VerificationProblem

ADAPTER_STUB_SCHEMA_VERSION = "verification-adapter-stubs/v1"

# A Tier-3 robust obligation is quantified over a bounded disturbance set: its
# closed loop is set-valued (one successor per admissible disturbance) and the
# worst-case term is baked into the obligation. An external backend must handle
# that obligation *shape* differently (a robust/set-valued query, not a single
# deterministic successor), so robust stubs carry an honest robustness flag and
# the disturbance set they quantify over. The robustness is derived purely from
# IR data: an obligation is robust when it cites a disturbance-bound assumption
# (id carrying this marker, the same convention the package regime descriptor
# uses) whose variables range over declared problem parameters. A robust stub is
# still non-discharging -- the flag describes the obligation shape, never a
# discharge.
_DISTURBANCE_ASSUMPTION_MARKER = "disturbance"

CATEGORY_REACHABILITY = "reachability"
CATEGORY_SOS_SYNTHESIS = "sos-certificate-synthesis"
CATEGORY_DEDUCTIVE_PROVER = "deductive-prover"
BACKEND_CATEGORIES = (
    CATEGORY_REACHABILITY,
    CATEGORY_SOS_SYNTHESIS,
    CATEGORY_DEDUCTIVE_PROVER,
)

_WELL_FORMED_TARGETS = tuple(
    target for target in OBLIGATION_TARGETS if target not in MALFORMED_OBLIGATION_TARGETS
)

_STUB_NOTE = "Descriptor only; this stub neither attempts nor records discharge."
_REPORT_NOTE = (
    "Adapter stubs describe how external backend categories would consume each "
    "obligation. They are tool-agnostic pointers of target and required shape "
    "only: no stub attempts, records, or claims discharge, and every obligation "
    "stays external-required."
)


@dataclass(frozen=True)
class BackendCategoryStub:
    """A static, non-discharging description of one external backend category."""

    category: str
    summary: str
    consumes_targets: tuple[str, ...]
    consumes: str
    produces: str

    def __post_init__(self) -> None:
        if self.category not in BACKEND_CATEGORIES:
            raise ValueError(f"unknown backend category: {self.category!r}")
        for label, value in (("summary", self.summary), ("consumes", self.consumes), ("produces", self.produces)):
            if not isinstance(value, str) or not value:
                raise ValueError(f"backend category {self.category} {label} must be non-empty")
        unknown = set(self.consumes_targets) - set(_WELL_FORMED_TARGETS)
        if unknown:
            raise ValueError(f"backend category {self.category} consumes unknown targets: {sorted(unknown)}")
        if not self.consumes_targets:
            raise ValueError(f"backend category {self.category} must consume at least one target")
        if len(self.consumes_targets) != len(set(self.consumes_targets)):
            raise ValueError(f"backend category {self.category} consumes duplicate targets")

    def consumes_target(self, target: str) -> bool:
        return target in self.consumes_targets

    def to_dict(self) -> dict[str, Any]:
        return {
            "category": self.category,
            "summary": self.summary,
            "consumesTargets": list(self.consumes_targets),
            "consumes": self.consumes,
            "produces": self.produces,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "BackendCategoryStub":
        if not isinstance(data, Mapping):
            raise ValueError("backend category stub must be a mapping")
        targets = data.get("consumesTargets")
        if not isinstance(targets, list):
            raise ValueError("backend category stub consumesTargets must be a list")
        return cls(
            category=_require_string(data, "category", "backend category stub"),
            summary=_require_string(data, "summary", "backend category stub"),
            consumes_targets=tuple(targets),
            consumes=_require_string(data, "consumes", "backend category stub"),
            produces=_require_string(data, "produces", "backend category stub"),
        )


# The catalog of backend categories. Each is a posture statement of what a
# category of external tools would take in and (externally) produce — never a
# claim that any such tool has been run.
BACKEND_CATEGORY_STUBS: tuple[BackendCategoryStub, ...] = (
    BackendCategoryStub(
        category=CATEGORY_REACHABILITY,
        summary=(
            "Reachability / forward-invariance analysis (reachable-set or "
            "Hamilton-Jacobi-style tools)."
        ),
        consumes_targets=(
            "continuous-barrier",
            "discrete-barrier",
            "generic-continuous",
            "generic-discrete",
            "obligation-only",
        ),
        consumes=(
            "the dynamics, the safe set, and the obligation's region as a "
            "set-invariance / avoidance query"
        ),
        produces=(
            "an over-approximated reachable set whose containment an external "
            "tool would have to settle the obligation with"
        ),
    ),
    BackendCategoryStub(
        category=CATEGORY_SOS_SYNTHESIS,
        summary="Sum-of-squares certificate synthesis over polynomial data.",
        consumes_targets=(
            "continuous-lyapunov",
            "discrete-lyapunov",
            "continuous-barrier",
            "discrete-barrier",
        ),
        consumes=(
            "the polynomial dynamics, candidate, and obligation expression as an "
            "SOS feasibility program"
        ),
        produces=(
            "an SOS multiplier certificate that an external solver would still "
            "have to verify"
        ),
    ),
    BackendCategoryStub(
        category=CATEGORY_DEDUCTIVE_PROVER,
        summary="Deductive theorem proving over real arithmetic / hybrid programs.",
        consumes_targets=_WELL_FORMED_TARGETS,
        consumes="the obligation, its assumptions, and the dynamics as a logical sequent",
        produces=(
            "a machine-checkable proof term an external kernel would still have "
            "to accept"
        ),
    ),
)


@dataclass(frozen=True)
class ObligationAdapterStub:
    """How one backend category would consume one obligation. Never a discharge.

    For a Tier-3 robust obligation (quantified over a bounded disturbance set),
    ``robust`` is set and ``disturbance_parameters`` / ``disturbance_assumption_ids``
    record the disturbance set the obligation ranges over -- the shape an external
    backend must handle as a set-valued/robust query. A nominal obligation leaves
    these empty and serializes exactly as before. The flag is descriptive only; a
    robust stub still discharges nothing.
    """

    obligation_id: str
    category: str
    target: str
    applicable: bool
    required_shape_features: tuple[str, ...]
    note: str = _STUB_NOTE
    discharges: bool = False
    robust: bool = False
    disturbance_parameters: tuple[str, ...] = ()
    disturbance_assumption_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.obligation_id:
            raise ValueError("obligation adapter stub obligation_id must be non-empty")
        if self.category not in BACKEND_CATEGORIES:
            raise ValueError(f"unknown backend category: {self.category!r}")
        if self.target not in OBLIGATION_TARGETS:
            raise ValueError(f"unknown obligation target: {self.target!r}")
        unknown = set(self.required_shape_features) - set(OBLIGATION_SHAPE_FEATURES)
        if unknown:
            raise ValueError(f"unknown required obligation shapes: {sorted(unknown)}")
        if self.discharges:
            raise ValueError("adapter stubs never discharge an obligation")
        if not self.note:
            raise ValueError("adapter stub note must be non-empty")
        for label, names in (
            ("disturbance_parameters", self.disturbance_parameters),
            ("disturbance_assumption_ids", self.disturbance_assumption_ids),
        ):
            if any(not isinstance(name, str) or not name for name in names):
                raise ValueError(f"adapter stub {label} must be non-empty strings")
            if len(names) != len(set(names)):
                raise ValueError(f"adapter stub {label} must be unique")
        if self.robust:
            if not self.disturbance_parameters:
                raise ValueError(
                    "a robust adapter stub must name the disturbance parameter(s) it "
                    "quantifies over"
                )
            if not self.disturbance_assumption_ids:
                raise ValueError(
                    "a robust adapter stub must cite the disturbance-bound assumption(s)"
                )
        elif self.disturbance_parameters or self.disturbance_assumption_ids:
            raise ValueError(
                "a nominal adapter stub must not name a disturbance set"
            )

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "obligationId": self.obligation_id,
            "category": self.category,
            "target": self.target,
            "applicable": self.applicable,
            "requiredShapeFeatures": list(self.required_shape_features),
            "discharges": self.discharges,
            "note": self.note,
        }
        if self.robust:
            payload["robust"] = True
            payload["disturbanceParameters"] = list(self.disturbance_parameters)
            payload["disturbanceAssumptionIds"] = list(self.disturbance_assumption_ids)
        return payload

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "ObligationAdapterStub":
        if not isinstance(data, Mapping):
            raise ValueError("obligation adapter stub must be a mapping")
        features = data.get("requiredShapeFeatures")
        if not isinstance(features, list):
            raise ValueError("obligation adapter stub requiredShapeFeatures must be a list")
        applicable = data.get("applicable")
        if not isinstance(applicable, bool):
            raise ValueError("obligation adapter stub applicable must be a bool")
        parameters = data.get("disturbanceParameters", [])
        assumption_ids = data.get("disturbanceAssumptionIds", [])
        if not isinstance(parameters, list) or not isinstance(assumption_ids, list):
            raise ValueError(
                "obligation adapter stub disturbance descriptors must be lists"
            )
        return cls(
            obligation_id=_require_string(data, "obligationId", "obligation adapter stub"),
            category=_require_string(data, "category", "obligation adapter stub"),
            target=_require_string(data, "target", "obligation adapter stub"),
            applicable=applicable,
            required_shape_features=tuple(features),
            note=data.get("note", _STUB_NOTE),
            discharges=bool(data.get("discharges", False)),
            robust=bool(data.get("robust", False)),
            disturbance_parameters=tuple(parameters),
            disturbance_assumption_ids=tuple(assumption_ids),
        )


@dataclass(frozen=True)
class AdapterStubReport:
    """The package's full adapter-stub inventory for one problem."""

    problem_id: str
    categories: tuple[BackendCategoryStub, ...]
    stubs: tuple[ObligationAdapterStub, ...]
    schema_version: str = ADAPTER_STUB_SCHEMA_VERSION
    note: str = _REPORT_NOTE

    def __post_init__(self) -> None:
        if self.schema_version != ADAPTER_STUB_SCHEMA_VERSION:
            raise ValueError(f"adapter stub report schema must be {ADAPTER_STUB_SCHEMA_VERSION!r}")
        if not self.problem_id:
            raise ValueError("adapter stub report problem_id must be non-empty")
        if not self.categories:
            raise ValueError("adapter stub report must list backend categories")
        category_names = [category.category for category in self.categories]
        if len(category_names) != len(set(category_names)):
            raise ValueError("adapter stub report category names must be unique")
        known_categories = set(category_names)
        for stub in self.stubs:
            if stub.category not in known_categories:
                raise ValueError(
                    f"adapter stub for {stub.obligation_id} names uncatalogued "
                    f"category {stub.category!r}"
                )
        if not self.note:
            raise ValueError("adapter stub report note must be non-empty")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schemaVersion": self.schema_version,
            "problemId": self.problem_id,
            "note": self.note,
            "categories": [category.to_dict() for category in self.categories],
            "stubs": [stub.to_dict() for stub in self.stubs],
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "AdapterStubReport":
        if not isinstance(data, Mapping):
            raise ValueError("adapter stub report payload must be a mapping")
        categories = data.get("categories")
        if not isinstance(categories, list):
            raise ValueError("adapter stub report categories must be a list")
        stubs = data.get("stubs")
        if not isinstance(stubs, list):
            raise ValueError("adapter stub report stubs must be a list")
        return cls(
            problem_id=_require_string(data, "problemId", "adapter stub report"),
            categories=tuple(BackendCategoryStub.from_dict(item) for item in categories),
            stubs=tuple(ObligationAdapterStub.from_dict(item) for item in stubs),
            schema_version=data.get("schemaVersion", ADAPTER_STUB_SCHEMA_VERSION),
            note=data.get("note", _REPORT_NOTE),
        )


def robust_obligation_disturbances(
    problem: VerificationProblem,
) -> dict[str, tuple[tuple[str, ...], tuple[str, ...]]]:
    """Map each robust obligation id to its IR-derived disturbance set.

    An obligation is robust when it cites a disturbance-bound assumption (id
    carrying the disturbance marker) whose variables range over declared problem
    parameters -- the same IR-only convention the package regime descriptor uses.
    Returns ``{obligation_id: (disturbance_parameters, disturbance_assumption_ids)}``
    for the robust obligations only; nominal obligations are absent. Pure
    classification; it records the obligation shape, it discharges nothing.
    """

    disturbance_assumptions = {
        assumption.id: assumption
        for assumption in problem.assumptions
        if _DISTURBANCE_ASSUMPTION_MARKER in assumption.id
    }
    if not disturbance_assumptions:
        return {}
    parameter_names = {parameter.name for parameter in problem.parameters}

    robust: dict[str, tuple[tuple[str, ...], tuple[str, ...]]] = {}
    for obligation in problem.obligations:
        cited = tuple(
            assumption_id
            for assumption_id in obligation.assumption_ids
            if assumption_id in disturbance_assumptions
        )
        if not cited:
            continue
        parameters = tuple(
            dict.fromkeys(
                name
                for assumption_id in cited
                for name in disturbance_assumptions[assumption_id].variables
                if name in parameter_names
            )
        )
        # A cited disturbance bound that ranges no declared parameter is not a
        # robust quantification in any honest sense; treat the obligation as nominal.
        if not parameters:
            continue
        robust[obligation.id] = (parameters, cited)
    return robust


def obligation_adapter_stubs(problem: VerificationProblem) -> AdapterStubReport:
    """Derive non-discharging adapter stubs for every obligation in ``problem``.

    For each obligation, emits one stub per backend category that could consume
    its target, naming the category, the obligation's classified target, and the
    obligation shape (region-scoping, assumptions, strict comparison, ...) the
    category would have to handle. A Tier-3 robust obligation (quantified over a
    bounded disturbance set) additionally carries a robustness flag and the
    disturbance set it ranges over, derived only from IR data. Malformed targets
    yield no applicable stub — no backend category can consume an ill-posed
    obligation. Nothing here is a discharge.
    """

    classifications = classifications_by_obligation(problem)
    robust_disturbances = robust_obligation_disturbances(problem)
    stubs: list[ObligationAdapterStub] = []
    for obligation in problem.obligations:
        classification = classifications[obligation.id]
        well_formed = classification.malformed_reason is None
        parameters, assumption_ids = robust_disturbances.get(obligation.id, ((), ()))
        is_robust = bool(parameters)
        for category in BACKEND_CATEGORY_STUBS:
            applicable = well_formed and category.consumes_target(classification.target)
            if not applicable:
                continue
            stubs.append(
                ObligationAdapterStub(
                    obligation_id=obligation.id,
                    category=category.category,
                    target=classification.target,
                    applicable=True,
                    required_shape_features=classification.shape_features,
                    robust=is_robust,
                    disturbance_parameters=parameters,
                    disturbance_assumption_ids=assumption_ids,
                )
            )
    return AdapterStubReport(
        problem_id=problem.id,
        categories=BACKEND_CATEGORY_STUBS,
        stubs=tuple(stubs),
    )


def _require_string(data: Mapping[str, Any], key: str, owner: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(f"{owner} {key} is invalid")
    return value
