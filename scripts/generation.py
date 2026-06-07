"""Shared helpers for generated example trajectories."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

import numpy as np

from engine.export import Trajectory
from engine.mechanics import LagrangianSystem
from engine.numerics import integrate_fixed_step
from engine.export.manifest import SystemSpec

StateTransform = Callable[[np.ndarray, np.ndarray], np.ndarray]


def physical_parameter_defaults(spec: SystemSpec) -> dict[str, float]:
    """Return default values for the symbols that appear in the Lagrangian."""

    return {
        parameter.name: parameter.default
        for parameter in spec.parameters
        if parameter.role == "physical"
    }


def initial_state_defaults(spec: SystemSpec) -> list[float]:
    """Return the default ``[q, qdot]`` state from a spec.

    Initial parameters follow the registry convention ``<state_name>0``:
    ``theta`` -> ``theta0`` and ``theta_dot`` -> ``theta_dot0``.
    """

    defaults = {
        parameter.name: parameter.default
        for parameter in spec.parameters
        if parameter.role == "initial"
    }
    state = []
    for variable in spec.state:
        if variable.kind not in {"coordinate", "velocity"}:
            continue
        parameter_name = f"{variable.name}0"
        if parameter_name not in defaults:
            raise KeyError(f"missing initial parameter default: {parameter_name}")
        state.append(defaults[parameter_name])
    return state


def generate_lagrangian_trajectory(
    *,
    spec: SystemSpec,
    system: LagrangianSystem,
    initial_state: Sequence[float],
    t_span: tuple[float, float],
    dt: float,
    state_names: Sequence[str],
    physical_parameters: Mapping[str, float],
    metadata: Mapping[str, Any] | None = None,
    state_transform: StateTransform | None = None,
) -> Trajectory:
    """Integrate a system and build a JSON-ready trajectory.

    ``state_transform`` receives ``(time, intrinsic_states)`` and can append
    derived rendering columns such as Cartesian embeddings.
    """

    time, intrinsic_states = integrate_fixed_step(
        system.numerical_rhs(),
        initial_state=initial_state,
        t_span=t_span,
        dt=dt,
    )
    states = state_transform(time, intrinsic_states) if state_transform else intrinsic_states
    series = spec.series(physical_parameters, states)
    return Trajectory.from_arrays(
        time=time,
        states=states,
        state_names=state_names,
        metadata=dict(metadata) if metadata is not None else None,
        series=series,
    )


def potential_plot_metadata(
    *,
    name: str,
    coordinate: str,
    coordinate_values: Sequence[float],
    potential_values: Sequence[float],
    energy_series: Sequence[float],
    coordinate_latex: str,
    potential_latex: str = "V",
) -> dict[str, Any]:
    """Return the viewer metadata payload for a one-dimensional potential."""

    return {
        "name": name,
        "coordinate": coordinate,
        "coordinateLatex": coordinate_latex,
        "potentialLatex": potential_latex,
        "coordinateValues": np.asarray(coordinate_values, dtype=float).tolist(),
        "potentialValues": np.asarray(potential_values, dtype=float).tolist(),
        "energy": float(np.mean(np.asarray(energy_series, dtype=float))),
    }


def write_trajectory_outputs(
    trajectory: Trajectory,
    output: Path,
    viewer_output: Path | None = None,
) -> Trajectory:
    """Write the primary output and optional viewer copy."""

    trajectory.write_json(output)
    if viewer_output is not None:
        trajectory.write_json(viewer_output)
    return trajectory
