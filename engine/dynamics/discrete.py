"""Discrete-time controlled dynamics: x_{k+1} = F(k, x_k, u_k, d_k; params).

The discrete analogue of `engine/dynamics/controlled.py`, completing the
controlled-dynamics roadmap item (`docs/VISION.md` §8). The same load-bearing
move applies: *closed-loop reduction* substitutes a symbolic feedback law
``u = pi(k, x)`` and yields a plain :class:`DiscreteSystem`. Admissible sets
are the same axis-aligned :class:`~engine.dynamics.controlled.Box` values,
and rollouts *measure and report* bound violations; they never silently clip.

``euler_discretization`` bridges the continuous layer: the forward-Euler map
``x + dt f(x, u, d)`` is an *approximation* of the sampled flow, not the
flow itself, and callers own the choice of ``dt``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Mapping, Sequence

import numpy as np
import sympy as sp

from engine.dynamics.controlled import Box, ControlledFirstOrderSystem
from engine.dynamics.first_order import FirstOrderSystem

DiscreteControlLaw = Callable[[int, np.ndarray], Sequence[float]]

_DEFAULT_STEP = sp.Symbol("k", integer=True, nonnegative=True)


@dataclass(frozen=True)
class DiscreteSystem:
    """A finite-dimensional discrete-time system x_{k+1} = F(k, x_k; params)."""

    state: tuple[sp.Symbol, ...]
    update: tuple[sp.Expr, ...]
    parameters: tuple[sp.Symbol, ...] = ()
    step: sp.Symbol = _DEFAULT_STEP

    def __post_init__(self) -> None:
        if len(self.state) != len(self.update):
            raise ValueError("state and update must have the same length")

    @property
    def state_symbols(self) -> tuple[sp.Symbol, ...]:
        return self.state

    def jacobian(self) -> sp.Matrix:
        return sp.simplify(sp.Matrix(self.update).jacobian(self.state))

    def fixed_points(
        self,
        substitutions: Mapping[sp.Symbol, float] | None = None,
    ) -> list[dict[sp.Symbol, sp.Expr]]:
        residuals = [
            (component - symbol).subs(substitutions or {})
            for component, symbol in zip(self.update, self.state, strict=True)
        ]
        return sp.solve(residuals, self.state, dict=True)

    def linearization(
        self,
        point: Mapping[sp.Symbol, sp.Expr | float],
        substitutions: Mapping[sp.Symbol, float] | None = None,
    ) -> sp.Matrix:
        return sp.simplify(self.jacobian().subs(substitutions or {}).subs(point))

    def numerical_update(
        self,
        substitutions: Mapping[sp.Symbol, float] | None = None,
    ):
        substitutions = substitutions or {}
        expressions = [expr.subs(substitutions) for expr in self.update]
        free_symbols = set().union(*(expr.free_symbols for expr in expressions))
        allowed = {self.step, *self.state}
        unresolved = free_symbols - allowed
        if unresolved:
            names = ", ".join(sorted(symbol.name for symbol in unresolved))
            raise ValueError(f"unresolved symbols in numerical update: {names}")

        args = (self.step, *self.state)
        compiled = sp.lambdify(args, expressions, modules="numpy")

        def update(k: int, state: Sequence[float]) -> np.ndarray:
            values = compiled(k, *state)
            return np.asarray(values, dtype=float)

        return update

    def iterate(
        self,
        initial_state: Sequence[float],
        step_count: int,
        substitutions: Mapping[sp.Symbol, float] | None = None,
    ) -> tuple[np.ndarray, np.ndarray]:
        """Deterministically iterate the map; returns (steps, states)."""

        if step_count < 1:
            raise ValueError("step_count must be at least 1")
        update = self.numerical_update(substitutions)
        states = np.empty((step_count + 1, len(self.state)), dtype=float)
        states[0] = np.asarray(initial_state, dtype=float)
        for index in range(step_count):
            states[index + 1] = update(index, states[index])
        return np.arange(step_count + 1), states


@dataclass(frozen=True)
class ControlledDiscreteSystem:
    """A discrete-time controlled system x_{k+1} = F(k, x_k, u_k, d_k; params)."""

    state: tuple[sp.Symbol, ...]
    controls: tuple[sp.Symbol, ...]
    update: tuple[sp.Expr, ...]
    disturbances: tuple[sp.Symbol, ...] = ()
    parameters: tuple[sp.Symbol, ...] = ()
    step: sp.Symbol = _DEFAULT_STEP
    control_bounds: Box | None = None
    disturbance_bounds: Box | None = None

    def __post_init__(self) -> None:
        if len(self.state) != len(self.update):
            raise ValueError("state and update must have the same length")
        if not self.controls:
            raise ValueError("controls must be non-empty; use DiscreteSystem otherwise")
        groups = (self.state, self.controls, self.disturbances, self.parameters, (self.step,))
        symbols = [symbol for group in groups for symbol in group]
        if len(symbols) != len(set(symbols)):
            raise ValueError("state, controls, disturbances, parameters, and step must be disjoint")
        if self.control_bounds is not None and self.control_bounds.dimension != len(self.controls):
            raise ValueError("control_bounds dimension must match controls")
        if self.disturbance_bounds is not None and (
            self.disturbance_bounds.dimension != len(self.disturbances)
        ):
            raise ValueError("disturbance_bounds dimension must match disturbances")

    def state_jacobian(self) -> sp.Matrix:
        return sp.simplify(sp.Matrix(self.update).jacobian(self.state))

    def control_jacobian(self) -> sp.Matrix:
        return sp.simplify(sp.Matrix(self.update).jacobian(self.controls))

    def closed_loop(
        self,
        control_law: Mapping[sp.Symbol, sp.Expr | float],
        disturbance_law: Mapping[sp.Symbol, sp.Expr | float] | None = None,
    ) -> DiscreteSystem:
        """Substitute a symbolic feedback law and return the autonomous map.

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
        closed_update = tuple(sp.simplify(expr.subs(replacements)) for expr in self.update)

        free: set[sp.Symbol] = set()
        for expression in closed_update:
            free |= expression.free_symbols
        leftover = free & (set(self.controls) | set(self.disturbances))
        if leftover:
            names = ", ".join(sorted(symbol.name for symbol in leftover))
            raise ValueError(f"laws reintroduce control/disturbance symbols: {names}")
        extra = free - set(self.state) - set(self.parameters) - {self.step}
        parameters = self.parameters + tuple(sorted(extra, key=lambda s: s.name))

        return DiscreteSystem(
            state=self.state,
            update=closed_update,
            parameters=parameters,
            step=self.step,
        )

    def numerical_update(
        self,
        control: DiscreteControlLaw,
        disturbance: DiscreteControlLaw | None = None,
        substitutions: Mapping[sp.Symbol, float] | None = None,
    ) -> Callable[[int, Sequence[float]], np.ndarray]:
        """Compose the lambdified map with numeric control/disturbance laws."""

        expressions = [expr.subs(substitutions or {}) for expr in self.update]
        free: set[sp.Symbol] = set()
        for expression in expressions:
            free |= expression.free_symbols
        allowed = {self.step, *self.state, *self.controls, *self.disturbances}
        unresolved = free - allowed
        if unresolved:
            names = ", ".join(sorted(symbol.name for symbol in unresolved))
            raise ValueError(f"unresolved symbols in numerical update: {names}")

        args = (self.step, *self.state, *self.controls, *self.disturbances)
        compiled = sp.lambdify(args, expressions, modules="numpy")
        disturbance_count = len(self.disturbances)

        def update(k: int, state: Sequence[float]) -> np.ndarray:
            state_array = np.asarray(state, dtype=float)
            control_values = np.asarray(control(k, state_array), dtype=float)
            if disturbance is None:
                disturbance_values = np.zeros(disturbance_count)
            else:
                disturbance_values = np.asarray(disturbance(k, state_array), dtype=float)
            values = compiled(k, *state_array, *control_values, *disturbance_values)
            return np.asarray(values, dtype=float)

        return update


