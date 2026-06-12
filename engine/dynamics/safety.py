"""Safety sets and certificate *candidates* with explicit proof obligations.

Design spec: `docs/safety-certificates.md`. Rigor discipline (see
`docs/VISION.md` §7): everything this module can check on its own is either
a symbolic identity or a *measured*, sampled result at rigor level 1. A
clean sample is evidence, not a certificate; a found violation is a genuine
counterexample. Nothing here certifies or proves, and every sampled result
is labeled ``rigor="measured"``.

Conventions:

- a region is a sublevel set ``{x : g(x) <= level}`` with signed margin
  ``level - g(x)`` (nonnegative inside);
- a barrier candidate's candidate-invariant/safe region is ``{B <= 0}``;
- a Lyapunov candidate must vanish at its equilibrium, be positive on its
  domain away from the equilibrium, and not increase along the flow.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

import numpy as np
import sympy as sp

from engine.dynamics.first_order import FirstOrderSystem

_MEASURED_NOTE = (
    "sampled check only: a clean sample is evidence, not a certificate; "
    "a violation is a genuine counterexample"
)


def _evaluator(
    state: tuple[sp.Symbol, ...],
    expression: sp.Expr,
    substitutions: Mapping[sp.Symbol, float] | None,
):
    resolved = sp.sympify(expression).subs(substitutions or {})
    unresolved = resolved.free_symbols - set(state)
    if unresolved:
        names = ", ".join(sorted(symbol.name for symbol in unresolved))
        raise ValueError(f"unresolved symbols: {names}")
    compiled = sp.lambdify(state, resolved, modules="numpy")

    def evaluate(points: np.ndarray) -> np.ndarray:
        array = np.atleast_2d(np.asarray(points, dtype=float))
        if array.shape[1] != len(state):
            raise ValueError("points must match the state dimension")
        values = compiled(*(array[:, index] for index in range(array.shape[1])))
        result = np.asarray(values, dtype=float)
        if result.shape == ():
            return np.full(array.shape[0], float(result))
        return result.reshape(array.shape[0])

    return evaluate


@dataclass(frozen=True)
class SublevelSet:
    """The region ``{x : expression <= level}`` over the given state symbols."""

    state: tuple[sp.Symbol, ...]
    expression: sp.Expr
    level: float = 0.0
    name: str = "sublevel-set"

    def __post_init__(self) -> None:
        if not self.state:
            raise ValueError("state must be non-empty")
        extra = sp.sympify(self.expression).free_symbols - set(self.state)
        if extra:
            names = ", ".join(sorted(symbol.name for symbol in extra))
            raise ValueError(f"expression has symbols outside the state: {names}")

    def margin_expression(self) -> sp.Expr:
        """Signed margin ``level - expression``; nonnegative inside."""

        return sp.sympify(self.level) - self.expression

    def margin(
        self,
        points: Sequence[float] | np.ndarray,
        substitutions: Mapping[sp.Symbol, float] | None = None,
    ) -> np.ndarray:
        return _evaluator(self.state, self.margin_expression(), substitutions)(
            np.asarray(points, dtype=float)
        )

    def contains(
        self,
        points: Sequence[float] | np.ndarray,
        substitutions: Mapping[sp.Symbol, float] | None = None,
        *,
        tolerance: float = 0.0,
    ) -> np.ndarray:
        return self.margin(points, substitutions) >= -tolerance


@dataclass(frozen=True)
class UnsafeSetReport:
    name: str
    entered: bool
    first_entry_time: float | None
    max_margin: float  # largest margin of the unsafe set seen (>= 0 means entered)


@dataclass(frozen=True)
class TrajectorySafetyReport:
    """Measured (rigor level 1) safety summary of one trajectory."""

    rigor: str
    min_safe_margin: float
    min_safe_margin_time: float
    stayed_safe: bool
    unsafe_sets: tuple[UnsafeSetReport, ...]
    note: str


@dataclass(frozen=True)
class SafetySpecification:
    """Safe set, unsafe sets/obstacles, and optional initial set, as data."""

    state: tuple[sp.Symbol, ...]
    safe_set: SublevelSet
    unsafe_sets: tuple[SublevelSet, ...] = ()
    initial_set: SublevelSet | None = None

    def __post_init__(self) -> None:
        regions = (self.safe_set, *self.unsafe_sets) + (
            (self.initial_set,) if self.initial_set is not None else ()
        )
        for region in regions:
            if region.state != self.state:
                raise ValueError("all regions must share the specification state")

    def trajectory_report(
        self,
        time: np.ndarray,
        states: np.ndarray,
        substitutions: Mapping[sp.Symbol, float] | None = None,
    ) -> TrajectorySafetyReport:
        """Measured margins along one trajectory. Evidence, not a guarantee."""

        time_array = np.asarray(time, dtype=float)
        state_array = np.atleast_2d(np.asarray(states, dtype=float))
        if state_array.shape[0] != time_array.shape[0]:
            raise ValueError("time and states must have matching sample counts")

        safe_margins = self.safe_set.margin(state_array, substitutions)
        worst_index = int(np.argmin(safe_margins))

        unsafe_reports = []
        for region in self.unsafe_sets:
            margins = region.margin(state_array, substitutions)
            inside = margins >= 0.0
            entered = bool(np.any(inside))
            unsafe_reports.append(
                UnsafeSetReport(
                    name=region.name,
                    entered=entered,
                    first_entry_time=(
                        float(time_array[int(np.argmax(inside))]) if entered else None
                    ),
                    max_margin=float(np.max(margins)),
                )
            )

        stayed_safe = bool(safe_margins[worst_index] >= 0.0) and not any(
            report.entered for report in unsafe_reports
        )
        return TrajectorySafetyReport(
            rigor="measured",
            min_safe_margin=float(safe_margins[worst_index]),
            min_safe_margin_time=float(time_array[worst_index]),
            stayed_safe=stayed_safe,
            unsafe_sets=tuple(unsafe_reports),
            note=_MEASURED_NOTE,
        )


def lie_derivative(function: sp.Expr, system: FirstOrderSystem) -> sp.Expr:
    """Derivative of ``function`` along the flow: d/dt + grad . f."""

    expression = sp.sympify(function)
    extra = expression.free_symbols - set(system.state) - set(system.parameters) - {system.time}
    if extra:
        names = ", ".join(sorted(symbol.name for symbol in extra))
        raise ValueError(f"function has symbols outside the system: {names}")
    return sp.simplify(
        sp.diff(expression, system.time)
        + sum(
            sp.diff(expression, state) * rhs
            for state, rhs in zip(system.state, system.rhs, strict=True)
        )
    )


@dataclass(frozen=True)
class ProofObligation:
    """The claim ``expression <comparison> 0`` on ``region`` (or everywhere).

    The engine emits these for external sound methods to discharge; it can
    only *sample* them itself (see :func:`sample_obligation`).
    """

    name: str
    state: tuple[sp.Symbol, ...]
    expression: sp.Expr
    comparison: str  # one of "<=", "<", ">=", ">"
    region: SublevelSet | None = None
    excluded_point: tuple[float, ...] | None = None
    description: str = ""

    def __post_init__(self) -> None:
        if self.comparison not in ("<=", "<", ">=", ">"):
            raise ValueError("comparison must be one of <=, <, >=, >")
        if self.region is not None and self.region.state != self.state:
            raise ValueError("region must share the obligation state")
        if self.excluded_point is not None and len(self.excluded_point) != len(self.state):
            raise ValueError("excluded_point must match the state dimension")


@dataclass(frozen=True)
class ObligationSample:
    """Measured (rigor level 1) sampling of a proof obligation."""

    obligation: str
    rigor: str
    satisfied: bool
    worst_value: float
    worst_point: tuple[float, ...]
    sample_count: int
    note: str


def grid_points(
    bounds: Sequence[tuple[float, float]],
    counts: Sequence[int],
) -> np.ndarray:
    """Deterministic rectangular grid, shape (prod(counts), len(bounds))."""

    if len(bounds) != len(counts):
        raise ValueError("bounds and counts must have the same length")
    if any(count < 2 for count in counts):
        raise ValueError("each count must be at least 2")
    axes = [
        np.linspace(low, high, count)
        for (low, high), count in zip(bounds, counts, strict=True)
    ]
    mesh = np.meshgrid(*axes, indexing="ij")
    return np.stack([axis.reshape(-1) for axis in mesh], axis=1)


def sample_obligation(
    obligation: ProofObligation,
    points: np.ndarray,
    substitutions: Mapping[sp.Symbol, float] | None = None,
) -> ObligationSample:
    """Evaluate an obligation on sample points restricted to its region.

    Returns a *measured* result. A satisfied sample is evidence only; a
    violated sample contains a genuine counterexample at ``worst_point``.
    """

    array = np.atleast_2d(np.asarray(points, dtype=float))
    if obligation.region is not None:
        array = array[obligation.region.margin(array, substitutions) >= 0.0]
    if obligation.excluded_point is not None:
        excluded = np.asarray(obligation.excluded_point, dtype=float)
        array = array[~np.all(array == excluded, axis=1)]
    if array.shape[0] == 0:
        raise ValueError("no sample points fall inside the obligation region")

    values = _evaluator(obligation.state, obligation.expression, substitutions)(array)
    # Canonical form: violation magnitude is how far the comparison fails.
    if obligation.comparison in ("<=", "<"):
        worst_index = int(np.argmax(values))
        strict = obligation.comparison == "<"
        satisfied = bool(values[worst_index] < 0.0 or (not strict and values[worst_index] <= 0.0))
    else:
        worst_index = int(np.argmin(values))
        strict = obligation.comparison == ">"
        satisfied = bool(values[worst_index] > 0.0 or (not strict and values[worst_index] >= 0.0))

    return ObligationSample(
        obligation=obligation.name,
        rigor="measured",
        satisfied=satisfied,
        worst_value=float(values[worst_index]),
        worst_point=tuple(float(value) for value in array[worst_index]),
        sample_count=int(array.shape[0]),
        note=_MEASURED_NOTE,
    )


@dataclass(frozen=True)
class LyapunovCandidate:
    """A candidate Lyapunov *function* (stability certificate candidate).

    Not to be confused with finite-time Lyapunov *exponents*
    (`engine/dynamics/diagnostics.py`), which are chaos diagnostics.
    """

    state: tuple[sp.Symbol, ...]
    function: sp.Expr
    equilibrium: tuple[float, ...]
    domain: SublevelSet | None = None
    name: str = "lyapunov-candidate"

    def __post_init__(self) -> None:
        if len(self.equilibrium) != len(self.state):
            raise ValueError("equilibrium must match the state dimension")
        if self.domain is not None and self.domain.state != self.state:
            raise ValueError("domain must share the candidate state")

    def value_at_equilibrium(self) -> sp.Expr:
        point = dict(zip(self.state, self.equilibrium, strict=True))
        return sp.simplify(sp.sympify(self.function).subs(point))

    def derivative_along(self, system: FirstOrderSystem) -> sp.Expr:
        if system.state != self.state:
            raise ValueError("system state must match the candidate state")
        return lie_derivative(self.function, system)

    def proof_obligations(self, system: FirstOrderSystem) -> tuple[ProofObligation, ...]:
        return (
            ProofObligation(
                name=f"{self.name}:equilibrium-value",
                state=self.state,
                expression=self.value_at_equilibrium(),
                comparison="<=",
                description="V vanishes at the equilibrium (with >= 0 nearby, "
                "checked via the positivity obligation); here V(x*) <= 0 "
                "combined with positivity off the equilibrium forces V(x*) = 0",
            ),
            ProofObligation(
                name=f"{self.name}:positivity",
                state=self.state,
                expression=-sp.sympify(self.function),
                comparison="<",
                region=self.domain,
                excluded_point=tuple(self.equilibrium),
                description="V > 0 on the domain away from the equilibrium",
            ),
            ProofObligation(
                name=f"{self.name}:decrease",
                state=self.state,
                expression=self.derivative_along(system),
                comparison="<=",
                region=self.domain,
                description="dV/dt <= 0 along the closed-loop flow on the domain",
            ),
        )


@dataclass(frozen=True)
class BarrierCandidate:
    """A candidate barrier function; candidate-safe region is ``{B <= 0}``.

    The non-increase obligation is stated on all of ``{B <= 0}``, a
    sufficient condition stronger than the boundary-only requirement.
    A sublevel invariant-set candidate is this same object.
    """

    state: tuple[sp.Symbol, ...]
    function: sp.Expr
    name: str = "barrier-candidate"

    def candidate_region(self) -> SublevelSet:
        return SublevelSet(
            state=self.state,
            expression=self.function,
            level=0.0,
            name=f"{self.name}:region",
        )

    def derivative_along(self, system: FirstOrderSystem) -> sp.Expr:
        if system.state != self.state:
            raise ValueError("system state must match the candidate state")
        return lie_derivative(self.function, system)

    def proof_obligations(
        self,
        system: FirstOrderSystem,
        specification: SafetySpecification | None = None,
    ) -> tuple[ProofObligation, ...]:
        obligations = [
            ProofObligation(
                name=f"{self.name}:non-increase",
                state=self.state,
                expression=self.derivative_along(system),
                comparison="<=",
                region=self.candidate_region(),
                description="dB/dt <= 0 on {B <= 0} (sufficient for invariance)",
            )
        ]
        if specification is not None:
            if specification.state != self.state:
                raise ValueError("specification state must match the candidate state")
            if specification.initial_set is not None:
                obligations.append(
                    ProofObligation(
                        name=f"{self.name}:initial-containment",
                        state=self.state,
                        expression=sp.sympify(self.function),
                        comparison="<=",
                        region=specification.initial_set,
                        description="B <= 0 on the initial set",
                    )
                )
            for region in specification.unsafe_sets:
                obligations.append(
                    ProofObligation(
                        name=f"{self.name}:excludes:{region.name}",
                        state=self.state,
                        expression=sp.sympify(self.function),
                        comparison=">",
                        region=region,
                        description="B > 0 on the unsafe set",
                    )
                )
        return tuple(obligations)


__all__ = [
    "BarrierCandidate",
    "LyapunovCandidate",
    "ObligationSample",
    "ProofObligation",
    "SafetySpecification",
    "SublevelSet",
    "TrajectorySafetyReport",
    "UnsafeSetReport",
    "grid_points",
    "lie_derivative",
    "sample_obligation",
]
