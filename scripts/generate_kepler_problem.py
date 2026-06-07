from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

import numpy as np

from engine.export import Trajectory
from scripts.example_specs import KEPLER
from scripts.generation import generate_lagrangian_trajectory, write_trajectory_outputs
from systems.kepler_problem import build_system


def generate_kepler_trajectory(
    *,
    mass: float = 1.0,
    gravitational_parameter: float = 1.0,
    initial_state: Sequence[float] = (1.0, 0.0, 0.0, 1.05),
    t_span: tuple[float, float] = (0.0, 24.0),
    dt: float = 0.01,
) -> Trajectory:
    system = build_system(mass=mass, gravitational_parameter=gravitational_parameter)
    return generate_lagrangian_trajectory(
        spec=KEPLER,
        system=system,
        initial_state=initial_state,
        t_span=t_span,
        dt=dt,
        state_names=["r", "phi", "r_dot", "phi_dot", "x", "y"],
        physical_parameters={"m": mass, "mu": gravitational_parameter},
        metadata={
            "system": "kepler_problem",
            "mass": mass,
            "gravitational_parameter": gravitational_parameter,
        },
        state_transform=lambda _time, intrinsic_states: np.column_stack(
            [
                intrinsic_states,
                intrinsic_states[:, 0] * np.cos(intrinsic_states[:, 1]),
                intrinsic_states[:, 0] * np.sin(intrinsic_states[:, 1]),
            ]
        ),
    )


def write_kepler_trajectory(
    output: Path,
    *,
    viewer_output: Path | None = None,
) -> Trajectory:
    trajectory = generate_kepler_trajectory()
    return write_trajectory_outputs(trajectory, output, viewer_output)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate Kepler problem orbit data.")
    parser.add_argument("--output", type=Path, default=Path("data/generated/kepler_problem.json"))
    parser.add_argument("--viewer-output", type=Path, default=Path("viewer/public/data/kepler_problem.json"))
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> None:
    args = parse_args(argv)
    write_kepler_trajectory(args.output, viewer_output=args.viewer_output)
    print(f"Wrote trajectory to {args.output}")


if __name__ == "__main__":
    main()
