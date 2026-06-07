from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

import numpy as np

from engine.export import Trajectory
from scripts.example_specs import HENON_HEILES
from scripts.generation import generate_lagrangian_trajectory, write_trajectory_outputs
from systems.henon_heiles import build_system


def _potential(x: np.ndarray, y: np.ndarray, stiffness: float, coupling: float) -> np.ndarray:
    return 0.5 * stiffness * (x**2 + y**2) + coupling * (x**2 * y - y**3 / 3.0)


def generate_henon_heiles_trajectory(
    *,
    mass: float = 1.0,
    stiffness: float = 1.0,
    coupling: float = 1.0,
    initial_state: Sequence[float] = (0.0, 0.1, 0.48, 0.0),
    t_span: tuple[float, float] = (0.0, 70.0),
    dt: float = 0.01,
) -> Trajectory:
    system = build_system(mass=mass, stiffness=stiffness, coupling=coupling)
    trajectory = generate_lagrangian_trajectory(
        spec=HENON_HEILES,
        system=system,
        initial_state=initial_state,
        t_span=t_span,
        dt=dt,
        state_names=["x", "y", "x_dot", "y_dot"],
        physical_parameters={"m": mass, "k": stiffness, "lambda": coupling},
    )
    assert trajectory.series is not None

    x_values = trajectory.states[:, 0]
    y_values = trajectory.states[:, 1]
    span = max(
        abs(float(x_values.min())),
        abs(float(x_values.max())),
        abs(float(y_values.min())),
        abs(float(y_values.max())),
        0.75,
    ) * 1.35
    grid_x = np.linspace(-span, span, 120)
    grid_y = np.linspace(-span, span, 120)
    xx, yy = np.meshgrid(grid_x, grid_y)
    potential = _potential(xx, yy, stiffness, coupling)

    return Trajectory.from_arrays(
        time=trajectory.time,
        states=trajectory.states,
        state_names=trajectory.state_names,
        metadata={
            "system": "henon_heiles",
            "mass": mass,
            "stiffness": stiffness,
            "coupling": coupling,
            "potentialSurface": {
                "xValues": grid_x.tolist(),
                "yValues": grid_y.tolist(),
                "values": potential.tolist(),
                "energy": float(np.mean(np.asarray(trajectory.series["H"], dtype=float))),
            },
        },
        series=trajectory.series,
    )


def write_henon_heiles_trajectory(
    output: Path,
    *,
    viewer_output: Path | None = None,
) -> Trajectory:
    trajectory = generate_henon_heiles_trajectory()
    return write_trajectory_outputs(trajectory, output, viewer_output)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate Hénon-Heiles trajectory data.")
    parser.add_argument("--output", type=Path, default=Path("data/generated/henon_heiles.json"))
    parser.add_argument("--viewer-output", type=Path, default=Path("viewer/public/data/henon_heiles.json"))
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> None:
    args = parse_args(argv)
    write_henon_heiles_trajectory(args.output, viewer_output=args.viewer_output)
    print(f"Wrote trajectory to {args.output}")


if __name__ == "__main__":
    main()
