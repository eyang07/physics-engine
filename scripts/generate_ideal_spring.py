from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

import numpy as np

from engine.export import Trajectory
from engine.numerics import integrate_fixed_step
from scripts.example_specs import IDEAL_SPRING
from systems.ideal_spring import build_system


def generate_ideal_spring_trajectory(
    *,
    mass: float = 1.0,
    spring_constant: float = 1.0,
    initial_state: Sequence[float] = (1.0, 0.0),
    t_span: tuple[float, float] = (0.0, 18.0),
    dt: float = 0.01,
) -> Trajectory:
    system = build_system(mass=mass, spring_constant=spring_constant)
    time, states = integrate_fixed_step(system.numerical_rhs(), initial_state, t_span, dt)
    series = IDEAL_SPRING.series({"m": mass, "k": spring_constant}, states)
    x_values = states[:, 0]
    span = max(abs(float(x_values.min())), abs(float(x_values.max())), 1.0) * 1.18
    coordinate_values = np.linspace(-span, span, 260)
    potential_values = 0.5 * spring_constant * coordinate_values**2
    return Trajectory.from_arrays(
        time=time,
        states=states,
        state_names=["x", "x_dot"],
        metadata={
            "system": "ideal_spring",
            "mass": mass,
            "spring_constant": spring_constant,
            "potentialPlots": [
                {
                    "name": "spring_potential",
                    "coordinate": "x",
                    "coordinateLatex": "x",
                    "potentialLatex": "V",
                    "coordinateValues": coordinate_values.tolist(),
                    "potentialValues": potential_values.tolist(),
                    "energy": float(np.mean(series["H"])),
                }
            ],
        },
        series=series,
    )


def write_ideal_spring_trajectory(
    output: Path,
    *,
    viewer_output: Path | None = None,
) -> Trajectory:
    trajectory = generate_ideal_spring_trajectory()
    trajectory.write_json(output)
    if viewer_output is not None:
        trajectory.write_json(viewer_output)
    return trajectory


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate ideal spring oscillator data.")
    parser.add_argument("--output", type=Path, default=Path("data/generated/ideal_spring.json"))
    parser.add_argument("--viewer-output", type=Path, default=Path("viewer/public/data/ideal_spring.json"))
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> None:
    args = parse_args(argv)
    write_ideal_spring_trajectory(args.output, viewer_output=args.viewer_output)
    print(f"Wrote trajectory to {args.output}")


if __name__ == "__main__":
    main()
