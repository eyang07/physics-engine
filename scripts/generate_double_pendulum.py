from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

import numpy as np

from engine.export import Trajectory
from engine.export.manifest import ParameterVariant
from scripts.example_specs import DOUBLE_PENDULUM
from scripts.generation import (
    generate_lagrangian_trajectory,
    write_parameter_variant_trajectories,
    write_trajectory_outputs,
)
from systems.double_pendulum import build_system


def double_pendulum_embedding(
    length1: float,
    length2: float,
    states: np.ndarray,
) -> np.ndarray:
    """Return ``x1, y1, x2, y2`` for sampled intrinsic states."""

    theta1 = states[:, 0]
    theta2 = states[:, 1]
    x1 = length1 * np.sin(theta1)
    y1 = -length1 * np.cos(theta1)
    x2 = x1 + length2 * np.sin(theta2)
    y2 = y1 - length2 * np.cos(theta2)
    return np.column_stack([x1, y1, x2, y2])


def double_pendulum_renderer_hints(length1: float, length2: float) -> dict[str, object]:
    radius = length1 + length2
    return {
        "bounds": {
            "x": [-radius, radius],
            "y": [-radius, radius],
        },
        "referenceGeometry": [
            {
                "kind": "pivot",
                "position": [0.0, 0.0],
            },
            {
                "kind": "doublePendulumLinks",
                "lengths": [length1, length2],
            },
        ],
    }


def generate_double_pendulum_trajectory(
    *,
    mass1: float = 1.0,
    mass2: float = 1.0,
    length1: float = 1.0,
    length2: float = 1.0,
    gravity: float = 9.81,
    theta1_0: float = 1.2,
    theta2_0: float = -0.2,
    theta1_dot0: float = 0.0,
    theta2_dot0: float = 0.25,
    t_span: tuple[float, float] = (0.0, 18.0),
    dt: float = 0.005,
) -> Trajectory:
    system = build_system(
        mass1=mass1,
        mass2=mass2,
        length1=length1,
        length2=length2,
        gravity=gravity,
    )
    physical_parameters = {
        "m1": mass1,
        "m2": mass2,
        "ell1": length1,
        "ell2": length2,
        "g": gravity,
    }
    trajectory = generate_lagrangian_trajectory(
        spec=DOUBLE_PENDULUM,
        system=system,
        initial_state=[theta1_0, theta2_0, theta1_dot0, theta2_dot0],
        t_span=t_span,
        dt=dt,
        state_names=[
            "theta1",
            "theta2",
            "theta1_dot",
            "theta2_dot",
            "x1",
            "y1",
            "x2",
            "y2",
        ],
        physical_parameters=physical_parameters,
        metadata={
            "system": "double_pendulum",
            "mass1": mass1,
            "mass2": mass2,
            "length1": length1,
            "length2": length2,
            "gravity": gravity,
            "rendererHints": double_pendulum_renderer_hints(length1, length2),
        },
        state_transform=lambda _time, states: np.column_stack(
            [
                states,
                double_pendulum_embedding(length1, length2, states),
            ]
        ),
    )
    return trajectory


def write_double_pendulum_trajectory(
    output: Path,
    *,
    viewer_output: Path | None = None,
    mass1: float = 1.0,
    mass2: float = 1.0,
    length1: float = 1.0,
    length2: float = 1.0,
    gravity: float = 9.81,
    theta1_0: float = 1.2,
    theta2_0: float = -0.2,
    theta1_dot0: float = 0.0,
    theta2_dot0: float = 0.25,
    t_end: float = 18.0,
    dt: float = 0.005,
) -> Trajectory:
    trajectory = generate_double_pendulum_trajectory(
        mass1=mass1,
        mass2=mass2,
        length1=length1,
        length2=length2,
        gravity=gravity,
        theta1_0=theta1_0,
        theta2_0=theta2_0,
        theta1_dot0=theta1_dot0,
        theta2_dot0=theta2_dot0,
        t_span=(0.0, t_end),
        dt=dt,
    )
    return write_trajectory_outputs(trajectory, output, viewer_output)


def _write_variant(
    variant: ParameterVariant,
    output: Path,
    viewer_output: Path | None,
) -> Trajectory:
    parameters = dict(variant.parameters)
    return write_double_pendulum_trajectory(
        output,
        viewer_output=viewer_output,
        mass1=parameters["m1"],
        mass2=parameters["m2"],
        length1=parameters["ell1"],
        length2=parameters["ell2"],
        gravity=parameters["g"],
        theta1_0=parameters["theta1_0"],
        theta2_0=parameters["theta2_0"],
        theta1_dot0=parameters["theta1_dot0"],
        theta2_dot0=parameters["theta2_dot0"],
    )


def write_double_pendulum_variant_trajectories(
    output_dir: Path,
    *,
    viewer_output_dir: Path | None = None,
) -> list[Trajectory]:
    return write_parameter_variant_trajectories(
        DOUBLE_PENDULUM,
        output_dir,
        write_variant=_write_variant,
        viewer_output_dir=viewer_output_dir,
        system_name="Double Pendulum",
    )


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate double-pendulum data.")
    parser.add_argument("--output", type=Path, default=Path("data/generated/double_pendulum.json"))
    parser.add_argument("--viewer-output", type=Path, default=Path("viewer/public/data/double_pendulum.json"))
    parser.add_argument("--mass1", type=float, default=1.0)
    parser.add_argument("--mass2", type=float, default=1.0)
    parser.add_argument("--length1", type=float, default=1.0)
    parser.add_argument("--length2", type=float, default=1.0)
    parser.add_argument("--gravity", type=float, default=9.81)
    parser.add_argument("--theta1-0", type=float, default=1.2)
    parser.add_argument("--theta2-0", type=float, default=-0.2)
    parser.add_argument("--theta1-dot0", type=float, default=0.0)
    parser.add_argument("--theta2-dot0", type=float, default=0.25)
    parser.add_argument("--t-end", type=float, default=18.0)
    parser.add_argument("--dt", type=float, default=0.005)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> None:
    args = parse_args(argv)
    trajectory = write_double_pendulum_trajectory(
        args.output,
        viewer_output=args.viewer_output,
        mass1=args.mass1,
        mass2=args.mass2,
        length1=args.length1,
        length2=args.length2,
        gravity=args.gravity,
        theta1_0=args.theta1_0,
        theta2_0=args.theta2_0,
        theta1_dot0=args.theta1_dot0,
        theta2_dot0=args.theta2_dot0,
        t_end=args.t_end,
        dt=args.dt,
    )
    print(f"Wrote {len(trajectory.time)} samples to {args.output}")
    if args.viewer_output is not None:
        print(f"Wrote viewer copy to {args.viewer_output}")


if __name__ == "__main__":
    main()
