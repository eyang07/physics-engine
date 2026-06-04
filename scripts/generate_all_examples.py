from __future__ import annotations

from pathlib import Path

from scripts.generate_charged_particle import write_charged_particle_trajectory
from scripts.generate_pendulum import write_pendulum_trajectory
from scripts.generate_sphere_geodesic import write_sphere_geodesic_trajectory


def main() -> None:
    write_pendulum_trajectory(
        Path("data/generated/pendulum.json"),
        viewer_output=Path("viewer/public/data/pendulum.json"),
    )
    write_sphere_geodesic_trajectory(
        Path("data/generated/sphere_geodesic.json"),
        viewer_output=Path("viewer/public/data/sphere_geodesic.json"),
    )
    write_charged_particle_trajectory(
        Path("data/generated/charged_particle.json"),
        viewer_output=Path("viewer/public/data/charged_particle.json"),
    )
    print("Wrote all example trajectories.")


if __name__ == "__main__":
    main()

