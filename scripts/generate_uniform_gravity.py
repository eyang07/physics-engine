from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

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
    return Trajectory.from_arrays(
        time=time,
        states=states,
        state_names=["x", "z", "x_dot", "z_dot"],
        metadata={"system": "uniform_gravity", "mass": mass, "gravity": gravity},
        series=UNIFORM_GRAVITY.series({"m": mass, "g": gravity}, states),
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

