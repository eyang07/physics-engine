from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

import numpy as np
import sympy as sp

from engine.dynamics import finite_time_lyapunov
from engine.export import Trajectory
from engine.numerics import integrate_adaptive
from scripts.example_specs import LORENZ
from scripts.generation import write_trajectory_outputs
from systems.lorenz_attractor import build_system


def _real_float(value: sp.Expr) -> float:
    numeric = complex(sp.N(value))
    return float(numeric.real)


def _complex_pair(value: sp.Expr) -> dict[str, float]:
    numeric = complex(sp.N(value))
    return {"real": float(numeric.real), "imag": float(numeric.imag)}


def lorenz_renderer_hints(states: np.ndarray) -> dict[str, object]:
    """Return renderer metadata derived from the attractor bounds."""

    raw_x = states[:, 0]
    raw_y = states[:, 1]
    raw_z = states[:, 2]
    # The viewer maps raw Lorenz coordinates (x, y, z) to scene (x, z, y).
    scene_min = np.array([raw_x.min(), raw_z.min(), raw_y.min()], dtype=float)
    scene_max = np.array([raw_x.max(), raw_z.max(), raw_y.max()], dtype=float)
    center = (scene_min + scene_max) / 2
    size = scene_max - scene_min
    scale = float(3.1 / max(size.max(), 1.0))

    transformed_min = (scene_min - center) * scale
    transformed_max = (scene_max - center) * scale

    return {
        "bounds": {
            "x": [float(transformed_min[0]), float(transformed_max[0])],
            "y": [float(transformed_min[1]), float(transformed_max[1])],
            "z": [float(transformed_min[2]), float(transformed_max[2])],
        },
        "camera": {
            "position": [3.0, 2.05, 4.4],
            "target": [0.0, 0.05, 0.0],
        },
        "transform": {
            "center": [float(center[0]), float(center[1]), float(center[2])],
            "scale": scale,
        },
        "referenceGeometry": [
            {
                "kind": "guideRings",
                "radius": float(max(size[0], size[2]) * scale * 0.36),
                "scale": [1.0, 1.0, 0.7],
                "yValues": [-0.68, 0.0, 0.68],
            },
            {
                "kind": "fixedPointMarkers",
                "radius": 0.04,
            },
        ],
    }


def generate_lorenz_trajectory(
    *,
    sigma: float = 10.0,
    rho: float = 28.0,
    beta: float = 8.0 / 3.0,
    initial_state: Sequence[float] = (0.0, 1.0, 1.05),
    t_span: tuple[float, float] = (0.0, 42.0),
    transient: float = 8.0,
    sample_dt: float = 0.01,
) -> Trajectory:
    system = build_system(sigma=sigma, rho=rho, beta=beta)
    time, states = integrate_adaptive(
        system.numerical_rhs(),
        initial_state,
        t_span,
        sample_dt=sample_dt,
        transient=transient,
        max_step=0.025,
    )
    rhs_values = np.asarray([system.numerical_rhs()(float(t), state) for t, state in zip(time, states, strict=True)])
    speed = np.linalg.norm(rhs_values, axis=1)
    radius = np.linalg.norm(states, axis=1)
    lyapunov = finite_time_lyapunov(system, time, states)

    x, y, z = system.state
    fixed_points = []
    for point in system.fixed_points():
        coordinates = {symbol.name: _real_float(point[symbol]) for symbol in system.state}
        eigenvalues = [
            _complex_pair(eigenvalue)
            for eigenvalue in system.eigenvalues_at(point)
        ]
        fixed_points.append({"coordinates": coordinates, "eigenvalues": eigenvalues})

    bounds = {
        name: {
            "min": float(states[:, index].min()),
            "max": float(states[:, index].max()),
        }
        for index, name in enumerate(("x", "y", "z"))
    }

    return Trajectory.from_arrays(
        time=time,
        states=states,
        state_names=["x", "y", "z"],
        metadata={
            "system": "lorenz_attractor",
            "kind": "first-order-flow",
            "parameters": {"sigma": sigma, "rho": rho, "beta": beta},
            "bounds": bounds,
            "divergence": float(system.divergence()),
            "fixedPoints": fixed_points,
            "diagnostics": {
                "lyapunov": {
                    "kind": "finite-time-largest",
                    "method": "sampled-variational-jacobian",
                    "series": "ftle",
                    "localGrowthSeries": "lyapunov_local_growth",
                    "initialTangent": lyapunov.initial_tangent.astype(float).tolist(),
                    "finalTangent": lyapunov.final_tangent.astype(float).tolist(),
                    "finalEstimate": lyapunov.final_estimate,
                    "sampleCount": int(len(time)),
                    "timeWindow": [float(time[0]), float(time[-1])],
                }
            },
            "rendererHints": lorenz_renderer_hints(states),
        },
        series={
            "speed": speed.tolist(),
            "radius": radius.tolist(),
            "ftle": lyapunov.estimate.astype(float).tolist(),
            "lyapunov_local_growth": lyapunov.local_growth.astype(float).tolist(),
        },
    )


def write_lorenz_trajectory(
    output: Path,
    *,
    viewer_output: Path | None = None,
    sigma: float = 10.0,
    rho: float = 28.0,
    beta: float = 8.0 / 3.0,
    initial_state: Sequence[float] = (0.0, 1.0, 1.05),
) -> Trajectory:
    trajectory = generate_lorenz_trajectory(
        sigma=sigma,
        rho=rho,
        beta=beta,
        initial_state=initial_state,
    )
    return write_trajectory_outputs(trajectory, output, viewer_output)


def _variant_filename(data_path: str) -> str:
    prefix = "/data/"
    if not data_path.startswith(prefix):
        raise ValueError(f"Lorenz variant path must start with {prefix!r}: {data_path!r}")
    return data_path.removeprefix(prefix)


def write_lorenz_variant_trajectories(
    output_dir: Path,
    *,
    viewer_output_dir: Path | None = None,
) -> list[Trajectory]:
    trajectories = []
    for variant in LORENZ.variants:
        if variant.data_path == LORENZ.data_path:
            continue

        parameters = variant.parameters
        filename = _variant_filename(variant.data_path)
        viewer_output = None if viewer_output_dir is None else viewer_output_dir / filename
        trajectories.append(
            write_lorenz_trajectory(
                output_dir / filename,
                viewer_output=viewer_output,
                sigma=parameters["sigma"],
                rho=parameters["rho"],
                beta=parameters["beta"],
                initial_state=(
                    parameters["x0"],
                    parameters["y0"],
                    parameters["z0"],
                ),
            )
        )
    return trajectories


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate Lorenz attractor data.")
    parser.add_argument("--output", type=Path, default=Path("data/generated/lorenz_attractor.json"))
    parser.add_argument("--viewer-output", type=Path, default=Path("viewer/public/data/lorenz_attractor.json"))
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> None:
    args = parse_args(argv)
    write_lorenz_trajectory(args.output, viewer_output=args.viewer_output)
    print(f"Wrote trajectory to {args.output}")


if __name__ == "__main__":
    main()
