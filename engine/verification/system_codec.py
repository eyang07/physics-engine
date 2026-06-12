"""Encode engine dynamics objects as verification-IR dynamics specs."""

from __future__ import annotations

import sympy as sp

from engine.dynamics.controlled import Box, ControlledFirstOrderSystem
from engine.dynamics.first_order import FirstOrderSystem
from engine.verification.ir import DynamicsSpec, InputSpec
from engine.verification.sympy_codec import expression_spec


def _input_specs(
    symbols: tuple[sp.Symbol, ...],
    bounds: Box | None,
    role: str,
) -> tuple[InputSpec, ...]:
    return tuple(
        InputSpec(
            name=symbol.name,
            latex=sp.latex(symbol),
            role=role,
            lower=None if bounds is None else bounds.lower[index],
            upper=None if bounds is None else bounds.upper[index],
        )
        for index, symbol in enumerate(symbols)
    )


def dynamics_spec_from_system(system: FirstOrderSystem) -> DynamicsSpec:
    """Encode a (typically closed-loop) first-order system; no open inputs."""

    return DynamicsSpec(
        kind="continuous",
        time_variable=system.time.name,
        state=tuple(symbol.name for symbol in system.state),
        rhs=tuple(expression_spec(expression) for expression in system.rhs),
    )


def dynamics_spec_from_controlled(system: ControlledFirstOrderSystem) -> DynamicsSpec:
    """Encode an open-loop controlled system with its admissible boxes."""

    inputs = _input_specs(system.controls, system.control_bounds, "control")
    inputs += _input_specs(system.disturbances, system.disturbance_bounds, "disturbance")
    return DynamicsSpec(
        kind="continuous",
        time_variable=system.time.name,
        state=tuple(symbol.name for symbol in system.state),
        rhs=tuple(expression_spec(expression) for expression in system.rhs),
        inputs=inputs,
    )
