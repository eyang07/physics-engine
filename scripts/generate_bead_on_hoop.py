from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

import numpy as np

from engine.export import Trajectory
from scripts.example_specs import BEAD_ON_HOOP
from scripts.generation import (
    generate_lagrangian_trajectory,
    potential_plot_metadata,
    write_trajectory_outputs,
)
from systems.bead_on_hoop import build_system


def embed_rotating_hoop(
    radius: float,
    angular_speed: float,
    time: np.ndarray,
    theta: np.ndarray,
) -> np.ndarray:
    phase = angular_speed * time
    radial = radius * np.sin(theta)
    return np.column_stack(
        [
            radial * np.cos(phase),
            radial * np.sin(phase),
            -radius * np.cos(theta),
        ]
    )


def bead_renderer_hints(radius: float) -> dict[str, object]:
    """Return scene metadata for the rotating-hoop renderer."""

    return {
        "bounds": {
            "x": [-radius, radius],
            "y": [-radius, radius],
            "z": [-radius, radius],
        },
        "camera": {
            "position": [2.35 * radius, 1.35 * radius, 2.65 * radius],
            "target": [0.0, 0.0, 0.0],
        },
        "referenceGeometry": [
            {
                "kind": "constraintHoop",
                "radius": radius,
                "axis": [0.0, 1.0, 0.0],
                "echoAngles": [
                    float(np.pi / 5),
                    float(2 * np.pi / 5),
                    float(3 * np.pi / 5),
                    float(4 * np.pi / 5),
                ],
            },
            {
                "kind": "rotationAxis",
                "start": [0.0, -1.18 * radius, 0.0],
                "end": [0.0, 1.18 * radius, 0.0],
            },
        ],
    }


def generate_bead_on_hoop_trajectory(
    *,
    mass: float = 1.0,
    radius: float = 1.0,
    gravity: float = 9.81,
    angular_speed: float = 4.0,
    theta0: float = 0.82,
    theta_dot0: float = 0.12,
    t_span: tuple[float, float] = (0.0, 18.0),
    dt: float = 0.01,
) -> Trajectory:
    system = build_system(
        mass=mass,
        radius=radius,
        gravity=gravity,
        angular_speed=angular_speed,
    )
    physical_parameters = {
        "m": mass,
        "R": radius,
        "g": gravity,
        "Omega": angular_speed,
    }
    theta_values = np.linspace(-np.pi, np.pi, 360)
    potential_values = (
        -mass * gravity * radius * np.cos(theta_values)
        - 0.5 * mass * radius**2 * angular_speed**2 * np.sin(theta_values) ** 2
    )
    trajectory = generate_lagrangian_trajectory(
        spec=BEAD_ON_HOOP,
        system=system,
        initial_state=[theta0, theta_dot0],
        t_span=t_span,
        dt=dt,
        state_names=["theta", "theta_dot", "x", "y", "z"],
        physical_parameters=physical_parameters,
        metadata={
            "system": "bead_on_hoop",
            "mass": mass,
            "radius": radius,
            "gravity": gravity,
            "angular_speed": angular_speed,
            "rendererHints": bead_renderer_hints(radius),
        },
        state_transform=lambda time, states: np.column_stack(
            [
                states,
                embed_rotating_hoop(radius, angular_speed, time, states[:, 0]),
            ]
        ),
    )
    assert trajectory.series is not None
    metadata = dict(trajectory.metadata or {})
    metadata["potentialPlots"] = [
        potential_plot_metadata(
            name="rotating_hoop_potential",
            coordinate="theta",
            coordinate_latex=r"\theta",
            coordinate_values=theta_values,
            potential_values=potential_values,
            energy_series=trajectory.series["H"],
        )
    ]
    return Trajectory.from_arrays(
        time=trajectory.time,
        states=trajectory.states,
        state_names=trajectory.state_names,
        metadata=metadata,
        series=trajectory.series,
    )


def write_bead_on_hoop_trajectory(
    output: Path,
    *,
    viewer_output: Path | None = None,
) -> Trajectory:
    trajectory = generate_bead_on_hoop_trajectory()
    return write_trajectory_outputs(trajectory, output, viewer_output)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate bead-on-rotating-hoop data.")
    parser.add_argument("--output", type=Path, default=Path("data/generated/bead_on_hoop.json"))
    parser.add_argument("--viewer-output", type=Path, default=Path("viewer/public/data/bead_on_hoop.json"))
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> None:
    args = parse_args(argv)
    write_bead_on_hoop_trajectory(args.output, viewer_output=args.viewer_output)
    print(f"Wrote trajectory to {args.output}")


if __name__ == "__main__":
    main()
