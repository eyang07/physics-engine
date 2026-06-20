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

SURFACE_GEODESIC_HINT = "surface-geodesic"


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


def _mesh_axes(
    family: str,
    *,
    u_count: int = 49,
    phi_count: int = 65,
) -> tuple[np.ndarray, np.ndarray]:
    if u_count < 2 or phi_count < 2:
        raise ValueError("surface mesh axes need at least two samples")
    if family == "sphere":
        u_axis = np.linspace(0.0, np.pi, u_count)
    elif family == "torus":
        u_axis = np.linspace(-np.pi, np.pi, u_count)
    elif family in {"paraboloid", "cone"}:
        u_axis = np.linspace(0.2, 2.4, u_count)
    elif family == "hyperboloid":
        u_axis = np.linspace(-1.4, 1.4, u_count)
    else:
        raise ValueError(f"unknown surface family: {family!r}")
    phi_axis = np.linspace(0.0, 2.0 * np.pi, phi_count)
    return u_axis, phi_axis


def _surface_triangles(u_count: int, phi_count: int) -> list[list[int]]:
    triangles: list[list[int]] = []
    for u_index in range(u_count - 1):
        for phi_index in range(phi_count - 1):
            lower_left = u_index * phi_count + phi_index
            lower_right = lower_left + 1
            upper_left = lower_left + phi_count
            upper_right = upper_left + 1
            triangles.append([lower_left, upper_left, lower_right])
            triangles.append([lower_right, upper_left, upper_right])
    return triangles


def _surface_mesh_payload(surface: SurfaceOfRevolution) -> dict[str, object]:
    u_axis, phi_axis = _mesh_axes(surface.family)
    u_grid, phi_grid = np.meshgrid(u_axis, phi_axis, indexing="ij")
    function = sp.lambdify(surface.coordinates, surface.embedding_expressions(), modules="numpy")
    components = function(u_grid, phi_grid)
    points = np.stack([np.asarray(component, dtype=float) for component in components], axis=-1)
    return {
        "kind": "surface-mesh",
        "rendererHint": SURFACE_GEODESIC_HINT,
        "family": surface.family,
        "coordinates": ["u", "phi"],
        "axes": [u_axis.astype(float).tolist(), phi_axis.astype(float).tolist()],
        "shape": [int(len(u_axis)), int(len(phi_axis))],
        "points": points.astype(float).tolist(),
        "triangles": _surface_triangles(len(u_axis), len(phi_axis)),
        "evaluation": "symbolic-exact",
    }


def _curvature_payload(surface: SurfaceOfRevolution) -> dict[str, object]:
    u_axis, phi_axis = _mesh_axes(surface.family)
    u_grid, phi_grid = np.meshgrid(u_axis, phi_axis, indexing="ij")
    expression = surface.gaussian_curvature()
    function = sp.lambdify(surface.coordinates, expression, modules="numpy")
    values = np.asarray(function(u_grid, phi_grid), dtype=float)
    values = np.broadcast_to(values, u_grid.shape).astype(float)
    return {
        "kind": "scalar-field",
        "rendererHint": "scalar-field",
        "name": "gaussianCurvature",
        "coordinates": ["u", "phi"],
        "axes": [u_axis.astype(float).tolist(), phi_axis.astype(float).tolist()],
        "shape": [int(len(u_axis)), int(len(phi_axis))],
        "values": values.tolist(),
        "quantity": "Gaussian curvature",
        "evaluation": "symbolic-exact",
    }


def _surface_geometry_payload(
    surface: SurfaceOfRevolution,
    positions: np.ndarray,
) -> dict[str, object]:
    return {
        "kind": "surface-geodesic",
        "rendererHint": SURFACE_GEODESIC_HINT,
        "family": surface.family,
        "surfaceMesh": _surface_mesh_payload(surface),
        "geodesic": {
            "kind": "embedded-polyline",
            "rendererHint": SURFACE_GEODESIC_HINT,
            "coordinates": ["x", "y", "z"],
            "source": "trajectory.states[x,y,z]",
            "points": positions.astype(float).tolist(),
            "evaluation": "integrated-geodesic-embedding",
        },
        "curvature": _curvature_payload(surface),
    }


def _embedded_tangent_vectors(
    surface: SurfaceOfRevolution,
    states: np.ndarray,
    vectors: np.ndarray,
) -> np.ndarray:
    tangent_expressions = surface.embedding_tangent_expressions()
    tangent_functions = [
        sp.lambdify(surface.coordinates, expressions, modules="numpy")
        for expressions in tangent_expressions
    ]
    basis = [
        np.column_stack(
            [
                np.broadcast_to(
                    np.asarray(component, dtype=float),
                    (states.shape[0],),
                )
                for component in function(states[:, 0], states[:, 1])
            ]
        )
        for function in tangent_functions
    ]
    return vectors[:, [0]] * basis[0] + vectors[:, [1]] * basis[1]


def _parallel_transport_payload(
    surface: SurfaceOfRevolution,
    time: np.ndarray,
    intrinsic_states: np.ndarray,
) -> dict[str, object]:
    curve = intrinsic_states[:, :2]
    metric_function = sp.lambdify(
        surface.coordinates,
        list(surface.first_fundamental_form()),
        modules="numpy",
    )
    initial_metric = np.asarray(metric_function(*curve[0]), dtype=float).reshape(2, 2)
    initial_vector = np.array([1.0 / np.sqrt(initial_metric[0, 0]), 0.0])
    transported = surface.metric_geometry().parallel_transport(
        time,
        curve,
        initial_vector,
    )
    embedded = _embedded_tangent_vectors(surface, intrinsic_states, transported)
    return {
        "kind": "parallel-transport-frame",
        "rendererHint": "parallel-transport",
        "coordinates": ["u", "phi"],
        "parameter": time.astype(float).tolist(),
        "initialVector": initial_vector.astype(float).tolist(),
        "vectors": transported.astype(float).tolist(),
        "embeddedVectors": embedded.astype(float).tolist(),
        "evaluation": "measured-trajectory-parallel-transport",
        "rigor": "measured",
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
        "surfaceGeometry": _surface_geometry_payload(surface, positions),
        "parallelTransport": _parallel_transport_payload(surface, time, intrinsic_states),
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
