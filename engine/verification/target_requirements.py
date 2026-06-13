"""Target-specific structural checks for future verification adapters."""

from __future__ import annotations

from dataclasses import dataclass

import sympy as sp

from engine.verification.capabilities import (
    AdapterCapabilities,
    classifications_by_obligation,
)
from engine.verification.diagnostics import VerificationDiagnostic
from engine.verification.ir import (
    CandidateSpec,
    DynamicsSpec,
    ExpressionSpec,
    ObligationSpec,
    RegionSpec,
    VerificationProblem,
)

SOS_POLYNOMIAL_ADAPTER = AdapterCapabilities(
    adapter="sos-polynomial-certificate",
    supported_targets=(
        "continuous-lyapunov",
        "discrete-lyapunov",
        "continuous-barrier",
        "discrete-barrier",
    ),
    supports_discharge=True,
)


@dataclass(frozen=True)
class PolynomialRequirementReport:
    """Structural compatibility report for one obligation target.

    This is only a pre-adapter filter. It is not a proof attempt and cannot
    certify a candidate.
    """

    obligation_id: str
    compatible: bool
    non_polynomial_fields: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.compatible and self.non_polynomial_fields:
            raise ValueError("compatible reports must not list failures")
        if not self.compatible and not self.non_polynomial_fields:
            raise ValueError("incompatible reports must explain the failures")

    def to_dict(self) -> dict[str, object]:
        return {
            "obligationId": self.obligation_id,
            "compatible": self.compatible,
            "nonPolynomialFields": list(self.non_polynomial_fields),
        }


def sos_polynomial_requirement_diagnostics(
    problem: VerificationProblem,
) -> tuple[VerificationDiagnostic, ...]:
    """Return diagnostics for an SOS-style polynomial certificate target.

    The checker rejects targets or expressions that a polynomial SOS adapter
    could not even attempt. It deliberately emits no success result for
    structurally compatible obligations.
    """

    classifications = classifications_by_obligation(problem)
    candidates_by_obligation = _candidates_by_obligation(problem)
    regions_by_id = {region.id: region for region in problem.regions}
    known_symbol_names = _known_symbol_names(problem)
    diagnostics: list[VerificationDiagnostic] = []

    for obligation in problem.obligations:
        classification = classifications[obligation.id]
        details = {
            "adapter": SOS_POLYNOMIAL_ADAPTER.adapter,
            "classification": classification.to_dict(),
        }

        if classification.malformed_reason is not None:
            diagnostics.append(
                VerificationDiagnostic(
                    code="sos.target_malformed",
                    severity="error",
                    status="malformed",
                    message=classification.malformed_reason,
                    location=f"obligations.{obligation.id}",
                    obligation_id=obligation.id,
                    details=details,
                )
            )
            continue

        if not SOS_POLYNOMIAL_ADAPTER.supports(classification):
            diagnostics.append(
                VerificationDiagnostic(
                    code="sos.target_unsupported",
                    severity="warning",
                    status="unsupported",
                    message="SOS polynomial checks only apply to certificate obligations.",
                    location=f"obligations.{obligation.id}",
                    obligation_id=obligation.id,
                    details=details,
                )
            )
            continue

        report = _polynomial_requirement_report(
            problem=problem,
            obligation=obligation,
            candidates=candidates_by_obligation[obligation.id],
            regions_by_id=regions_by_id,
            known_symbol_names=known_symbol_names,
        )
        if not report.compatible:
            diagnostics.append(
                VerificationDiagnostic(
                    code="sos.polynomial_requirement",
                    severity="warning",
                    status="unsupported",
                    message=(
                        "SOS polynomial adapters require polynomial dynamics, "
                        "regions, candidates, and obligation expressions."
                    ),
                    location=f"obligations.{obligation.id}",
                    obligation_id=obligation.id,
                    details={**details, "requirement": report.to_dict()},
                )
            )

    return tuple(diagnostics)


def _polynomial_requirement_report(
    *,
    problem: VerificationProblem,
    obligation: ObligationSpec,
    candidates: tuple[CandidateSpec, ...],
    regions_by_id: dict[str, RegionSpec],
    known_symbol_names: set[str],
) -> PolynomialRequirementReport:
    failures: list[str] = []
    if problem.dynamics is not None:
        failures.extend(_non_polynomial_dynamics(problem.dynamics, known_symbol_names))
    else:
        failures.append("dynamics")

    if not _is_polynomial(obligation.expression, known_symbol_names):
        failures.append(f"obligations.{obligation.id}.expression")

    for candidate in candidates:
        if not _is_polynomial(candidate.expression, known_symbol_names):
            failures.append(f"candidates.{candidate.id}.expression")
        if candidate.region_id is not None:
            _check_region(candidate.region_id, regions_by_id, known_symbol_names, failures)

    if obligation.region_id is not None:
        _check_region(obligation.region_id, regions_by_id, known_symbol_names, failures)

    unique_failures = tuple(dict.fromkeys(failures))
    return PolynomialRequirementReport(
        obligation_id=obligation.id,
        compatible=not unique_failures,
        non_polynomial_fields=unique_failures,
    )


def _non_polynomial_dynamics(
    dynamics: DynamicsSpec,
    known_symbol_names: set[str],
) -> tuple[str, ...]:
    fields = []
    label = "rhs" if dynamics.kind == "continuous" else "update"
    for index, expression in enumerate(dynamics.rhs):
        if not _is_polynomial(expression, known_symbol_names):
            fields.append(f"dynamics.{label}.{index}")
    return tuple(fields)


def _check_region(
    region_id: str,
    regions_by_id: dict[str, RegionSpec],
    known_symbol_names: set[str],
    failures: list[str],
) -> None:
    region = regions_by_id.get(region_id)
    if region is None:
        failures.append(f"regions.{region_id}")
        return
    if not _is_polynomial(region.expression, known_symbol_names):
        failures.append(f"regions.{region_id}.expression")


def _is_polynomial(
    expression: ExpressionSpec,
    known_symbol_names: set[str],
) -> bool:
    expr = sp.sympify(expression.source)
    unknown = {symbol.name for symbol in expr.free_symbols} - known_symbol_names
    if unknown:
        return False
    return bool(expr.is_polynomial(*sorted(expr.free_symbols, key=lambda symbol: symbol.name)))


def _known_symbol_names(problem: VerificationProblem) -> set[str]:
    names = {variable.name for variable in problem.variables}
    names.update(parameter.name for parameter in problem.parameters)
    if problem.dynamics is not None:
        names.add(problem.dynamics.time_variable)
    if problem.open_loop_dynamics is not None:
        names.add(problem.open_loop_dynamics.time_variable)
    return names


def _candidates_by_obligation(
    problem: VerificationProblem,
) -> dict[str, tuple[CandidateSpec, ...]]:
    mapping: dict[str, list[CandidateSpec]] = {
        obligation.id: [] for obligation in problem.obligations
    }
    for candidate in problem.candidates:
        for obligation_id in candidate.obligation_ids:
            mapping[obligation_id].append(candidate)
    return {
        obligation_id: tuple(candidates)
        for obligation_id, candidates in mapping.items()
    }
