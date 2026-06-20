from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

import numpy as np
import sympy as sp


@dataclass(frozen=True)
class QuadraticDispersionPacket:
    alpha: sp.Expr
    k0: sp.Expr
    sigma: sp.Expr
    x0: sp.Expr

    def __post_init__(self) -> None:
        object.__setattr__(self, "alpha", sp.sympify(self.alpha))
        object.__setattr__(self, "k0", sp.sympify(self.k0))
        object.__setattr__(self, "sigma", sp.sympify(self.sigma))
        object.__setattr__(self, "x0", sp.sympify(self.x0))

    def omega(self, k: sp.Expr) -> sp.Expr:
        return sp.simplify(self.alpha * k**2)

    def group_velocity(self) -> sp.Expr:
        k = sp.Symbol("k", positive=True)
        return sp.simplify(sp.diff(self.omega(k), k).subs(k, self.k0))

    def phase_velocity(self) -> sp.Expr:
        return sp.simplify(self.omega(self.k0) / self.k0)

    def width(self, t: sp.Expr) -> sp.Expr:
        return sp.simplify(self.sigma * sp.sqrt(1 + (2 * self.alpha * t / self.sigma**2) ** 2))

    def center(self, t: sp.Expr) -> sp.Expr:
        return sp.simplify(self.x0 + self.group_velocity() * t)

    def parameter_expressions(self) -> tuple[sp.Expr, ...]:
        return (self.alpha, self.k0, self.sigma, self.x0)

    def manifest_metadata(self) -> dict[str, object]:
        return {
            "kind": "quadratic-dispersion-wave-packet",
            "dispersionLatex": sp.latex(self.omega(sp.Symbol("k", positive=True))),
        }


def _substitutions_for(
    expressions: Sequence[sp.Expr],
    parameters: Mapping[str, float],
) -> dict[sp.Symbol, float]:
    return {
        symbol: parameters[symbol.name]
        for expression in expressions
        for symbol in expression.free_symbols
        if symbol.name in parameters
    }


def numeric_velocities(
    packet: QuadraticDispersionPacket,
    *,
    parameters: Mapping[str, float],
) -> tuple[float, float]:
    substitutions = _substitutions_for(packet.parameter_expressions(), parameters)
    return (
        float(packet.phase_velocity().subs(substitutions)),
        float(packet.group_velocity().subs(substitutions)),
    )


def envelope_width(
    packet: QuadraticDispersionPacket,
    time: Sequence[float],
    *,
    parameters: Mapping[str, float],
) -> np.ndarray:
    substitutions = _substitutions_for(packet.parameter_expressions(), parameters)
    fn = sp.lambdify(sp.Symbol("t", real=True), packet.width(sp.Symbol("t", real=True)).subs(substitutions), modules="numpy")
    return np.asarray(fn(np.asarray(time, dtype=float)), dtype=float)


def packet_fields(
    packet: QuadraticDispersionPacket,
    x: Sequence[float],
    time: Sequence[float],
    *,
    parameters: Mapping[str, float],
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    alpha = float(parameters["alpha"])
    k0 = float(parameters["k0"])
    sigma0 = float(parameters["sigma"])
    x0 = float(parameters["x0"])
    phase_velocity, group_velocity = numeric_velocities(packet, parameters=parameters)
    x_values = np.asarray(x, dtype=float)
    t_values = np.asarray(time, dtype=float)
    widths = envelope_width(packet, t_values, parameters=parameters)
    centers = x0 + group_velocity * t_values
    envelope = np.sqrt(sigma0 / widths[:, np.newaxis]) * np.exp(
        -0.5 * ((x_values[np.newaxis, :] - centers[:, np.newaxis]) / widths[:, np.newaxis]) ** 2
    )
    phase = k0 * (x_values[np.newaxis, :] - x0) - (phase_velocity * k0) * t_values[:, np.newaxis]
    amplitude = envelope * np.cos(phase)
    intensity = envelope**2
    return amplitude, intensity, widths


def build_system(
    *,
    alpha: sp.Expr | float | None = None,
    k0: sp.Expr | float | None = None,
    sigma: sp.Expr | float | None = None,
    x0: sp.Expr | float | None = None,
) -> QuadraticDispersionPacket:
    return QuadraticDispersionPacket(
        alpha=sp.Symbol("alpha", positive=True) if alpha is None else alpha,
        k0=sp.Symbol("k0", positive=True) if k0 is None else k0,
        sigma=sp.Symbol("sigma", positive=True) if sigma is None else sigma,
        x0=sp.Symbol("x0", real=True) if x0 is None else x0,
    )


system = build_system()
