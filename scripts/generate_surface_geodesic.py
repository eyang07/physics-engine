from __future__ import annotations

import argparse
from pathlib import Path
from typing import Mapping, Sequence

import numpy as np
import sympy as sp

from engine.export import Trajectory
from engine.numerics import integrate_fixed_step
from scripts.generation import invariant_residual_records, write_trajectory_outputs
from systems.surface_geodesic import (
    SurfaceFamily,
    SurfaceOfRevolution,
    cone_surface,
    hyperboloid_surface,
    paraboloid_surface,
    sphere_surface,
    torus_surface,
)


def _surface_from_values(
    family: SurfaceFamily,
    parameters: Mapping[str, float],
) -> SurfaceOfRevolution:
    if family == "sphere":
        return sphere_surface(radius=parameters.get("R", 1.0))
    if family == "torus":
        return torus_surface(
            major_radius=parameters.get("R_major", 2.0),
            minor_radius=parameters.get("r_minor", 0.7),
        )
    if family == "paraboloid":
        return paraboloid_surface(scale=parameters.get("a", 0.35))
    if family == "cone":
        return cone_surface(slope=parameters.get("c", 0.65))
    if family == "hyperboloid":
        return hyperboloid_surface(
            waist_radius=parameters.get("a", 0.8),
            height_scale=parameters.get("c", 0.9),
        )
    raise ValueError(f"unknown surface family: {family!r}")


def _default_physical_parameters(family: SurfaceFamily) -> dict[str, float]:
    if family == "sphere":
        return {"R": 1.0}
    if family == "torus":
        return {"R_major": 2.0, "r_minor": 0.7}
    if family == "paraboloid":
        return {"a": 0.35}
    if family == "cone":
        return {"c": 0.65}
    if family == "hyperboloid":
        return {"a": 0.8, "c": 0.9}
    raise ValueError(f"unknown surface family: {family!r}")


def _default_initial_state(family: SurfaceFamily) -> list[float]:
    if family == "sphere":
        return [1.12, 0.0, 0.42, 1.05]
    if family == "torus":
        return [0.72, 0.0, 0.38, 0.92]
    if family == "paraboloid":
        return [1.15, 0.0, 0.18, 0.82]
    if family == "cone":
        return [1.2, 0.0, 0.22, 0.75]
    if family == "hyperboloid":
        return [0.35, 0.0, 0.24, 0.88]
    raise ValueError(f"unknown surface family: {family!r}")


def _embedding(surface: SurfaceOfRevolution, states: np.ndarray) -> np.ndarray:
    expressions = surface.embedding_expressions()
    function = sp.lambdify(surface.coordinates, expressions, modules="numpy")
    values = function(states[:, 0], states[:, 1])
    return np.column_stack([np.asarray(component, dtype=float) for component in values])


def _invariant_series(surface: SurfaceOfRevolution, states: np.ndarray) -> dict[str, list[float]]:
    state_symbols = (*surface.coordinates, *surface.velocities)
    columns = [states[:, index] for index in range(4)]
    series: dict[str, list[float]] = {}
    for name, expression in {
        "H": surface.kinetic_energy(),
        "clairaut": surface.clairaut_quantity(),
    }.items():
        function = sp.lambdify(state_symbols, expression, modules="numpy")
        values = np.asarray(function(*columns), dtype=float)
        series[name] = np.broadcast_to(values, (states.shape[0],)).astype(float).tolist()
    return series


def _renderer_hints(surface: SurfaceOfRevolution, positions: np.ndarray) -> dict[str, object]:
    padding = 0.1 * max(1.0, float(np.max(np.ptp(positions, axis=0))))
    bounds = {
        axis: [
            float(np.min(positions[:, index]) - padding),
            float(np.max(positions[:, index]) + padding),
        ]
        for index, axis in enumerate(("x", "y", "z"))
    }
    center = [float(value) for value in np.mean(positions, axis=0)]
    span = max(bounds[axis][1] - bounds[axis][0] for axis in ("x", "y", "z"))
    return {
        "bounds": bounds,
        "camera": {
            "position": [center[0] + 1.4 * span, center[1] - 1.6 * span, center[2] + span],
            "target": center,
        },
        "referenceGeometry": [
            {
                "kind": "surfaceOfRevolution",
                "family": surface.family,
            }
        ],
    }


def generate_surface_geodesic_trajectory(
    *,
    family: SurfaceFamily = "torus",
    physical_parameters: Mapping[str, float] | None = None,
    initial_state: Sequence[float] | None = None,
    t_span: tuple[float, float] = (0.0, 18.0),
    dt: float = 0.01,
) -> Trajectory:
    parameters = dict(_default_physical_parameters(family))
    parameters.update(physical_parameters or {})
    surface = _surface_from_values(family, parameters)
    state0 = list(initial_state) if initial_state is not None else _default_initial_state(family)
    system = surface.geodesic_system()
    time, intrinsic_states = integrate_fixed_step(
        system.numerical_rhs(),
        initial_state=state0,
        t_span=t_span,
        dt=dt,
    )
    positions = _embedding(surface, intrinsic_states)
    states = np.column_stack([intrinsic_states, positions])
    series = _invariant_series(surface, intrinsic_states)
    metadata = {
        "system": "surface_geodesic",
        "family": family,
        "parameters": parameters,
        "rendererHints": _renderer_hints(surface, positions),
        "invariantResiduals": invariant_residual_records(series),
    }
    return Trajectory.from_arrays(
        time=time,
        states=states,
        state_names=("u", "phi", "u_dot", "phi_dot", "x", "y", "z"),
        metadata=metadata,
        series=series,
    )


def write_surface_geodesic_trajectory(
    output: Path,
    *,
    viewer_output: Path | None = None,
    family: SurfaceFamily = "torus",
    t_end: float = 18.0,
    dt: float = 0.01,
) -> Trajectory:
    trajectory = generate_surface_geodesic_trajectory(
        family=family,
        t_span=(0.0, t_end),
        dt=dt,
    )
    return write_trajectory_outputs(trajectory, output, viewer_output)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate a surface-of-revolution geodesic.")
    parser.add_argument("--output", type=Path, default=Path("data/generated/surface_geodesic.json"))
    parser.add_argument(
        "--viewer-output",
        type=Path,
        default=Path("viewer/public/data/surface_geodesic.json"),
    )
    parser.add_argument(
        "--family",
        choices=("sphere", "torus", "paraboloid", "cone", "hyperboloid"),
        default="torus",
    )
    parser.add_argument("--t-end", type=float, default=18.0)
    parser.add_argument("--dt", type=float, default=0.01)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> None:
    args = parse_args(argv)
    trajectory = write_surface_geodesic_trajectory(
        args.output,
        viewer_output=args.viewer_output,
        family=args.family,
        t_end=args.t_end,
        dt=args.dt,
    )
    print(f"Wrote {len(trajectory.time)} samples to {args.output}")
    if args.viewer_output is not None:
        print(f"Wrote viewer copy to {args.viewer_output}")


if __name__ == "__main__":
    main()
