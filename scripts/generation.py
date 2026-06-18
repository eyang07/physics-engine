"""Shared helpers for generated example trajectories."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

import numpy as np

from engine.dynamics import InvariantResidual, invariant_residuals
from engine.export import Trajectory
from engine.export.manifest import ParameterVariant, SystemSpec
from engine.mechanics import LagrangianSystem
from engine.numerics import integrate_fixed_step

StateTransform = Callable[[np.ndarray, np.ndarray], np.ndarray]
VariantWriter = Callable[[ParameterVariant, Path, Path | None], Trajectory]


def _invariant_residual_record(residual: InvariantResidual) -> dict[str, Any]:
    return {
        "name": residual.name,
        "series": residual.name,
        "reference": residual.reference,
        "referenceKind": "initial",
        "rigor": "measured",
        "maxAbs": residual.max_abs,
        "rms": residual.rms,
        "maxRelative": residual.max_relative,
        "scale": residual.scale,
    }


def invariant_residual_records(series: Mapping[str, Sequence[float]]) -> list[dict[str, Any]]:
    """Return measured residual metadata for sampled invariant series."""

    return [
        _invariant_residual_record(residual)
        for residual in invariant_residuals(series).values()
    ]


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
    output_metadata = dict(metadata) if metadata is not None else None
    if series:
        output_metadata = dict(output_metadata or {})
        output_metadata["invariantResiduals"] = invariant_residual_records(series)
    return Trajectory.from_arrays(
        time=time,
        states=states,
        state_names=state_names,
        metadata=output_metadata,
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


def variant_filename(data_path: str, *, system_name: str) -> str:
    """Return the relative JSON filename for a manifest variant data path."""

    prefix = "/data/"
    if not data_path.startswith(prefix):
        raise ValueError(
            f"{system_name} variant path must start with {prefix!r}: {data_path!r}"
        )
    return data_path.removeprefix(prefix)


def write_parameter_variant_trajectories(
    spec: SystemSpec,
    output_dir: Path,
    *,
    write_variant: VariantWriter,
    viewer_output_dir: Path | None = None,
    system_name: str | None = None,
) -> list[Trajectory]:
    """Write every non-default manifest variant for one system.

    The manifest entry whose `data_path` matches the primary system output is
    the default trajectory and is generated by the caller's primary writer.
    """

    name = system_name or spec.title
    trajectories = []
    for variant in spec.variants:
        if variant.data_path == spec.data_path:
            continue

        filename = variant_filename(variant.data_path, system_name=name)
        viewer_output = (
            None if viewer_output_dir is None else viewer_output_dir / filename
        )
        trajectories.append(
            write_variant(
                variant,
                output_dir / filename,
                viewer_output,
            )
        )
    return trajectories
