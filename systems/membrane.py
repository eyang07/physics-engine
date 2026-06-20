from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

import numpy as np
from scipy.special import jn, jn_zeros
import sympy as sp


@dataclass(frozen=True)
class RectangularMode:
    m: int
    n: int

    def __post_init__(self) -> None:
        if self.m < 1 or self.n < 1:
            raise ValueError("rectangular membrane mode indices must be positive")


@dataclass(frozen=True)
class CircularMode:
    angular: int
    radial: int

    def __post_init__(self) -> None:
        if self.angular < 0:
            raise ValueError("circular membrane angular index must be nonnegative")
        if self.radial < 1:
            raise ValueError("circular membrane radial index must be positive")


@dataclass(frozen=True)
class MembraneSystem:
    width: sp.Expr
    height: sp.Expr
    radius: sp.Expr
    wave_speed: sp.Expr

    def __post_init__(self) -> None:
        object.__setattr__(self, "width", sp.sympify(self.width))
        object.__setattr__(self, "height", sp.sympify(self.height))
        object.__setattr__(self, "radius", sp.sympify(self.radius))
        object.__setattr__(self, "wave_speed", sp.sympify(self.wave_speed))

    def rectangular_angular_frequency(self, mode: RectangularMode) -> sp.Expr:
        return sp.simplify(
            sp.pi
            * self.wave_speed
            * sp.sqrt((mode.m / self.width) ** 2 + (mode.n / self.height) ** 2)
        )

    def rectangular_frequency(self, mode: RectangularMode) -> sp.Expr:
        return sp.simplify(self.rectangular_angular_frequency(mode) / (2 * sp.pi))

    def rectangular_mode_shape(self, mode: RectangularMode, x: sp.Expr, y: sp.Expr) -> sp.Expr:
        return sp.sin(mode.m * sp.pi * x / self.width) * sp.sin(
            mode.n * sp.pi * y / self.height
        )

    def circular_bessel_zero(self, mode: CircularMode) -> float:
        return float(jn_zeros(mode.angular, mode.radial)[-1])

    def circular_angular_frequency(self, mode: CircularMode) -> sp.Expr:
        return sp.simplify(self.wave_speed * self.circular_bessel_zero(mode) / self.radius)

    def circular_frequency(self, mode: CircularMode) -> sp.Expr:
        return sp.simplify(self.circular_angular_frequency(mode) / (2 * sp.pi))

    def normal_modes(self, *, parameters: Mapping[str, float]) -> dict[str, object]:
        rectangular = [RectangularMode(1, 1), RectangularMode(2, 1), RectangularMode(1, 2)]
        circular = [CircularMode(0, 1), CircularMode(1, 1), CircularMode(2, 1)]
        substitutions = _substitutions_for(
            (self.width, self.height, self.radius, self.wave_speed),
            parameters,
        )
        return {
            "method": "analytic-membrane-eigenmodes",
            "rectangular": [
                {
                    "m": mode.m,
                    "n": mode.n,
                    "frequency": float(self.rectangular_frequency(mode).subs(substitutions)),
                    "angularFrequency": float(
                        self.rectangular_angular_frequency(mode).subs(substitutions)
                    ),
                }
                for mode in rectangular
            ],
            "circular": [
                {
                    "angular": mode.angular,
                    "radial": mode.radial,
                    "besselZero": self.circular_bessel_zero(mode),
                    "frequency": float(self.circular_frequency(mode).subs(substitutions)),
                    "angularFrequency": float(
                        self.circular_angular_frequency(mode).subs(substitutions)
                    ),
                }
                for mode in circular
            ],
        }

    def manifest_metadata(self) -> dict[str, object]:
        return {
            "kind": "membrane",
            "equationLatex": r"u_{tt}=c^2(u_{xx}+u_{yy})",
        }

    def parameter_expressions(self) -> tuple[sp.Expr, ...]:
        return (self.width, self.height, self.radius, self.wave_speed)


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


