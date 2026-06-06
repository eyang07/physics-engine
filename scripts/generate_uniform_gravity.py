from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

import numpy as np

from engine.export import Trajectory
from engine.numerics import integrate_fixed_step
from scripts.example_specs import UNIFORM_GRAVITY
from systems.uniform_gravity import build_system


def generate_uniform_gravity_trajectory(
    *,
    mass: float = 1.0,
    gravity: float = 9.81,
    initial_state: Sequence[float] = (0.0, 0.0, 1.7, 4.6),
    t_span: tuple[float, float] = (0.0, 1.05),
    dt: float = 0.005,
) -> Trajectory:
    system = build_system(mass=mass, gravity=gravity)
    time, states = integrate_fixed_step(system.numerical_rhs(), initial_state, t_span, dt)
    series = UNIFORM_GRAVITY.series({"m": mass, "g": gravity}, states)
    z_values = states[:, 1]
    z_span = float(z_values.max() - z_values.min())
    pad = max(0.25, z_span * 0.18)
    coordinate_values = np.linspace(float(z_values.min() - pad), float(z_values.max() + pad), 220)
    potential_values = mass * gravity * coordinate_values
    return Trajectory.from_arrays(
        time=time,
        states=states,
        state_names=["x", "z", "x_dot", "z_dot"],
        metadata={
            "system": "uniform_gravity",
            "mass": mass,
            "gravity": gravity,
            "potentialPlots": [
                {
                    "name": "gravity_potential",
                    "coordinate": "z",
                    "coordinateLatex": "z",
                    "potentialLatex": "V",
                    "coordinateValues": coordinate_values.tolist(),
                    "potentialValues": potential_values.tolist(),
                    "energy": float(np.mean(series["H"])),
                }
            ],
        },
        series=series,
    )


def write_uniform_gravity_trajectory(
    output: Path,
    *,
    viewer_output: Path | None = None,
) -> Trajectory:
    trajectory = generate_uniform_gravity_trajectory()
    trajectory.write_json(output)
    if viewer_output is not None:
        trajectory.write_json(viewer_output)
    return trajectory


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate uniform-gravity projectile data.")
    parser.add_argument("--output", type=Path, default=Path("data/generated/uniform_gravity.json"))
    parser.add_argument("--viewer-output", type=Path, default=Path("viewer/public/data/uniform_gravity.json"))
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> None:
    args = parse_args(argv)
    write_uniform_gravity_trajectory(args.output, viewer_output=args.viewer_output)
    print(f"Wrote trajectory to {args.output}")


if __name__ == "__main__":
    main()
