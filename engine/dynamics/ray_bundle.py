from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

import numpy as np
import sympy as sp

from engine.dynamics.cotangent import CotangentHamiltonianSystem
from engine.numerics import integrate_fixed_step


@dataclass(frozen=True)
class RayBundleResult:
    time: np.ndarray
    rays: np.ndarray
    hamiltonians: np.ndarray
    state_names: tuple[str, ...]
    coordinate_count: int

    @property
    def center_index(self) -> int:
        return self.rays.shape[0] // 2

    @property
    def center_ray(self) -> np.ndarray:
        return self.rays[self.center_index]

    @property
    def hamiltonian_initials(self) -> np.ndarray:
        return self.hamiltonians[:, 0]

    @property
    def max_hamiltonian_drift(self) -> float:
        return float(np.max(np.abs(self.hamiltonians - self.hamiltonians[:, [0]])))

    def ray_records(self) -> list[dict[str, object]]:
        return [
            {
                "index": index,
                "states": self.rays[index].astype(float).tolist(),
            }
            for index in range(self.rays.shape[0])
        ]

    def wavefront_records(self, snapshot_stride: int) -> list[dict[str, object]]:
        return [
            {
                "time": float(self.time[index]),
                "points": self.rays[:, index, : self.coordinate_count].astype(float).tolist(),
            }
            for index in ray_bundle_snapshot_indices(len(self.time), snapshot_stride)
        ]


def integrate_ray_bundle(
    system: CotangentHamiltonianSystem,
    initial_states: Sequence[Sequence[float]],
    *,
    t_span: tuple[float, float],
    dt: float,
    state_names: Sequence[str] | None = None,
    substitutions: Mapping[sp.Symbol, float] | None = None,
) -> RayBundleResult:
    """Integrate a bundle of cotangent Hamiltonian rays on a shared time grid."""

    initial_array = np.asarray(initial_states, dtype=float)
    if initial_array.ndim != 2:
        raise ValueError("initial_states must be a two-dimensional array")
    if initial_array.shape[0] == 0:
        raise ValueError("initial_states must contain at least one ray")
    if initial_array.shape[1] != len(system.state_symbols):
        raise ValueError("each initial state must match the system state dimension")

    names = tuple(state_names or [str(symbol) for symbol in system.state_symbols])
    if len(names) != initial_array.shape[1]:
        raise ValueError("state_names must match the system state dimension")

    rhs = system.numerical_rhs(substitutions)
    hamiltonian = _hamiltonian_evaluator(system, substitutions)

    shared_time: np.ndarray | None = None
    ray_states: list[np.ndarray] = []
    ray_hamiltonians: list[np.ndarray] = []
    for initial_state in initial_array:
        time, states = integrate_fixed_step(
            rhs,
            initial_state=initial_state,
            t_span=t_span,
            dt=dt,
        )
        if shared_time is None:
            shared_time = time
        elif not np.array_equal(shared_time, time):
            raise RuntimeError("ray integration produced inconsistent time samples")
        ray_states.append(states)
        ray_hamiltonians.append(hamiltonian(states))

    assert shared_time is not None
    return RayBundleResult(
        time=shared_time,
        rays=np.stack(ray_states, axis=0),
        hamiltonians=np.stack(ray_hamiltonians, axis=0),
        state_names=names,
        coordinate_count=len(system.coordinates),
    )


def ray_bundle_snapshot_indices(sample_count: int, snapshot_stride: int) -> tuple[int, ...]:
    if sample_count <= 0:
        raise ValueError("sample_count must be positive")
    if snapshot_stride <= 0:
        raise ValueError("snapshot_stride must be positive")

    indices = list(range(0, sample_count, snapshot_stride))
    if indices[-1] != sample_count - 1:
        indices.append(sample_count - 1)
    return tuple(indices)


def ray_bundle_coordinate_bounds(
    rays: np.ndarray,
    *,
    coordinate_count: int,
    coordinate_names: Sequence[str] | None = None,
    include_flat_z: bool = True,
) -> dict[str, list[float]]:
    if coordinate_count <= 0:
        raise ValueError("coordinate_count must be positive")

    ray_array = np.asarray(rays, dtype=float)
    if ray_array.ndim != 3 or ray_array.shape[2] < coordinate_count:
        raise ValueError("rays must have shape (ray, sample, state)")

    names = tuple(coordinate_names or _default_coordinate_names(coordinate_count))
    if len(names) != coordinate_count:
        raise ValueError("coordinate_names must match coordinate_count")

    positions = ray_array[:, :, :coordinate_count].reshape(-1, coordinate_count)
    bounds = {
        name: [float(positions[:, index].min()), float(positions[:, index].max())]
        for index, name in enumerate(names)
    }
    if include_flat_z and "z" not in bounds:
        bounds["z"] = [0.0, 0.0]
    return bounds


def _hamiltonian_evaluator(
    system: CotangentHamiltonianSystem,
    substitutions: Mapping[sp.Symbol, float] | None,
):
    symbol = system.symbol.subs(substitutions or {})
    unresolved = symbol.free_symbols.difference(system.state_symbols)
    if unresolved:
        names = ", ".join(sorted(str(symbol) for symbol in unresolved))
        raise ValueError(f"Hamiltonian has unresolved symbols: {names}")

    evaluator = sp.lambdify(system.state_symbols, symbol, modules="numpy")

    def evaluate(states: np.ndarray) -> np.ndarray:
        values = evaluator(*(states[:, index] for index in range(states.shape[1])))
        array = np.asarray(values, dtype=float)
        if array.shape == ():
            return np.full(states.shape[0], float(array), dtype=float)
        return array.reshape(states.shape[0])

    return evaluate


def _default_coordinate_names(coordinate_count: int) -> tuple[str, ...]:
    names = ("x", "y", "z")
    if coordinate_count <= len(names):
        return names[:coordinate_count]
    return tuple(f"q{index}" for index in range(coordinate_count))


__all__ = [
    "RayBundleResult",
    "integrate_ray_bundle",
    "ray_bundle_coordinate_bounds",
    "ray_bundle_snapshot_indices",
]
