from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

import numpy as np
import sympy as sp

from engine.export import Trajectory
from engine.numerics import integrate_fixed_step
from systems.variable_speed_wavefront import build_system, wave_speed


def _hamiltonian_values(
    states: np.ndarray,
    *,
    base_speed: float,
    lens_strength: float,
    lens_width: float,
) -> np.ndarray:
    x = states[:, 0]
    y = states[:, 1]
    xi = states[:, 2]
    eta = states[:, 3]
    speed = base_speed * (1 - lens_strength * np.exp(-(x**2 + y**2) / (2 * lens_width**2)))
    return 0.5 * speed**2 * (xi**2 + eta**2)


def _initial_covector(
    *,
    x: float,
    y: float,
    base_speed: float,
    lens_strength: float,
    lens_width: float,
) -> tuple[float, float]:
    speed = float(
        wave_speed(
            sp.Float(x),
            sp.Float(y),
            base_speed=base_speed,
            lens_strength=lens_strength,
            lens_width=lens_width,
        )
    )
    return 1.0 / speed, 0.0


def wavefront_renderer_hints(
    rays: np.ndarray,
    *,
    x0: float,
    y_span: tuple[float, float],
) -> dict[str, object]:
    positions = rays[:, :, :2].reshape(-1, 2)
    x_min = float(positions[:, 0].min())
    x_max = float(positions[:, 0].max())
    y_min = float(positions[:, 1].min())
    y_max = float(positions[:, 1].max())
    viewport_x = [float(x0 - 0.25), float(-x0 + 0.35)]
    viewport_y = [float(y_span[0] - 0.3), float(y_span[1] + 0.3)]
    return {
        "bounds": {
            "x": [x_min, x_max],
            "y": [y_min, y_max],
            "z": [0.0, 0.0],
        },
        "viewportBounds": {
            "x": viewport_x,
            "y": viewport_y,
            "z": [0.0, 0.0],
        },
        "camera": {
            "position": [0.0, 0.0, 6.0],
            "target": [(viewport_x[0] + viewport_x[1]) / 2, (viewport_y[0] + viewport_y[1]) / 2, 0.0],
        },
        "referenceGeometry": [
            {
                "kind": "slowSpeedLens",
                "position": [0.0, 0.0, 0.0],
            }
        ],
    }


def generate_variable_speed_wavefront(
    *,
    base_speed: float = 1.0,
    lens_strength: float = 0.42,
    lens_width: float = 0.85,
    ray_count: int = 33,
    y_span: tuple[float, float] = (-1.8, 1.8),
    x0: float = -3.0,
    t_span: tuple[float, float] = (0.0, 12.0),
    dt: float = 0.01,
    snapshot_stride: int = 40,
) -> Trajectory:
    if ray_count < 3:
        raise ValueError("ray_count must be at least 3")

    system = build_system(
        base_speed=base_speed,
        lens_strength=lens_strength,
        lens_width=lens_width,
    )
    rhs = system.numerical_rhs()

    y0_values = np.linspace(y_span[0], y_span[1], ray_count)
    ray_states: list[np.ndarray] = []
    ray_hamiltonians: list[np.ndarray] = []
    shared_time: np.ndarray | None = None
    for y0 in y0_values:
        xi0, eta0 = _initial_covector(
            x=x0,
            y=float(y0),
            base_speed=base_speed,
            lens_strength=lens_strength,
            lens_width=lens_width,
        )
        time, states = integrate_fixed_step(
            rhs,
            initial_state=[x0, float(y0), xi0, eta0],
            t_span=t_span,
            dt=dt,
        )
        if shared_time is None:
            shared_time = time
        ray_states.append(states)
        ray_hamiltonians.append(
            _hamiltonian_values(
                states,
                base_speed=base_speed,
                lens_strength=lens_strength,
                lens_width=lens_width,
            )
        )

    assert shared_time is not None
    rays = np.stack(ray_states, axis=0)
    hamiltonians = np.stack(ray_hamiltonians, axis=0)
    center_ray = rays[ray_count // 2]
    snapshot_indices = list(range(0, len(shared_time), snapshot_stride))
    if snapshot_indices[-1] != len(shared_time) - 1:
        snapshot_indices.append(len(shared_time) - 1)

    wavefronts = [
        {
            "time": float(shared_time[index]),
            "points": rays[:, index, :2].astype(float).tolist(),
        }
        for index in snapshot_indices
    ]

    metadata = {
        "system": "variable_speed_wavefront",
        "kind": "ray-bundle",
        "parameters": {
            "base_speed": base_speed,
            "lens_strength": lens_strength,
            "lens_width": lens_width,
        },
        "rayBundle": {
            "stateNames": ["x", "y", "xi", "eta"],
            "initialY": y0_values.astype(float).tolist(),
            "rays": [
                {
                    "index": index,
                    "states": rays[index].astype(float).tolist(),
                }
                for index in range(ray_count)
            ],
        },
        "wavefronts": wavefronts,
        "rendererHints": wavefront_renderer_hints(rays, x0=x0, y_span=y_span),
        "hamiltonian": {
            "initial": hamiltonians[:, 0].astype(float).tolist(),
            "maxDrift": float(np.max(np.abs(hamiltonians - hamiltonians[:, [0]]))),
        },
    }

    return Trajectory.from_arrays(
        time=shared_time,
        states=center_ray,
        state_names=["x", "y", "xi", "eta"],
        metadata=metadata,
        series={
            "p": hamiltonians[ray_count // 2].astype(float).tolist(),
        },
    )


def write_variable_speed_wavefront(
    output: Path,
    *,
    viewer_output: Path | None = None,
) -> Trajectory:
    trajectory = generate_variable_speed_wavefront()
    trajectory.write_json(output)
    if viewer_output is not None:
        trajectory.write_json(viewer_output)
    return trajectory


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate variable-speed wavefront ray data.")
    parser.add_argument("--output", type=Path, default=Path("data/generated/variable_speed_wavefront.json"))
    parser.add_argument("--viewer-output", type=Path, default=Path("viewer/public/data/variable_speed_wavefront.json"))
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> None:
    args = parse_args(argv)
    write_variable_speed_wavefront(args.output, viewer_output=args.viewer_output)
    print(f"Wrote trajectory to {args.output}")


if __name__ == "__main__":
    main()
