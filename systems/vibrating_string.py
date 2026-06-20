from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Mapping, Sequence

import numpy as np
import sympy as sp

BoundaryKind = str
Profile = Callable[[np.ndarray], np.ndarray]


@dataclass(frozen=True)
class BoundaryConditions:
    left: BoundaryKind
    right: BoundaryKind

    def __post_init__(self) -> None:
        allowed = {"fixed", "free"}
        if self.left not in allowed or self.right not in allowed:
            raise ValueError("string boundary conditions must be 'fixed' or 'free'")

    @property
    def kind(self) -> str:
        return f"{self.left}-{self.right}"


@dataclass(frozen=True)
class VibratingStringSystem:
    length: sp.Expr
    wave_speed: sp.Expr
    density: sp.Expr
    tension: sp.Expr
    boundary: BoundaryConditions = BoundaryConditions("fixed", "fixed")

    def __post_init__(self) -> None:
        object.__setattr__(self, "length", sp.sympify(self.length))
        object.__setattr__(self, "wave_speed", sp.sympify(self.wave_speed))
        object.__setattr__(self, "density", sp.sympify(self.density))
        object.__setattr__(self, "tension", sp.sympify(self.tension))

    def mode_wavenumber(self, n: int) -> sp.Expr:
        if n < 1:
            raise ValueError("mode index n must be positive")
        if self.boundary.kind in {"fixed-fixed", "free-free"}:
            return sp.pi * n / self.length
        return sp.pi * (sp.Rational(2 * n - 1, 2)) / self.length

    def angular_frequency(self, n: int) -> sp.Expr:
        return sp.simplify(self.wave_speed * self.mode_wavenumber(n))

    def frequency(self, n: int) -> sp.Expr:
        return sp.simplify(self.angular_frequency(n) / (2 * sp.pi))

    def mode_shape(self, n: int, x: sp.Expr) -> sp.Expr:
        k = self.mode_wavenumber(n)
        if self.boundary.left == "fixed":
            return sp.sin(k * x)
        return sp.cos(k * x)

    def normal_modes(
        self,
        count: int,
        *,
        parameters: Mapping[str, float] | None = None,
    ) -> dict[str, object]:
        x = sp.Symbol("x", real=True)
        substitutions = _substitutions_for(
            (self.length, self.wave_speed, self.density, self.tension),
            parameters or {},
        )
        return {
            "method": "analytic-string-boundary-eigenmodes",
            "boundary": self.boundary.kind,
            "coordinate": "x",
            "frequencies": [
                float(self.frequency(n).subs(substitutions)) for n in range(1, count + 1)
            ],
            "angularFrequencies": [
                float(self.angular_frequency(n).subs(substitutions))
                for n in range(1, count + 1)
            ],
            "modeShapesLatex": [
                sp.latex(self.mode_shape(n, x)) for n in range(1, count + 1)
            ],
        }

    def manifest_metadata(self) -> dict[str, object]:
        return {
            "kind": "vibrating-string",
            "boundary": self.boundary.kind,
            "equationLatex": r"u_{tt}=c^2 u_{xx}",
            "coordinate": "x",
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


def _numeric_system(system: VibratingStringSystem, parameters: Mapping[str, float]) -> tuple[float, float, float, float]:
    expressions = (system.length, system.wave_speed, system.density, system.tension)
    substitutions = _substitutions_for(expressions, parameters)
    return (
        float(system.length.subs(substitutions)),
        float(system.wave_speed.subs(substitutions)),
        float(system.density.subs(substitutions)),
        float(system.tension.subs(substitutions)),
    )


def modal_displacement(
    system: VibratingStringSystem,
    x: Sequence[float],
    t: Sequence[float],
    amplitudes: Sequence[float],
    *,
    parameters: Mapping[str, float],
) -> np.ndarray:
    length, wave_speed, _density, _tension = _numeric_system(system, parameters)
    x_values = np.asarray(x, dtype=float)
    t_values = np.asarray(t, dtype=float)
    result = np.zeros((len(t_values), len(x_values)))
    for index, amplitude in enumerate(amplitudes, start=1):
        k = float(system.mode_wavenumber(index).subs({system.length: length}))
        omega = wave_speed * k
        shape = _mode_shape_values(system.boundary, k, x_values)
        result += float(amplitude) * np.cos(omega * t_values[:, np.newaxis]) * shape
    return result


def modal_velocity(
    system: VibratingStringSystem,
    x: Sequence[float],
    t: Sequence[float],
    amplitudes: Sequence[float],
    *,
    parameters: Mapping[str, float],
) -> np.ndarray:
    length, wave_speed, _density, _tension = _numeric_system(system, parameters)
    x_values = np.asarray(x, dtype=float)
    t_values = np.asarray(t, dtype=float)
    result = np.zeros((len(t_values), len(x_values)))
    for index, amplitude in enumerate(amplitudes, start=1):
        k = float(system.mode_wavenumber(index).subs({system.length: length}))
        omega = wave_speed * k
        shape = _mode_shape_values(system.boundary, k, x_values)
        result += -float(amplitude) * omega * np.sin(omega * t_values[:, np.newaxis]) * shape
    return result


def modal_spatial_derivative(
    system: VibratingStringSystem,
    x: Sequence[float],
    t: Sequence[float],
    amplitudes: Sequence[float],
    *,
    parameters: Mapping[str, float],
) -> np.ndarray:
    length, wave_speed, _density, _tension = _numeric_system(system, parameters)
    x_values = np.asarray(x, dtype=float)
    t_values = np.asarray(t, dtype=float)
    result = np.zeros((len(t_values), len(x_values)))
    for index, amplitude in enumerate(amplitudes, start=1):
        k = float(system.mode_wavenumber(index).subs({system.length: length}))
        omega = wave_speed * k
        derivative = _mode_shape_derivative_values(system.boundary, k, x_values)
        result += float(amplitude) * np.cos(omega * t_values[:, np.newaxis]) * derivative
    return result


def modal_energy(
    system: VibratingStringSystem,
    x: Sequence[float],
    t: Sequence[float],
    amplitudes: Sequence[float],
    *,
    parameters: Mapping[str, float],
) -> np.ndarray:
    _length, _wave_speed, density, tension = _numeric_system(system, parameters)
    velocity = modal_velocity(system, x, t, amplitudes, parameters=parameters)
    spatial = modal_spatial_derivative(system, x, t, amplitudes, parameters=parameters)
    density_values = 0.5 * density * velocity**2 + 0.5 * tension * spatial**2
    return np.trapz(density_values, np.asarray(x, dtype=float), axis=1)


def dalembert_solution(
    x: Sequence[float],
    t: Sequence[float],
    *,
    wave_speed: float,
    initial_displacement: Profile,
    initial_velocity_antiderivative: Profile,
) -> np.ndarray:
    x_values = np.asarray(x, dtype=float)
    t_values = np.asarray(t, dtype=float)
    left = x_values[np.newaxis, :] - wave_speed * t_values[:, np.newaxis]
    right = x_values[np.newaxis, :] + wave_speed * t_values[:, np.newaxis]
    return 0.5 * (initial_displacement(left) + initial_displacement(right)) + (
        initial_velocity_antiderivative(right)
        - initial_velocity_antiderivative(left)
    ) / (2.0 * wave_speed)


def gaussian_profile(*, center: float, width: float) -> Profile:
    if width <= 0.0:
        raise ValueError("width must be positive")

    def profile(x: np.ndarray) -> np.ndarray:
        return np.exp(-0.5 * ((x - center) / width) ** 2)

    return profile


def right_traveling_velocity_antiderivative(
    *,
    wave_speed: float,
    profile: Profile,
) -> Profile:
    def antiderivative(x: np.ndarray) -> np.ndarray:
        return -wave_speed * profile(x)

    return antiderivative


def _mode_shape_values(boundary: BoundaryConditions, k: float, x: np.ndarray) -> np.ndarray:
    if boundary.left == "fixed":
        return np.sin(k * x)[np.newaxis, :]
    return np.cos(k * x)[np.newaxis, :]


def _mode_shape_derivative_values(boundary: BoundaryConditions, k: float, x: np.ndarray) -> np.ndarray:
    if boundary.left == "fixed":
        return (k * np.cos(k * x))[np.newaxis, :]
    return (-k * np.sin(k * x))[np.newaxis, :]


def build_system(
    *,
    length: sp.Expr | float | None = None,
    wave_speed: sp.Expr | float | None = None,
    density: sp.Expr | float | None = None,
    boundary: BoundaryConditions | None = None,
) -> VibratingStringSystem:
    length_value = sp.Symbol("L", positive=True) if length is None else length
    speed_value = sp.Symbol("c", positive=True) if wave_speed is None else wave_speed
    density_value = sp.Symbol("rho", positive=True) if density is None else density
    tension = sp.simplify(density_value * speed_value**2)
    return VibratingStringSystem(
        length=length_value,
        wave_speed=speed_value,
        density=density_value,
        tension=tension,
        boundary=boundary or BoundaryConditions("fixed", "fixed"),
    )


system = build_system()