def _numeric_values(system: MembraneSystem, parameters: Mapping[str, float]) -> tuple[float, float, float, float]:
    substitutions = _substitutions_for(
        (system.width, system.height, system.radius, system.wave_speed),
        parameters,
    )
    return (
        float(system.width.subs(substitutions)),
        float(system.height.subs(substitutions)),
        float(system.radius.subs(substitutions)),
        float(system.wave_speed.subs(substitutions)),
    )


def rectangular_mode_values(
    system: MembraneSystem,
    mode: RectangularMode,
    x: Sequence[float],
    y: Sequence[float],
    *,
    parameters: Mapping[str, float],
) -> np.ndarray:
    width, height, _radius, _speed = _numeric_values(system, parameters)
    xx, yy = np.meshgrid(np.asarray(x, dtype=float), np.asarray(y, dtype=float), indexing="ij")
    return np.sin(mode.m * np.pi * xx / width) * np.sin(mode.n * np.pi * yy / height)


def rectangular_superposition(
    system: MembraneSystem,
    modes: Sequence[tuple[RectangularMode, float]],
    x: Sequence[float],
    y: Sequence[float],
    time: Sequence[float],
    *,
    parameters: Mapping[str, float],
) -> np.ndarray:
    substitutions = _substitutions_for(
        (system.width, system.height, system.radius, system.wave_speed),
        parameters,
    )
    t = np.asarray(time, dtype=float)
    values = np.zeros((len(t), len(x), len(y)))
    for mode, amplitude in modes:
        omega = float(system.rectangular_angular_frequency(mode).subs(substitutions))
        shape = rectangular_mode_values(system, mode, x, y, parameters=parameters)
        values += float(amplitude) * np.cos(omega * t[:, np.newaxis, np.newaxis]) * shape
    return values


def circular_mode_values(
    system: MembraneSystem,
    mode: CircularMode,
    x: Sequence[float],
    y: Sequence[float],
    *,
    parameters: Mapping[str, float],
) -> np.ndarray:
    _width, _height, radius, _speed = _numeric_values(system, parameters)
    xx, yy = np.meshgrid(np.asarray(x, dtype=float), np.asarray(y, dtype=float), indexing="ij")
    r = np.sqrt(xx**2 + yy**2)
    theta = np.arctan2(yy, xx)
    alpha = system.circular_bessel_zero(mode)
    values = jn(mode.angular, alpha * r / radius) * np.cos(mode.angular * theta)
    return np.where(r <= radius, values, np.nan)


def circular_superposition(
    system: MembraneSystem,
    modes: Sequence[tuple[CircularMode, float]],
    x: Sequence[float],
    y: Sequence[float],
    time: Sequence[float],
    *,
    parameters: Mapping[str, float],
) -> np.ndarray:
    substitutions = _substitutions_for(
        (system.width, system.height, system.radius, system.wave_speed),
        parameters,
    )
    t = np.asarray(time, dtype=float)
    values = np.zeros((len(t), len(x), len(y)))
    mask = None
    for mode, amplitude in modes:
        omega = float(system.circular_angular_frequency(mode).subs(substitutions))
        shape = circular_mode_values(system, mode, x, y, parameters=parameters)
        if mask is None:
            mask = np.isnan(shape)
        values += float(amplitude) * np.cos(omega * t[:, np.newaxis, np.newaxis]) * np.nan_to_num(shape)
    if mask is not None:
        values[:, mask] = np.nan
    return values


def build_system(
    *,
    width: sp.Expr | float | None = None,
    height: sp.Expr | float | None = None,
    radius: sp.Expr | float | None = None,
    wave_speed: sp.Expr | float | None = None,
) -> MembraneSystem:
    return MembraneSystem(
        width=sp.Symbol("Lx", positive=True) if width is None else width,
        height=sp.Symbol("Ly", positive=True) if height is None else height,
        radius=sp.Symbol("R", positive=True) if radius is None else radius,
        wave_speed=sp.Symbol("c", positive=True) if wave_speed is None else wave_speed,
    )


system = build_system()
