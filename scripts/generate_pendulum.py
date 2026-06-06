from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

import numpy as np

from engine.export import Trajectory
from engine.numerics import integrate_fixed_step
from scripts.example_specs import PENDULUM
from systems.pendulum import build_system


def generate_pendulum_trajectory(
    *,
    mass: float = 1.0,
    length: float = 1.0,
    gravity: float = 9.81,
    theta0: float = 0.85,
    theta_dot0: float = 0.0,
    t_span: tuple[float, float] = (0.0, 16.0),
    dt: float = 0.01,
) -> Trajectory:
    system = build_system(mass=mass, length=length, gravity=gravity)
    rhs = system.numerical_rhs()
    time, states = integrate_fixed_step(
        rhs,
        initial_state=[theta0, theta_dot0],
        t_span=t_span,
        dt=dt,
    )
    series = PENDULUM.series({"m": mass, "ell": length, "g": gravity}, states)
    theta_values = np.linspace(-np.pi, np.pi, 320)
    potential_values = mass * gravity * length * (1 - np.cos(theta_values))
    return Trajectory.from_arrays(
        time=time,
        states=states,
        state_names=["theta", "theta_dot"],
        metadata={
            "potentialPlots": [
                {
                    "name": "pendulum_potential",
                    "coordinate": "theta",
                    "coordinateLatex": r"\theta",
                    "potentialLatex": "V",
                    "coordinateValues": theta_values.tolist(),
                    "potentialValues": potential_values.tolist(),
                    "energy": float(np.mean(series["H"])),
                }
            ]
        },
        series=series,
    )


def write_pendulum_trajectory(
    output: Path,
    *,
    viewer_output: Path | None = None,
    mass: float = 1.0,
    length: float = 1.0,
    gravity: float = 9.81,
    theta0: float = 0.85,
    theta_dot0: float = 0.0,
    t_end: float = 16.0,
    dt: float = 0.01,
) -> Trajectory:
    trajectory = generate_pendulum_trajectory(
        mass=mass,
        length=length,
        gravity=gravity,
        theta0=theta0,
        theta_dot0=theta_dot0,
        t_span=(0.0, t_end),
        dt=dt,
    )
    trajectory.write_json(output)
    if viewer_output is not None:
        trajectory.write_json(viewer_output)
    return trajectory


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate a simple pendulum trajectory.")
    parser.add_argument("--output", type=Path, default=Path("data/generated/pendulum.json"))
    parser.add_argument(
        "--viewer-output",
        type=Path,
        default=Path("viewer/public/data/pendulum.json"),
        help="Optional copy served by the TypeScript viewer.",
    )
    parser.add_argument("--mass", type=float, default=1.0)
    parser.add_argument("--length", type=float, default=1.0)
    parser.add_argument("--gravity", type=float, default=9.81)
    parser.add_argument("--theta0", type=float, default=0.85)
    parser.add_argument("--theta-dot0", type=float, default=0.0)
    parser.add_argument("--t-end", type=float, default=16.0)
    parser.add_argument("--dt", type=float, default=0.01)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> None:
    args = parse_args(argv)
    trajectory = write_pendulum_trajectory(
        args.output,
        viewer_output=args.viewer_output,
        mass=args.mass,
        length=args.length,
        gravity=args.gravity,
        theta0=args.theta0,
        theta_dot0=args.theta_dot0,
        t_end=args.t_end,
        dt=args.dt,
    )
    print(f"Wrote {len(trajectory.time)} samples to {args.output}")
    if args.viewer_output is not None:
        print(f"Wrote viewer copy to {args.viewer_output}")


if __name__ == "__main__":
    main()
