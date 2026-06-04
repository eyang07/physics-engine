from __future__ import annotations

from pathlib import Path

from engine.export.manifest import write_manifest
from scripts.example_specs import SPECS
from scripts.generate_charged_particle import write_charged_particle_trajectory
from scripts.generate_ideal_spring import write_ideal_spring_trajectory
from scripts.generate_kepler_problem import write_kepler_trajectory
from scripts.generate_pendulum import write_pendulum_trajectory
from scripts.generate_sphere_geodesic import write_sphere_geodesic_trajectory
from scripts.generate_uniform_gravity import write_uniform_gravity_trajectory


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
    write_uniform_gravity_trajectory(
        Path("data/generated/uniform_gravity.json"),
        viewer_output=Path("viewer/public/data/uniform_gravity.json"),
    )
    write_ideal_spring_trajectory(
        Path("data/generated/ideal_spring.json"),
        viewer_output=Path("viewer/public/data/ideal_spring.json"),
    )
    write_kepler_trajectory(
        Path("data/generated/kepler_problem.json"),
        viewer_output=Path("viewer/public/data/kepler_problem.json"),
    )
    write_manifest(
        SPECS,
        Path("data/generated/manifest.json"),
        Path("viewer/public/data/manifest.json"),
    )
    print("Wrote all example trajectories and the manifest.")


if __name__ == "__main__":
    main()
