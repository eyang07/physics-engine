from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Sequence

import numpy as np
from scipy.integrate import solve_ivp


Rhs = Callable[[float, Sequence[float]], np.ndarray]
# Split right-hand sides for separable Hamiltonians H = T(p) + V(q):
# velocity(p) = dH/dp gives dq/dt, force(q) = -dH/dq gives dp/dt.
SplitRhs = Callable[[Sequence[float]], np.ndarray]


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


@dataclass(frozen=True)
class EventIntegrationResult:
    """Adaptive integration output with located event crossings.

    ``event_times[i]``/``event_states[i]`` hold every detected zero crossing
    of ``events[i]``, in time order; empty arrays mean no crossing.
    """

    time: np.ndarray
    states: np.ndarray
    event_times: tuple[np.ndarray, ...]
    event_states: tuple[np.ndarray, ...]


def integrate_with_events(
    rhs: Rhs,
    initial_state: Sequence[float],
    t_span: tuple[float, float],
    *,
    events: Sequence[Callable[[float, Sequence[float]], float]],
    directions: Sequence[float] | None = None,
    terminal: Sequence[bool] | None = None,
    rtol: float = 1e-9,
    atol: float = 1e-12,
    max_step: float = np.inf,
) -> EventIntegrationResult:
    """Integrate adaptively and locate zero crossings of event functions.

    ``directions[i]`` restricts which crossings of ``events[i]`` count:
    ``+1`` rising, ``-1`` falling, ``0`` (default) both. Terminal events stop
    the integration at their first crossing. Crossing times come from the
    solver's root-finding, so they are sharp to integration tolerance — but
    still measured evidence, not validated numerics.
    """

    if not events:
        raise ValueError("at least one event function is required")
    t0, t1 = t_span
    if t1 <= t0:
        raise ValueError("t_span must satisfy t1 > t0")
    direction_values = tuple(directions) if directions is not None else (0.0,) * len(events)
    terminal_values = tuple(terminal) if terminal is not None else (False,) * len(events)
    if len(direction_values) != len(events) or len(terminal_values) != len(events):
        raise ValueError("directions and terminal flags must match the event count")

    wrapped_events = []
    for event, direction, is_terminal in zip(
        events, direction_values, terminal_values, strict=True
    ):

        def wrapper(t: float, y: np.ndarray, event=event) -> float:
            return float(event(t, y))

        wrapper.direction = direction
        wrapper.terminal = is_terminal
        wrapped_events.append(wrapper)

    solution = solve_ivp(
        rhs,
        (t0, t1),
        np.asarray(initial_state, dtype=float),
        method="DOP853",
        events=wrapped_events,
        rtol=rtol,
        atol=atol,
        max_step=max_step,
    )
    if not solution.success:
        raise RuntimeError(f"event integration failed: {solution.message}")

    return EventIntegrationResult(
        time=solution.t,
        states=solution.y.T,
        event_times=tuple(np.asarray(times, dtype=float) for times in solution.t_events),
        event_states=tuple(
            np.asarray(states, dtype=float).reshape(-1, len(solution.y))
            for states in solution.y_events
        ),
    )


def symplectic_euler_step(
    velocity: SplitRhs,
    force: SplitRhs,
    position: np.ndarray,
    momentum: np.ndarray,
    dt: float,
) -> tuple[np.ndarray, np.ndarray]:
    """First-order symplectic Euler step (momentum update first)."""

    new_momentum = momentum + dt * force(position)
    new_position = position + dt * velocity(new_momentum)
    return new_position, new_momentum


def stormer_verlet_step(
    velocity: SplitRhs,
    force: SplitRhs,
    position: np.ndarray,
    momentum: np.ndarray,
    dt: float,
) -> tuple[np.ndarray, np.ndarray]:
    """Second-order Störmer-Verlet (leapfrog) step."""

    half_momentum = momentum + 0.5 * dt * force(position)
    new_position = position + dt * velocity(half_momentum)
    new_momentum = half_momentum + 0.5 * dt * force(new_position)
    return new_position, new_momentum


_SYMPLECTIC_STEPPERS = {
    "symplectic-euler": symplectic_euler_step,
    "stormer-verlet": stormer_verlet_step,
}


def integrate_symplectic(
    velocity: SplitRhs,
    force: SplitRhs,
    initial_position: Sequence[float],
    initial_momentum: Sequence[float],
    t_span: tuple[float, float],
    dt: float,
    *,
    method: str = "stormer-verlet",
) -> tuple[np.ndarray, np.ndarray]:
    """Integrate a separable Hamiltonian flow with a symplectic method.

    The split form assumes ``H = T(p) + V(q)``: ``velocity`` depends only on
    the momenta and ``force`` only on the positions. Returned states stack
    ``[q_0, ..., q_n, p_0, ..., p_n]`` per row, matching
    ``HamiltonianSystem.numerical_rhs``. Symplecticity preserves the phase
    space structure; it does not make the trajectory exact, and energy error
    stays bounded rather than vanishing.
    """

    if dt <= 0:
        raise ValueError("dt must be positive")
    t0, t1 = t_span
    if t1 <= t0:
        raise ValueError("t_span must satisfy t1 > t0")
    if method not in _SYMPLECTIC_STEPPERS:
        names = ", ".join(sorted(_SYMPLECTIC_STEPPERS))
        raise ValueError(f"unknown symplectic method {method!r}; expected one of: {names}")
    stepper = _SYMPLECTIC_STEPPERS[method]

    position = np.asarray(initial_position, dtype=float)
    momentum = np.asarray(initial_momentum, dtype=float)
    if position.shape != momentum.shape:
        raise ValueError("initial position and momentum must have the same dimension")

    step_count = int(np.ceil((t1 - t0) / dt))
    times = t0 + dt * np.arange(step_count + 1)
    times[-1] = t1

    states = np.empty((step_count + 1, 2 * len(position)), dtype=float)
    states[0] = np.concatenate([position, momentum])

    for index in range(step_count):
        step_dt = times[index + 1] - times[index]
        position, momentum = stepper(velocity, force, position, momentum, step_dt)
        states[index + 1] = np.concatenate([position, momentum])

    return times, states


def integrate_adaptive(
    rhs: Rhs,
    initial_state: Sequence[float],
    t_span: tuple[float, float],
    *,
    sample_dt: float,
    transient: float = 0.0,
    rtol: float = 1e-9,
    atol: float = 1e-12,
    max_step: float = np.inf,
) -> tuple[np.ndarray, np.ndarray]:
    """Integrate an ODE adaptively and return uniformly sampled states."""

    if sample_dt <= 0:
        raise ValueError("sample_dt must be positive")
    if transient < 0:
        raise ValueError("transient must be non-negative")

    t0, t1 = t_span
    if t1 <= t0:
        raise ValueError("t_span must satisfy t1 > t0")
    sample_start = t0 + transient
    if sample_start >= t1:
        raise ValueError("transient must be shorter than the integration span")

    step_count = int(np.ceil((t1 - sample_start) / sample_dt))
    t_eval = sample_start + sample_dt * np.arange(step_count + 1)
    t_eval[-1] = t1

    solution = solve_ivp(
        rhs,
        (t0, t1),
        np.asarray(initial_state, dtype=float),
        method="DOP853",
        t_eval=t_eval,
        rtol=rtol,
        atol=atol,
        max_step=max_step,
    )
    if not solution.success:
        raise RuntimeError(f"adaptive integration failed: {solution.message}")

    return solution.t - sample_start, solution.y.T