@dataclass(frozen=True)
class DiscreteRolloutResult:
    steps: np.ndarray
    states: np.ndarray
    # Controls/disturbances applied at steps 0..N-1; one row fewer than states.
    controls: np.ndarray
    disturbances: np.ndarray
    # Measured suprema of distance outside the admissible boxes along the
    # rollout; 0.0 when no bounds were declared or none were exceeded.
    control_violation: float
    disturbance_violation: float


def discrete_rollout(
    system: ControlledDiscreteSystem,
    control: DiscreteControlLaw,
    *,
    initial_state: Sequence[float],
    step_count: int,
    disturbance: DiscreteControlLaw | None = None,
    substitutions: Mapping[sp.Symbol, float] | None = None,
) -> DiscreteRolloutResult:
    """Deterministically iterate the closed loop under a numeric law.

    Bound violations are reported, never clipped away: a law that should
    saturate must do so explicitly (e.g. via ``Box.clip``).
    """

    if step_count < 1:
        raise ValueError("step_count must be at least 1")
    update = system.numerical_update(control, disturbance, substitutions)

    states = np.empty((step_count + 1, len(system.state)), dtype=float)
    states[0] = np.asarray(initial_state, dtype=float)
    control_samples = np.empty((step_count, len(system.controls)), dtype=float)
    disturbance_samples = np.zeros((step_count, len(system.disturbances)), dtype=float)
    for index in range(step_count):
        control_samples[index] = np.asarray(control(index, states[index]), dtype=float)
        if disturbance is not None:
            disturbance_samples[index] = np.asarray(
                disturbance(index, states[index]), dtype=float
            )
        states[index + 1] = update(index, states[index])

    control_violation = 0.0
    if system.control_bounds is not None:
        control_violation = system.control_bounds.violation(control_samples)
    disturbance_violation = 0.0
    if system.disturbance_bounds is not None and disturbance_samples.shape[1]:
        disturbance_violation = system.disturbance_bounds.violation(disturbance_samples)

    return DiscreteRolloutResult(
        steps=np.arange(step_count + 1),
        states=states,
        controls=control_samples,
        disturbances=disturbance_samples,
        control_violation=control_violation,
        disturbance_violation=disturbance_violation,
    )


