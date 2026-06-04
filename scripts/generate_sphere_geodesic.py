from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

import numpy as np

from engine.export import Trajectory
from engine.numerics import integrate_fixed_step
from scripts.example_specs import SPHERE_GEODESIC
from systems.sphere_geodesic import build_system


def embed_sphere(radius: float, theta: np.ndarray, phi: np.ndarray) -> np.ndarray:
    return np.column_stack(
        [
            radius * np.sin(theta) * np.cos(phi),
            radius * np.sin(theta) * np.sin(phi),
            radius * np.cos(theta),
        ]
    )


def generate_sphere_geodesic_trajectory(
    *,
    mass: float = 1.0,
    radius: float = 1.0,
    theta0: float = 1.12,
    phi0: float = 0.0,
    theta_dot0: float = 0.42,
    phi_dot0: float = 1.05,
    t_span: tuple[float, float] = (0.0, 13.5),
    dt: float = 0.01,
) -> Trajectory:
    system = build_system(mass=mass, radius=radius)
    rhs = system.numerical_rhs()
    time, intrinsic_states = integrate_fixed_step(
        rhs,
        initial_state=[theta0, phi0, theta_dot0, phi_dot0],
        t_span=t_span,
        dt=dt,
    )
    embedded = embed_sphere(radius, intrinsic_states[:, 0], intrinsic_states[:, 1])
    states = np.column_stack([intrinsic_states, embedded])
    return Trajectory.from_arrays(
        time=time,
        states=states,
        state_names=["theta", "phi", "theta_dot", "phi_dot", "x", "y", "z"],
        metadata={
            "system": "sphere_geodesic",
            "radius": radius,
            "mass": mass,
        },
        series=SPHERE_GEODESIC.series({"m": mass, "R": radius}, states),
    )


def write_sphere_geodesic_trajectory(
    output: Path,
    *,
    viewer_output: Path | None = None,
    radius: float = 1.0,
    t_end: float = 13.5,
    dt: float = 0.01,
) -> Trajectory:
    trajectory = generate_sphere_geodesic_trajectory(
        radius=radius,
        t_span=(0.0, t_end),
        dt=dt,
    )
    trajectory.write_json(output)
    if viewer_output is not None:
        trajectory.write_json(viewer_output)
    return trajectory


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate a sphere geodesic trajectory.")
    parser.add_argument("--output", type=Path, default=Path("data/generated/sphere_geodesic.json"))
    parser.add_argument(
        "--viewer-output",
        type=Path,
        default=Path("viewer/public/data/sphere_geodesic.json"),
    )
    parser.add_argument("--radius", type=float, default=1.0)
    parser.add_argument("--t-end", type=float, default=13.5)
    parser.add_argument("--dt", type=float, default=0.01)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> None:
    args = parse_args(argv)
    trajectory = write_sphere_geodesic_trajectory(
        args.output,
        viewer_output=args.viewer_output,
        radius=args.radius,
        t_end=args.t_end,
        dt=args.dt,
    )
    print(f"Wrote {len(trajectory.time)} samples to {args.output}")
    if args.viewer_output is not None:
        print(f"Wrote viewer copy to {args.viewer_output}")


if __name__ == "__main__":
    main()

