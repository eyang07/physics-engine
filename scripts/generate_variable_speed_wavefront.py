from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

import numpy as np
import sympy as sp

from engine.dynamics import integrate_ray_bundle, ray_bundle_coordinate_bounds
from engine.export import Trajectory
from systems.variable_speed_wavefront import build_system, wave_speed


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
    viewport_x = [float(x0 - 0.25), float(-x0 + 0.35)]
    viewport_y = [float(y_span[0] - 0.3), float(y_span[1] + 0.3)]
    return {
        "bounds": ray_bundle_coordinate_bounds(rays, coordinate_count=2),
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

    y0_values = np.linspace(y_span[0], y_span[1], ray_count)
    initial_states = []
    for y0 in y0_values:
        xi0, eta0 = _initial_covector(
            x=x0,
            y=float(y0),
            base_speed=base_speed,
            lens_strength=lens_strength,
            lens_width=lens_width,
        )
        initial_states.append([x0, float(y0), xi0, eta0])

    bundle = integrate_ray_bundle(
        system,
        initial_states,
        t_span=t_span,
        dt=dt,
        state_names=["x", "y", "xi", "eta"],
    )

    metadata = {
        "system": "variable_speed_wavefront",
        "kind": "ray-bundle",
        "parameters": {
            "base_speed": base_speed,
            "lens_strength": lens_strength,
            "lens_width": lens_width,
        },
        "rayBundle": {
            "stateNames": list(bundle.state_names),
            "initialY": y0_values.astype(float).tolist(),
            "rays": bundle.ray_records(),
        },
        "wavefronts": bundle.wavefront_records(snapshot_stride),
        "rendererHints": wavefront_renderer_hints(bundle.rays, x0=x0, y_span=y_span),
        "hamiltonian": {
            "initial": bundle.hamiltonian_initials.astype(float).tolist(),
            "maxDrift": bundle.max_hamiltonian_drift,
        },
    }

    return Trajectory.from_arrays(
        time=bundle.time,
        states=bundle.center_ray,
        state_names=bundle.state_names,
        metadata=metadata,
        series={
            "p": bundle.hamiltonians[bundle.center_index].astype(float).tolist(),
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
