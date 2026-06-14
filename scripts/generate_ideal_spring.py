from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

import numpy as np

from engine.export import Trajectory
from engine.export.manifest import ParameterVariant
from scripts.example_specs import IDEAL_SPRING
from scripts.generation import (
    generate_lagrangian_trajectory,
    potential_plot_metadata,
    write_parameter_variant_trajectories,
    write_trajectory_outputs,
)
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
    trajectory = generate_lagrangian_trajectory(
        spec=IDEAL_SPRING,
        system=system,
        initial_state=initial_state,
        t_span=t_span,
        dt=dt,
        state_names=["x", "x_dot"],
        physical_parameters={"m": mass, "k": spring_constant},
    )
    assert trajectory.series is not None
    x_values = trajectory.states[:, 0]
    span = max(abs(float(x_values.min())), abs(float(x_values.max())), 1.0) * 1.18
    coordinate_values = np.linspace(-span, span, 260)
    potential_values = 0.5 * spring_constant * coordinate_values**2
    metadata = dict(trajectory.metadata or {})
    metadata.update(
        {
            "system": "ideal_spring",
            "mass": mass,
            "spring_constant": spring_constant,
            "potentialPlots": [
                potential_plot_metadata(
                    name="spring_potential",
                    coordinate="x",
                    coordinate_latex="x",
                    coordinate_values=coordinate_values,
                    potential_values=potential_values,
                    energy_series=trajectory.series["H"],
                )
            ],
        }
    )
    return Trajectory.from_arrays(
        time=trajectory.time,
        states=trajectory.states,
        state_names=trajectory.state_names,
        metadata=metadata,
        series=trajectory.series,
    )


def write_ideal_spring_trajectory(
    output: Path,
    *,
    viewer_output: Path | None = None,
    mass: float = 1.0,
    spring_constant: float = 1.0,
    initial_state: Sequence[float] = (1.0, 0.0),
) -> Trajectory:
    trajectory = generate_ideal_spring_trajectory(
        mass=mass,
        spring_constant=spring_constant,
        initial_state=initial_state,
    )
    return write_trajectory_outputs(trajectory, output, viewer_output)


def _write_ideal_spring_variant(
    variant: ParameterVariant,
    output: Path,
    viewer_output: Path | None,
) -> Trajectory:
    parameters = variant.parameters
    return write_ideal_spring_trajectory(
        output,
        viewer_output=viewer_output,
        mass=parameters["m"],
        spring_constant=parameters["k"],
        initial_state=(parameters["x0"], parameters["x_dot0"]),
    )


def write_ideal_spring_variant_trajectories(
    output_dir: Path,
    *,
    viewer_output_dir: Path | None = None,
) -> list[Trajectory]:
    return write_parameter_variant_trajectories(
        IDEAL_SPRING,
        output_dir,
        write_variant=_write_ideal_spring_variant,
        viewer_output_dir=viewer_output_dir,
        system_name="Ideal spring",
    )


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
