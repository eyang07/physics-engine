from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

import numpy as np

from engine.export import Trajectory
from scripts.example_specs import UNIFORM_GRAVITY
from scripts.generation import (
    generate_lagrangian_trajectory,
    potential_plot_metadata,
    write_trajectory_outputs,
)
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
    trajectory = generate_lagrangian_trajectory(
        spec=UNIFORM_GRAVITY,
        system=system,
        initial_state=initial_state,
        t_span=t_span,
        dt=dt,
        state_names=["x", "z", "x_dot", "z_dot"],
        physical_parameters={"m": mass, "g": gravity},
    )
    assert trajectory.series is not None
    z_values = trajectory.states[:, 1]
    z_span = float(z_values.max() - z_values.min())
    pad = max(0.25, z_span * 0.18)
    coordinate_values = np.linspace(float(z_values.min() - pad), float(z_values.max() + pad), 220)
    potential_values = mass * gravity * coordinate_values
    return Trajectory.from_arrays(
        time=trajectory.time,
        states=trajectory.states,
        state_names=trajectory.state_names,
        metadata={
            "system": "uniform_gravity",
            "mass": mass,
            "gravity": gravity,
            "potentialPlots": [
                potential_plot_metadata(
                    name="gravity_potential",
                    coordinate="z",
                    coordinate_latex="z",
                    coordinate_values=coordinate_values,
                    potential_values=potential_values,
                    energy_series=trajectory.series["H"],
                )
            ],
        },
        series=trajectory.series,
    )


def write_uniform_gravity_trajectory(
    output: Path,
    *,
    viewer_output: Path | None = None,
) -> Trajectory:
    trajectory = generate_uniform_gravity_trajectory()
    return write_trajectory_outputs(trajectory, output, viewer_output)


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
