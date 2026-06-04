from __future__ import annotations

from typing import Callable, Sequence

import numpy as np


Rhs = Callable[[float, Sequence[float]], np.ndarray]


def rk4_step(rhs: Rhs, t: float, state: np.ndarray, dt: float) -> np.ndarray:
    k1 = rhs(t, state)
    k2 = rhs(t + 0.5 * dt, state + 0.5 * dt * k1)
    k3 = rhs(t + 0.5 * dt, state + 0.5 * dt * k2)
    k4 = rhs(t + dt, state + dt * k3)
    return state + (dt / 6.0) * (k1 + 2.0 * k2 + 2.0 * k3 + k4)


def integrate_fixed_step(
    rhs: Rhs,
    initial_state: Sequence[float],
    t_span: tuple[float, float],
    dt: float,
) -> tuple[np.ndarray, np.ndarray]:
    """Integrate an ODE with fixed-step RK4."""

    if dt <= 0:
        raise ValueError("dt must be positive")

    t0, t1 = t_span
    if t1 <= t0:
        raise ValueError("t_span must satisfy t1 > t0")

    step_count = int(np.ceil((t1 - t0) / dt))
    times = t0 + dt * np.arange(step_count + 1)
    times[-1] = t1

    states = np.empty((step_count + 1, len(initial_state)), dtype=float)
    states[0] = np.asarray(initial_state, dtype=float)

    for index in range(step_count):
        step_dt = times[index + 1] - times[index]
        states[index + 1] = rk4_step(rhs, times[index], states[index], step_dt)

    return times, states

