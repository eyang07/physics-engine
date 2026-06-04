from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

from engine.export import Trajectory
from engine.numerics import integrate_fixed_step
from systems.charged_particle import build_uniform_magnetic_field_system


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
    rhs = system.numerical_rhs()
    time, states = integrate_fixed_step(
        rhs,
        initial_state=initial_state,
        t_span=t_span,
        dt=dt,
    )
    return Trajectory.from_arrays(
        time=time,
        states=states,
        state_names=["x", "y", "z", "x_dot", "y_dot", "z_dot"],
        metadata={
            "system": "charged_particle_uniform_magnetic_field",
            "mass": mass,
            "charge": charge,
            "magnetic_field": [0.0, 0.0, magnetic_field_z],
        },
    )


def write_charged_particle_trajectory(
    output: Path,
    *,
    viewer_output: Path | None = None,
    t_end: float = 18.0,
    dt: float = 0.01,
) -> Trajectory:
    trajectory = generate_charged_particle_trajectory(t_span=(0.0, t_end), dt=dt)
    trajectory.write_json(output)
    if viewer_output is not None:
        trajectory.write_json(viewer_output)
    return trajectory


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

