from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

import numpy as np
from scipy.linalg import expm
import sympy as sp

from engine.dynamics.first_order import FirstOrderSystem


@dataclass(frozen=True)
class LyapunovResult:
    estimate: np.ndarray
    local_growth: np.ndarray
    initial_tangent: np.ndarray
    final_tangent: np.ndarray

    @property
    def final_estimate(self) -> float:
        return float(self.estimate[-1])


@dataclass(frozen=True)
class PoincareSection:
    coordinate: str
    value: float
    direction: str
    state_names: tuple[str, ...]
    points: list[dict[str, object]]


def finite_time_lyapunov(
    system: FirstOrderSystem,
    time: Sequence[float],
    states: Sequence[Sequence[float]],
    *,
    initial_tangent: Sequence[float] | None = None,
    substitutions: Mapping[sp.Symbol, float] | None = None,
) -> LyapunovResult:
    """Estimate the largest finite-time Lyapunov exponent from sampled states.

    The tangent vector is propagated with the local Jacobian matrix over each
    sample interval and renormalized after every step. This is an approximate
    sampled-trajectory Benettin estimate, suitable for deterministic diagnostic
    exports rather than high-precision chaos studies.
    """

    time_array = np.asarray(time, dtype=float)
    state_array = np.asarray(states, dtype=float)
    if time_array.ndim != 1:
        raise ValueError("time must be one-dimensional")
    if state_array.ndim != 2:
        raise ValueError("states must be two-dimensional")
    if len(time_array) != state_array.shape[0]:
        raise ValueError("time and states must have the same sample count")
    if state_array.shape[1] != len(system.state_symbols):
        raise ValueError("states must match the system state dimension")
    if len(time_array) < 2:
        raise ValueError("at least two samples are required")

    tangent = np.asarray(
        initial_tangent if initial_tangent is not None else _default_tangent(state_array.shape[1]),
        dtype=float,
    )
    if tangent.shape != (state_array.shape[1],):
        raise ValueError("initial_tangent must match the system state dimension")

    tangent_norm = float(np.linalg.norm(tangent))
    if tangent_norm <= 0:
        raise ValueError("initial_tangent must be nonzero")
    tangent = tangent / tangent_norm
    normalized_initial_tangent = tangent.copy()

    jacobian = _jacobian_evaluator(system, substitutions)
    estimate = np.zeros(len(time_array), dtype=float)
    local_growth = np.zeros(len(time_array), dtype=float)
    log_sum = 0.0
    elapsed = 0.0

    for index in range(1, len(time_array)):
        dt = float(time_array[index] - time_array[index - 1])
        if dt <= 0:
            raise ValueError("time samples must be strictly increasing")

        tangent = expm(jacobian(float(time_array[index - 1]), state_array[index - 1]) * dt) @ tangent
        growth = float(np.linalg.norm(tangent))
        if growth <= 0:
            raise FloatingPointError("tangent vector collapsed during Lyapunov estimate")

        log_growth = float(np.log(growth))
        local_growth[index] = log_growth / dt
        log_sum += log_growth
        elapsed += dt
        estimate[index] = log_sum / elapsed
        tangent = tangent / growth

    return LyapunovResult(
        estimate=estimate,
        local_growth=local_growth,
        initial_tangent=normalized_initial_tangent,
        final_tangent=tangent,
    )


def poincare_section_crossings(
    time: Sequence[float],
    states: Sequence[Sequence[float]],
    *,
    state_names: Sequence[str],
    coordinate: str,
    value: float = 0.0,
    direction: str = "positive",
    max_points: int | None = None,
    series: Mapping[str, Sequence[float]] | None = None,
    extra_values: Mapping[str, Sequence[float]] | None = None,
) -> PoincareSection:
    """Extract linearly interpolated crossings of a codimension-one section."""

    time_array = np.asarray(time, dtype=float)
    state_array = np.asarray(states, dtype=float)
    names = tuple(state_names)
    if time_array.ndim != 1 or state_array.ndim != 2:
        raise ValueError("time must be one-dimensional and states two-dimensional")
    if len(time_array) != state_array.shape[0]:
        raise ValueError("time and states must have the same sample count")
    if len(names) != state_array.shape[1]:
        raise ValueError("state_names must match the state dimension")
    if direction not in {"positive", "negative", "both"}:
        raise ValueError("direction must be 'positive', 'negative', or 'both'")
    if max_points is not None and max_points <= 0:
        raise ValueError("max_points must be positive")

    coordinate_index = names.index(coordinate)
    section_values = state_array[:, coordinate_index] - value
    sampled_series = {
        key: np.asarray(values, dtype=float)
        for key, values in (series or {}).items()
    }
    sampled_extras = {
        key: np.asarray(values, dtype=float)
        for key, values in (extra_values or {}).items()
    }
    points: list[dict[str, object]] = []

    for index in range(len(time_array) - 1):
        left = float(section_values[index])
        right = float(section_values[index + 1])
        if not _crosses(left, right, direction):
            continue

        span = right - left
        fraction = 0.0 if span == 0 else -left / span
        if fraction < 0.0 or fraction > 1.0:
            continue

        interpolated_state = state_array[index] + fraction * (state_array[index + 1] - state_array[index])
        interpolated_time = float(time_array[index] + fraction * (time_array[index + 1] - time_array[index]))
        record: dict[str, object] = {
            "time": interpolated_time,
            "state": interpolated_state.astype(float).tolist(),
            "coordinates": {
                name: float(interpolated_state[state_index])
                for state_index, name in enumerate(names)
            },
        }
        if sampled_series:
            record["series"] = {
                key: float(values[index] + fraction * (values[index + 1] - values[index]))
                for key, values in sampled_series.items()
            }
        if sampled_extras:
            record["extra"] = {
                key: float(values[index] + fraction * (values[index + 1] - values[index]))
                for key, values in sampled_extras.items()
            }
        points.append(record)

        if max_points is not None and len(points) >= max_points:
            break

    return PoincareSection(
        coordinate=coordinate,
        value=float(value),
        direction=direction,
        state_names=names,
        points=points,
    )


def _jacobian_evaluator(
    system: FirstOrderSystem,
    substitutions: Mapping[sp.Symbol, float] | None,
):
    jacobian = system.jacobian().subs(substitutions or {})
    unresolved = jacobian.free_symbols.difference({system.time, *system.state_symbols})
    if unresolved:
        names = ", ".join(sorted(str(symbol) for symbol in unresolved))
        raise ValueError(f"Jacobian has unresolved symbols: {names}")

    compiled = sp.lambdify((system.time, *system.state_symbols), jacobian, modules="numpy")

    def evaluate(t: float, state: np.ndarray) -> np.ndarray:
        return np.asarray(compiled(t, *state), dtype=float)

    return evaluate


def _default_tangent(dimension: int) -> np.ndarray:
    tangent = np.zeros(dimension, dtype=float)
    tangent[0] = 1.0
    return tangent


def _crosses(left: float, right: float, direction: str) -> bool:
    if direction == "positive":
        return left < 0.0 <= right
    if direction == "negative":
        return left > 0.0 >= right
    return (left < 0.0 <= right) or (left > 0.0 >= right)


__all__ = [
    "LyapunovResult",
    "PoincareSection",
    "finite_time_lyapunov",
    "poincare_section_crossings",
]
