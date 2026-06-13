"""Adapter from safety certificate candidates to verification-problem IR."""

from __future__ import annotations

import re
from typing import Any, Mapping, Sequence

import sympy as sp

from engine.dynamics.first_order import FirstOrderSystem
from engine.dynamics.safety import (
    BarrierCandidate,
    LyapunovCandidate,
    ProofObligation,
    SafetySpecification,
    SublevelSet,
)
from engine.verification.ir import (
    AssumptionSpec,
    CandidateSpec,
    ObligationSpec,
    ParameterSpec,
    RegionSpec,
    VariableSpec,
    VerificationProblem,
    problem_from_parts,
)
from engine.verification.sympy_codec import expression_spec
from engine.verification.system_codec import dynamics_spec_from_system

_SOURCE = "engine.dynamics.safety"
_DEFAULT_NOTE = (
    "Verification-problem IR only: obligations require external sound discharge; "
    "sampled checks are measured evidence, not certification."
)


def _slug(text: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", text).strip("-").lower()
    return slug or "item"


def _unique_slug(text: str, used: set[str]) -> str:
    base = _slug(text)
    candidate = base
    index = 2
    while candidate in used:
        candidate = f"{base}-{index}"
        index += 1
    used.add(candidate)
    return candidate


def _region_key(region: SublevelSet) -> tuple[str, str, float]:
    return (region.name, sp.srepr(sp.sympify(region.expression)), float(region.level))


def _metadata(metadata: Mapping[str, Any] | None) -> dict[str, Any]:
    payload = {
        "status": "candidate",
        "note": _DEFAULT_NOTE,
    }
    if metadata is not None:
        payload.update(dict(metadata))
    return payload


def _state_from_obligations(obligations: Sequence[ProofObligation]) -> tuple[sp.Symbol, ...]:
    if not obligations:
        raise ValueError("at least one proof obligation is required")
    state = obligations[0].state
    for obligation in obligations:
        if obligation.state != state:
            raise ValueError("all obligations must share the same state")
    return state


def _assumption_from_parameter(symbol: sp.Symbol) -> AssumptionSpec | None:
    comparison: str | None = None
    label: str | None = None
    if symbol.is_positive:
        comparison = ">"
        label = "positive"
    elif symbol.is_nonnegative:
        comparison = ">="
        label = "nonnegative"
    elif symbol.is_negative:
        comparison = "<"
        label = "negative"
    elif symbol.is_nonpositive:
        comparison = "<="
        label = "nonpositive"
    elif symbol.is_nonzero:
        comparison = "!="
        label = "nonzero"

    if comparison is None or label is None:
        return None
    return AssumptionSpec(
        id=_slug(f"parameter-{symbol.name}-{label}"),
        name=f"{symbol.name} is {label}",
        role="parameter-domain",
        expression=expression_spec(symbol),
        comparison=comparison,
        rhs=0.0,
        variables=(symbol.name,),
        description="Parameter-domain assumption made explicit for external discharge.",
    )


def _parameter_assumptions(
    symbols: Sequence[sp.Symbol],
    explicit: Sequence[AssumptionSpec],
) -> tuple[AssumptionSpec, ...]:
    assumptions = list(explicit)
    used = {assumption.id for assumption in assumptions}
    for symbol in symbols:
        assumption = _assumption_from_parameter(symbol)
        if assumption is not None and assumption.id not in used:
            assumptions.append(assumption)
            used.add(assumption.id)
    return tuple(assumptions)


def verification_problem_from_obligations(
    name: str,
    obligations: Sequence[ProofObligation],
    *,
    system: FirstOrderSystem | None = None,
    candidate: LyapunovCandidate | BarrierCandidate | None = None,
    specification: SafetySpecification | None = None,
    substitutions: Mapping[sp.Symbol, float] | None = None,
    assumptions: Sequence[AssumptionSpec] = (),
    metadata: Mapping[str, Any] | None = None,
) -> VerificationProblem:
    """Package proof obligations as a backend-agnostic verification problem.

    ``system`` is the (closed-loop) model the obligations were derived along
    and is encoded as the problem dynamics; ``candidate`` is the certificate
    candidate that generated the obligations and is linked to all of them.
    The resulting problem records claims for external discharge; it does not
    include proof results and does not mark any obligation certified.
    """

    obligation_tuple = tuple(obligations)
    state = _state_from_obligations(obligation_tuple)
    if specification is not None and specification.state != state:
        raise ValueError("specification state must match the obligation state")
    if system is not None and system.state != state:
        raise ValueError("system state must match the obligation state")
    if candidate is not None and candidate.state != state:
        raise ValueError("candidate state must match the obligation state")

    variables = tuple(
        VariableSpec(name=symbol.name, latex=sp.latex(symbol))
        for symbol in state
    )

    used_region_ids: set[str] = set()
    region_ids_by_key: dict[tuple[str, str, float], str] = {}
    regions: list[RegionSpec] = []

    def register_region(region: SublevelSet, role: str) -> str:
        if region.state != state:
            raise ValueError("all regions must share the obligation state")
        key = _region_key(region)
        if key in region_ids_by_key:
            return region_ids_by_key[key]
        region_id = _unique_slug(f"{role}-{region.name}", used_region_ids)
        region_ids_by_key[key] = region_id
        regions.append(
            RegionSpec(
                id=region_id,
                name=region.name,
                kind="sublevel",
                role=role,
                variables=tuple(symbol.name for symbol in state),
                expression=expression_spec(region.expression),
                level=float(region.level),
            )
        )
        return region_id

    if specification is not None:
        register_region(specification.safe_set, "safe")
        if specification.initial_set is not None:
            register_region(specification.initial_set, "initial")
        for unsafe in specification.unsafe_sets:
            register_region(unsafe, "unsafe")

    for obligation in obligation_tuple:
        if obligation.region is not None:
            register_region(obligation.region, "domain")

    free_symbols: set[sp.Symbol] = set()
    for obligation in obligation_tuple:
        free_symbols.update(sp.sympify(obligation.expression).free_symbols)
        if obligation.region is not None:
            free_symbols.update(sp.sympify(obligation.region.expression).free_symbols)
    if system is not None:
        for expression in system.rhs:
            free_symbols.update(sp.sympify(expression).free_symbols)
        free_symbols.discard(system.time)
    if candidate is not None:
        free_symbols.update(sp.sympify(candidate.function).free_symbols)
    if specification is not None:
        safety_regions = [specification.safe_set, *specification.unsafe_sets]
        if specification.initial_set is not None:
            safety_regions.append(specification.initial_set)
        for region in safety_regions:
            free_symbols.update(sp.sympify(region.expression).free_symbols)

    state_symbols = set(state)
    substitution_values = substitutions or {}
    parameter_symbols = sorted(
        (free_symbols | set(substitution_values)) - state_symbols,
        key=lambda symbol: symbol.name,
    )
    parameters = tuple(
        ParameterSpec(
            name=symbol.name,
            latex=sp.latex(symbol),
            value=(
                float(substitution_values[symbol])
                if symbol in substitution_values
                else None
            ),
        )
        for symbol in parameter_symbols
    )
    assumption_specs = _parameter_assumptions(parameter_symbols, assumptions)
    assumption_ids = tuple(assumption.id for assumption in assumption_specs)

    used_obligation_ids: set[str] = set()
    obligation_specs = []
    for obligation in obligation_tuple:
        region_id = None
        if obligation.region is not None:
            region_id = region_ids_by_key[_region_key(obligation.region)]
        obligation_specs.append(
            ObligationSpec(
                id=_unique_slug(obligation.name, used_obligation_ids),
                name=obligation.name,
                expression=expression_spec(obligation.expression),
                comparison=obligation.comparison,
                rhs=0.0,
                region_id=region_id,
                excluded_points=(
                    (tuple(float(value) for value in obligation.excluded_point),)
                    if obligation.excluded_point is not None
                    else ()
                ),
                assumption_ids=assumption_ids,
                description=obligation.description,
            )
        )

    candidates: tuple[CandidateSpec, ...] = ()
    if candidate is not None:
        if isinstance(candidate, LyapunovCandidate):
            kind = "lyapunov"
            equilibrium = tuple(float(value) for value in candidate.equilibrium)
            candidate_region = candidate.domain
        else:
            kind = "barrier"
            equilibrium = None
            candidate_region = candidate.candidate_region()
        region_id = None
        if candidate_region is not None:
            region_id = region_ids_by_key.get(_region_key(candidate_region))
        candidates = (
            CandidateSpec(
                id=_slug(candidate.name),
                name=candidate.name,
                kind=kind,
                expression=expression_spec(candidate.function),
                obligation_ids=tuple(spec.id for spec in obligation_specs),
                equilibrium=equilibrium,
                region_id=region_id,
            ),
        )

    return problem_from_parts(
        id=_slug(name),
        name=name,
        source=_SOURCE,
        variables=variables,
        parameters=parameters,
        regions=regions,
        obligations=obligation_specs,
        assumptions=assumption_specs,
        dynamics=None if system is None else dynamics_spec_from_system(system),
        candidates=candidates,
        metadata=_metadata(metadata),
    )


def verification_problem_from_barrier(
    name: str,
    system: FirstOrderSystem,
    candidate: BarrierCandidate,
    *,
    specification: SafetySpecification | None = None,
    substitutions: Mapping[sp.Symbol, float] | None = None,
    assumptions: Sequence[AssumptionSpec] = (),
    metadata: Mapping[str, Any] | None = None,
) -> VerificationProblem:
    return verification_problem_from_obligations(
        name,
        candidate.proof_obligations(system, specification),
        system=system,
        candidate=candidate,
        specification=specification,
        substitutions=substitutions,
        assumptions=assumptions,
        metadata=metadata,
    )


def verification_problem_from_lyapunov(
    name: str,
    system: FirstOrderSystem,
    candidate: LyapunovCandidate,
    *,
    substitutions: Mapping[sp.Symbol, float] | None = None,
    assumptions: Sequence[AssumptionSpec] = (),
    metadata: Mapping[str, Any] | None = None,
) -> VerificationProblem:
    return verification_problem_from_obligations(
        name,
        candidate.proof_obligations(system),
        system=system,
        candidate=candidate,
        substitutions=substitutions,
        assumptions=assumptions,
        metadata=metadata,
    )
