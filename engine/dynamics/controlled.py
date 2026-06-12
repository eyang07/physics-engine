"""Controlled first-order dynamics: dx/dt = f(t, x, u, d; params).

Design spec: `docs/controlled-dynamics.md`. The load-bearing move is
*closed-loop reduction*: substituting a symbolic feedback law ``u = pi(t, x)``
yields a plain :class:`~engine.dynamics.first_order.FirstOrderSystem`, so all
existing diagnostics (Jacobian, divergence, fixed points, linearization,
finite-time Lyapunov exponents, invariant residuals) apply to closed-loop
systems unchanged.

Admissible sets are axis-aligned boxes in v0. Rollouts *measure and report*
bound violations; they never silently clip. Saturation is an explicit
modeling decision the caller makes inside the control law (see
:meth:`Box.clip`).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Mapping, Sequence

import numpy as np
import sympy as sp

from engine.dynamics.first_order import FirstOrderSystem
from engine.numerics import integrate_fixed_step

ControlLaw = Callable[[float, np.ndarray], Sequence[float]]


@dataclass(frozen=True)
class Box:
    """An axis-aligned box of admissible values (controls or disturbances)."""

    lower: tuple[float, ...]
    upper: tuple[float, ...]

    def __post_init__(self) -> None:
        lower = tuple(float(value) for value in self.lower)
        upper = tuple(float(value) for value in self.upper)
        object.__setattr__(self, "lower", lower)
        object.__setattr__(self, "upper", upper)
        if len(lower) != len(upper):
            raise ValueError("lower and upper must have the same length")
        if not lower:
            raise ValueError("box must have at least one dimension")
        if any(lo > hi for lo, hi in zip(lower, upper, strict=True)):
            raise ValueError("lower bounds must not exceed upper bounds")

    @property
    def dimension(self) -> int:
        return len(self.lower)

    def violation(self, values: Sequence[float] | np.ndarray) -> float:
        """Largest componentwise distance outside the box; 0.0 if inside."""

        array = np.atleast_2d(np.asarray(values, dtype=float))
        if array.shape[-1] != self.dimension:
            raise ValueError("values must match the box dimension")
        lower = np.asarray(self.lower)
        upper = np.asarray(self.upper)
        below = np.clip(lower - array, 0.0, None)
        above = np.clip(array - upper, 0.0, None)
        return float(np.max(np.maximum(below, above)))

    def contains(self, values: Sequence[float] | np.ndarray, *, tolerance: float = 0.0) -> bool:
        return self.violation(values) <= tolerance

    def clip(self, values: Sequence[float] | np.ndarray) -> np.ndarray:
        array = np.asarray(values, dtype=float)
        if array.shape[-1] != self.dimension:
            raise ValueError("values must match the box dimension")
        return np.clip(array, np.asarray(self.lower), np.asarray(self.upper))


@dataclass(frozen=True)
class ControlledFirstOrderSystem:
    """A finite-dimensional controlled system dx/dt = f(t, x, u, d; params)."""

    state: tuple[sp.Symbol, ...]
    controls: tuple[sp.Symbol, ...]
    rhs: tuple[sp.Expr, ...]
    disturbances: tuple[sp.Symbol, ...] = ()
    parameters: tuple[sp.Symbol, ...] = ()
    time: sp.Symbol = sp.Symbol("t", real=True)
    control_bounds: Box | None = None
    disturbance_bounds: Box | None = None

    def __post_init__(self) -> None:
        if len(self.state) != len(self.rhs):
            raise ValueError("state and rhs must have the same length")
        if not self.controls:
            raise ValueError("controls must be non-empty; use FirstOrderSystem otherwise")
        groups = (self.state, self.controls, self.disturbances, self.parameters, (self.time,))
        symbols = [symbol for group in groups for symbol in group]
        if len(symbols) != len(set(symbols)):
            raise ValueError("state, controls, disturbances, parameters, and time must be disjoint")
        if self.control_bounds is not None and self.control_bounds.dimension != len(self.controls):
            raise ValueError("control_bounds dimension must match controls")
        if self.disturbance_bounds is not None and (
            self.disturbance_bounds.dimension != len(self.disturbances)
        ):
            raise ValueError("disturbance_bounds dimension must match disturbances")

    def state_jacobian(self) -> sp.Matrix:
        return sp.simplify(sp.Matrix(self.rhs).jacobian(self.state))

    def control_jacobian(self) -> sp.Matrix:
        return sp.simplify(sp.Matrix(self.rhs).jacobian(self.controls))

    def disturbance_jacobian(self) -> sp.Matrix:
        if not self.disturbances:
            return sp.zeros(len(self.state), 0)
        return sp.simplify(sp.Matrix(self.rhs).jacobian(self.disturbances))

    def equilibrium_residual(
        self,
        state_point: Mapping[sp.Symbol, sp.Expr | float],
        control_point: Mapping[sp.Symbol, sp.Expr | float],
        disturbance_point: Mapping[sp.Symbol, sp.Expr | float] | None = None,
        substitutions: Mapping[sp.Symbol, float] | None = None,
    ) -> tuple[sp.Expr, ...]:
        """f evaluated at the candidate equilibrium; all-zero iff equilibrium."""

        replacements: dict[sp.Symbol, sp.Expr | float] = dict(substitutions or {})
        replacements.update(state_point)
        replacements.update(control_point)
        replacements.update(disturbance_point or {})
        return tuple(sp.simplify(expr.subs(replacements)) for expr in self.rhs)

    def is_equilibrium(
        self,
        state_point: Mapping[sp.Symbol, sp.Expr | float],
        control_point: Mapping[sp.Symbol, sp.Expr | float],
        disturbance_point: Mapping[sp.Symbol, sp.Expr | float] | None = None,
        substitutions: Mapping[sp.Symbol, float] | None = None,
    ) -> bool:
        residual = self.equilibrium_residual(
            state_point, control_point, disturbance_point, substitutions
        )
        return all(component == 0 for component in residual)

    def closed_loop(
        self,
        control_law: Mapping[sp.Symbol, sp.Expr | float],
        disturbance_law: Mapping[sp.Symbol, sp.Expr | float] | None = None,
    ) -> FirstOrderSystem:
        """Substitute a symbolic feedback law and return the autonomous system.

        Disturbance channels without an entry in ``disturbance_law`` are set
        to zero (their nominal value). Gains or other new symbols introduced
        by the laws become parameters of the closed-loop system.
        """

        unknown = set(control_law) - set(self.controls)
        if unknown:
            names = ", ".join(sorted(symbol.name for symbol in unknown))
            raise ValueError(f"control_law contains non-control symbols: {names}")
        missing = set(self.controls) - set(control_law)
        if missing:
            names = ", ".join(sorted(symbol.name for symbol in missing))
            raise ValueError(f"control_law must cover all controls; missing: {names}")
        disturbance_law = dict(disturbance_law or {})
        unknown = set(disturbance_law) - set(self.disturbances)
        if unknown:
            names = ", ".join(sorted(symbol.name for symbol in unknown))
            raise ValueError(f"disturbance_law contains non-disturbance symbols: {names}")
        for symbol in self.disturbances:
            disturbance_law.setdefault(symbol, sp.Integer(0))

        replacements = {**dict(control_law), **disturbance_law}
        closed_rhs = tuple(sp.simplify(expr.subs(replacements)) for expr in self.rhs)

        free: set[sp.Symbol] = set()
        for expression in closed_rhs:
            free |= expression.free_symbols
        leftover = free & (set(self.controls) | set(self.disturbances))
        if leftover:
            names = ", ".join(sorted(symbol.name for symbol in leftover))
            raise ValueError(f"laws reintroduce control/disturbance symbols: {names}")
        extra = free - set(self.state) - set(self.parameters) - {self.time}
        parameters = self.parameters + tuple(sorted(extra, key=lambda s: s.name))

        return FirstOrderSystem(
            state=self.state,
            rhs=closed_rhs,
            parameters=parameters,
            time=self.time,
        )

    def numerical_rhs(
        self,
        control: ControlLaw,
        disturbance: ControlLaw | None = None,
        substitutions: Mapping[sp.Symbol, float] | None = None,
    ) -> Callable[[float, Sequence[float]], np.ndarray]:
        """Compose the lambdified dynamics with numeric control/disturbance laws."""

        expressions = [expr.subs(substitutions or {}) for expr in self.rhs]
        free: set[sp.Symbol] = set()
        for expression in expressions:
            free |= expression.free_symbols
        allowed = {self.time, *self.state, *self.controls, *self.disturbances}
        unresolved = free - allowed
        if unresolved:
            names = ", ".join(sorted(symbol.name for symbol in unresolved))
            raise ValueError(f"unresolved symbols in numerical RHS: {names}")

        args = (self.time, *self.state, *self.controls, *self.disturbances)
        compiled = sp.lambdify(args, expressions, modules="numpy")
        disturbance_count = len(self.disturbances)

        def rhs(t: float, state: Sequence[float]) -> np.ndarray:
            state_array = np.asarray(state, dtype=float)
            control_values = np.asarray(control(t, state_array), dtype=float)
            if disturbance is None:
                disturbance_values = np.zeros(disturbance_count)
            else:
                disturbance_values = np.asarray(disturbance(t, state_array), dtype=float)
            values = compiled(t, *state_array, *control_values, *disturbance_values)
            return np.asarray(values, dtype=float)

        return rhs


@dataclass(frozen=True)
class RolloutResult:
    time: np.ndarray
    states: np.ndarray
    controls: np.ndarray
    disturbances: np.ndarray
    # Measured suprema of distance outside the admissible boxes along the
    # rollout; 0.0 when no bounds were declared or none were exceeded.
    control_violation: float
    disturbance_violation: float


def rollout(
    system: ControlledFirstOrderSystem,
    control: ControlLaw,
    *,
    initial_state: Sequence[float],
    t_span: tuple[float, float],
    dt: float,
    disturbance: ControlLaw | None = None,
    substitutions: Mapping[sp.Symbol, float] | None = None,
) -> RolloutResult:
    """Deterministically integrate the closed loop under a numeric law.

    Bound violations are reported, never clipped away: a law that should
    saturate must do so explicitly (e.g. via ``Box.clip``).
    """

    rhs = system.numerical_rhs(control, disturbance, substitutions)
    time, states = integrate_fixed_step(
        rhs, initial_state=np.asarray(initial_state, dtype=float), t_span=t_span, dt=dt
    )

    control_samples = np.asarray(
        [np.asarray(control(t, x), dtype=float) for t, x in zip(time, states, strict=True)]
    )
    if disturbance is None:
        disturbance_samples = np.zeros((len(time), len(system.disturbances)))
    else:
        disturbance_samples = np.asarray(
            [np.asarray(disturbance(t, x), dtype=float) for t, x in zip(time, states, strict=True)]
        )

    control_violation = 0.0
    if system.control_bounds is not None:
        control_violation = system.control_bounds.violation(control_samples)
    disturbance_violation = 0.0
    if system.disturbance_bounds is not None and disturbance_samples.shape[1]:
        disturbance_violation = system.disturbance_bounds.violation(disturbance_samples)

    return RolloutResult(
        time=time,
        states=states,
        controls=control_samples,
        disturbances=disturbance_samples,
        control_violation=control_violation,
        disturbance_violation=disturbance_violation,
    )


__all__ = [
    "Box",
    "ControlLaw",
    "ControlledFirstOrderSystem",
    "RolloutResult",
    "rollout",
]
