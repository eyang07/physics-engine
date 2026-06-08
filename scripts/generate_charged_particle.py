from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

import numpy as np

from engine.export import Trajectory
from scripts.example_specs import CHARGED_PARTICLE
from scripts.generation import generate_lagrangian_trajectory, write_trajectory_outputs
from systems.charged_particle import build_uniform_magnetic_field_system


def charged_particle_renderer_hints(states: np.ndarray) -> dict[str, object]:
    """Return renderer metadata for the magnetic-field scene."""

    x = states[:, 0]
    y = states[:, 1]
    z = states[:, 2] * 0.62
    x_extent = float(max(np.max(np.abs(x)), 1.2))
    y_extent = float(max(np.max(np.abs(y)), 1.2))
    z_min = float(min(z.min(), -1.05))
    z_max = float(max(z.max(), 1.05))

    return {
        "bounds": {
            "x": [float(x.min()), float(x.max())],
            "y": [z_min, z_max],
            "z": [float(y.min()), float(y.max())],
        },
        "camera": {
            "position": [3.0, 2.0, 3.4],
            "target": [0.0, 0.0, 0.0],
        },
        "referenceGeometry": [
            {
                "kind": "magneticField",
                "radii": [0.86],
                "yValues": [-0.7, 0.05, 0.8],
                "start": [0.0, -1.05, 0.0],
                "end": [0.0, 1.05, 0.0],
            }
        ],
        "flow": {
            "kind": "magneticRotation",
            "bounds": {
                "x": [-x_extent, x_extent],
                "z": [-y_extent, y_extent],
            },
        },
    }


def generate_charged_particle_trajectory(
    *,
    mass: float = 1.0,
    charge: float = -1.0,
    magnetic_field_z: float = 1.0,
    initial_state: Sequence[float] = (0.85, 0.0, -1.6, 0.0, 0.85, 0.22),
    t_span: tuple[float, float] = (0.0, 18.0),
    dt: float = 0.01,
) -> Trajectory:
    system = build_uniform_magnetic_field_system(
        mass=mass,
        charge=charge,
        magnetic_field_z=magnetic_field_z,
    )
    trajectory = generate_lagrangian_trajectory(
        spec=CHARGED_PARTICLE,
        system=system,
        initial_state=initial_state,
        t_span=t_span,
        dt=dt,
        state_names=["x", "y", "z", "x_dot", "y_dot", "z_dot"],
        physical_parameters={"m": mass, "q": charge, "B_z": magnetic_field_z},
        metadata={
            "system": "charged_particle_uniform_magnetic_field",
            "mass": mass,
            "charge": charge,
            "magnetic_field": [0.0, 0.0, magnetic_field_z],
        },
    )
    metadata = dict(trajectory.metadata or {})
    metadata["rendererHints"] = charged_particle_renderer_hints(trajectory.states)
    return Trajectory.from_arrays(
        time=trajectory.time,
        states=trajectory.states,
        state_names=trajectory.state_names,
        metadata=metadata,
        series=trajectory.series,
    )


def write_charged_particle_trajectory(
    output: Path,
    *,
    viewer_output: Path | None = None,
    t_end: float = 18.0,
    dt: float = 0.01,
) -> Trajectory:
    trajectory = generate_charged_particle_trajectory(t_span=(0.0, t_end), dt=dt)
    return write_trajectory_outputs(trajectory, output, viewer_output)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate a charged-particle trajectory.")
    parser.add_argument("--output", type=Path, default=Path("data/generated/charged_particle.json"))
    parser.add_argument(
        "--viewer-output",
        type=Path,
        default=Path("viewer/public/data/charged_particle.json"),
    )
    parser.add_argument("--t-end", type=float, default=18.0)
    parser.add_argument("--dt", type=float, default=0.01)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> None:
    args = parse_args(argv)
    trajectory = write_charged_particle_trajectory(
        args.output,
        viewer_output=args.viewer_output,
        t_end=args.t_end,
        dt=args.dt,
    )
    print(f"Wrote {len(trajectory.time)} samples to {args.output}")
    if args.viewer_output is not None:
        print(f"Wrote viewer copy to {args.viewer_output}")


if __name__ == "__main__":
    main()
