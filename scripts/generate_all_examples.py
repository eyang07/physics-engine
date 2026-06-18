from __future__ import annotations

from pathlib import Path

from engine.export.manifest import write_manifest
from scripts.example_specs import LENSES, SPECS
from scripts.generate_bead_on_hoop import write_bead_on_hoop_trajectory
from scripts.generate_charged_particle import write_charged_particle_trajectory
from scripts.generate_double_pendulum import (
    write_double_pendulum_trajectory,
    write_double_pendulum_variant_trajectories,
)
from scripts.generate_henon_heiles import write_henon_heiles_trajectory
from scripts.generate_ideal_spring import (
    write_ideal_spring_trajectory,
    write_ideal_spring_variant_trajectories,
)
from scripts.generate_kepler_problem import write_kepler_trajectory
from scripts.generate_lorenz_attractor import write_lorenz_trajectory, write_lorenz_variant_trajectories
from scripts.generate_n_body_gravity import (
    write_n_body_trajectory,
    write_n_body_variant_trajectories,
)
from scripts.generate_pendulum import write_pendulum_trajectory
from scripts.generate_sphere_geodesic import write_sphere_geodesic_trajectory
from scripts.generate_uniform_gravity import write_uniform_gravity_trajectory
from scripts.generate_variable_speed_wavefront import write_variable_speed_wavefront


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
    write_ideal_spring_variant_trajectories(
        Path("data/generated"),
        viewer_output_dir=Path("viewer/public/data"),
    )
    write_kepler_trajectory(
        Path("data/generated/kepler_problem.json"),
        viewer_output=Path("viewer/public/data/kepler_problem.json"),
    )
    write_bead_on_hoop_trajectory(
        Path("data/generated/bead_on_hoop.json"),
        viewer_output=Path("viewer/public/data/bead_on_hoop.json"),
    )
    write_double_pendulum_trajectory(
        Path("data/generated/double_pendulum.json"),
        viewer_output=Path("viewer/public/data/double_pendulum.json"),
    )
    write_double_pendulum_variant_trajectories(
        Path("data/generated"),
        viewer_output_dir=Path("viewer/public/data"),
    )
    write_n_body_trajectory(
        Path("data/generated/n_body_gravity.json"),
        viewer_output=Path("viewer/public/data/n_body_gravity.json"),
    )
    write_n_body_variant_trajectories(
        Path("data/generated"),
        viewer_output_dir=Path("viewer/public/data"),
    )
    write_lorenz_trajectory(
        Path("data/generated/lorenz_attractor.json"),
        viewer_output=Path("viewer/public/data/lorenz_attractor.json"),
    )
    write_lorenz_variant_trajectories(
        Path("data/generated"),
        viewer_output_dir=Path("viewer/public/data"),
    )
    write_henon_heiles_trajectory(
        Path("data/generated/henon_heiles.json"),
        viewer_output=Path("viewer/public/data/henon_heiles.json"),
    )
    write_variable_speed_wavefront(
        Path("data/generated/variable_speed_wavefront.json"),
        viewer_output=Path("viewer/public/data/variable_speed_wavefront.json"),
    )
    write_manifest(
        SPECS,
        Path("data/generated/manifest.json"),
        Path("viewer/public/data/manifest.json"),
        lenses=LENSES,
    )
    print("Wrote all example trajectories and the manifest.")


if __name__ == "__main__":
    main()
