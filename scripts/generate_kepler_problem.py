from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

import numpy as np

from engine.export import Trajectory
from engine.numerics import integrate_fixed_step
from scripts.example_specs import KEPLER
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
    time, intrinsic_states = integrate_fixed_step(system.numerical_rhs(), initial_state, t_span, dt)
    r = intrinsic_states[:, 0]
    phi = intrinsic_states[:, 1]
    embedded = np.column_stack([r * np.cos(phi), r * np.sin(phi)])
    states = np.column_stack([intrinsic_states, embedded])
    return Trajectory.from_arrays(
        time=time,
        states=states,
        state_names=["r", "phi", "r_dot", "phi_dot", "x", "y"],
        metadata={
            "system": "kepler_problem",
            "mass": mass,
            "gravitational_parameter": gravitational_parameter,
        },
        series=KEPLER.series(
            {"m": mass, "mu": gravitational_parameter}, states
        ),
    )


def write_kepler_trajectory(
    output: Path,
    *,
    viewer_output: Path | None = None,
) -> Trajectory:
    trajectory = generate_kepler_trajectory()
    trajectory.write_json(output)
    if viewer_output is not None:
        trajectory.write_json(viewer_output)
    return trajectory


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