def euler_discretization(
    system: FirstOrderSystem | ControlledFirstOrderSystem,
    dt: sp.Expr | float,
    *,
    step: sp.Symbol | None = None,
) -> DiscreteSystem | ControlledDiscreteSystem:
    """Forward-Euler map ``x_{k+1} = x + dt f(x, u, d)`` of an autonomous system.

    The map approximates the sampled flow to first order in ``dt``; it is a
    modeling decision, not the flow itself. A symbolic ``dt`` becomes a
    parameter of the discrete system.
    """

    for expression in system.rhs:
        if sp.sympify(expression).has(system.time):
            raise ValueError("euler discretization requires an autonomous system")

    update = tuple(
        symbol + dt * expression
        for symbol, expression in zip(system.state, system.rhs, strict=True)
    )
    extra = (dt,) if isinstance(dt, sp.Symbol) else ()
    step_symbol = step if step is not None else _DEFAULT_STEP

    if isinstance(system, ControlledFirstOrderSystem):
        return ControlledDiscreteSystem(
            state=system.state,
            controls=system.controls,
            update=update,
            disturbances=system.disturbances,
            parameters=system.parameters + extra,
            step=step_symbol,
            control_bounds=system.control_bounds,
            disturbance_bounds=system.disturbance_bounds,
        )
    return DiscreteSystem(
        state=system.state,
        update=update,
        parameters=system.parameters + extra,
        step=step_symbol,
    )


__all__ = [
    "ControlledDiscreteSystem",
    "DiscreteControlLaw",
    "DiscreteRolloutResult",
    "DiscreteSystem",
    "discrete_rollout",
    "euler_discretization",
]
