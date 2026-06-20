from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

import numpy as np

from engine.export import Trajectory, field_lines, scalar_field_grid, vector_field_grid
from engine.fields import integrate_field_lines, seeds_on_segment
from systems.electromagnetic_field import build_system


DEFAULT_PARAMETERS = {
    "q": 1.0,
    "d": 1.4,
    "epsilon0": 1.0,
    "m_dipole": 1.0,
    "mu0": 1.0,
    "I": 1.0,
    "a": 0.7,
}


def _grid_axes() -> list[np.ndarray]:
    return [
        np.linspace(-2.4, 2.4, 48),
        np.linspace(-1.8, 1.8, 44),
    ]


def _electric_line_seeds(*, separation: float) -> np.ndarray:
    positive_charge = np.array([-separation / 2.0, 0.0])
    angles = np.linspace(-0.72, 0.72, 7)
    radius = 0.18
    return np.array(
        [
            positive_charge + radius * np.array([np.cos(angle), np.sin(angle)])
            for angle in angles
        ],
        dtype=float,
    )


def _field_metadata() -> dict[str, object]:
    system = build_system()
    axes = _grid_axes()
    parameters = dict(DEFAULT_PARAMETERS)
    separation = parameters["d"]
    charge_positions = [
        [-separation / 2.0, 0.0],
        [separation / 2.0, 0.0],
    ]
    bounds = [(-2.4, 2.4), (-1.8, 1.8)]

    electric_seeds = _electric_line_seeds(separation=separation)
    electric_lines = integrate_field_lines(
        system.electric_field,
        electric_seeds,
        bounds=bounds,
        arc_step=0.02,
        max_steps=600,
        both_directions=False,
        parameter_values=parameters,
        singularities=charge_positions,
        stop_radius=0.08,
    )

    magnetic_seeds = seeds_on_segment([-1.15, 0.42], [1.15, 0.42], 9)
    magnetic_lines = integrate_field_lines(
        system.magnetic_field,
        magnetic_seeds,
        bounds=bounds,
        arc_step=0.02,
        max_steps=750,
        both_directions=True,
        parameter_values=parameters,
        singularities=[[0.0, 0.0]],
        stop_radius=0.08,
    )

    return {
        "electricPotential": scalar_field_grid(
            system.electric_potential,
            axes,
            name="electricPotential",
            parameter_values=parameters,
        ),
        "electricField": vector_field_grid(
            system.electric_field,
            axes,
            name="electricField",
            parameter_values=parameters,
        ),
        "electricFieldLines": field_lines(
            electric_lines,
            name="electricFieldLines",
            dimension=2,
            seeds=electric_seeds,
        ),
        "magneticField": vector_field_grid(
            system.magnetic_field,
            axes,
            name="magneticField",
            parameter_values=parameters,
        ),
        "magneticFieldLines": field_lines(
            magnetic_lines,
            name="magneticFieldLines",
            dimension=2,
            seeds=magnetic_seeds,
        ),
    }


def generate_electromagnetic_field() -> Trajectory:
    metadata = {
        "system": "electromagnetic_field",
        "kind": "static-field",
        "parameters": dict(DEFAULT_PARAMETERS),
        "fields": _field_metadata(),
    }
    return Trajectory.from_arrays(
        time=[0.0],
        states=[[]],
        state_names=[],
        metadata=metadata,
    )


def write_electromagnetic_field(
    output: Path,
    *,
    viewer_output: Path | None = None,
) -> Trajectory:
    trajectory = generate_electromagnetic_field()
    trajectory.write_json(output)
    if viewer_output is not None:
        trajectory.write_json(viewer_output)
    return trajectory


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate static electromagnetic field data.")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/generated/electromagnetic_field.json"),
    )
    parser.add_argument(
        "--viewer-output",
        type=Path,
        default=Path("viewer/public/data/electromagnetic_field.json"),
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> None:
    args = parse_args(argv)
    write_electromagnetic_field(args.output, viewer_output=args.viewer_output)
    print(f"Wrote field data to {args.output}")


if __name__ == "__main__":
    main()
