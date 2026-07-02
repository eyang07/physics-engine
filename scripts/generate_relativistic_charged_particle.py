from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

import sympy as sp

from engine.export import Trajectory
from engine.numerics import integrate_fixed_step
from scripts.generation import invariant_residual_records, write_trajectory_outputs
from systems.relativistic_charged_particle import (
    coordinate_time_series,
    em_invariant_series,
    four_velocity_norm_series,
    initial_state,
    mass_shell_series,
    spacetime_renderer_hints,
    worldline_payload,
)
from systems.relativistic_charged_particle import build_system


def generate_relativistic_charged_particle(
    *,
    mass: float = 1.0,
    charge: float = 1.0,
    electric: Sequence[float] = (0.08, -0.03, 0.0),
    magnetic: Sequence[float] = (0.0, 0.0, 0.9),
    velocity: Sequence[float] = (0.08, 0.32, 0.16),
    position: Sequence[float] = (0.0, 0.35, -0.2, -0.9),
    tau_span: tuple[float, float] = (0.0, 12.0),
    dt: float = 0.005,
) -> Trajectory:
    """Generate the BE-130 general relativistic charged-particle export."""

    if mass <= 0.0:
        raise ValueError("mass must be positive")
    electric_components = tuple(float(component) for component in electric)
    magnetic_components = tuple(float(component) for component in magnetic)
    if len(electric_components) != 3 or len(magnetic_components) != 3:
        raise ValueError("electric and magnetic fields must have three components")

    system = build_system()
    substitutions = {
        sp.Symbol("B_x", real=True): magnetic_components[0],
        sp.Symbol("B_y", real=True): magnetic_components[1],
        sp.Symbol("B_z", real=True): magnetic_components[2],
        sp.Symbol("E_x", real=True): electric_components[0],
        sp.Symbol("E_y", real=True): electric_components[1],
        sp.Symbol("E_z", real=True): electric_components[2],
        sp.Symbol("m", positive=True): mass,
        sp.Symbol("q", real=True): charge,
    }
    time, states = integrate_fixed_step(
        system.numerical_rhs(substitutions),
        initial_state(position=position, velocity=velocity, mass=mass),
        tau_span,
        dt,
    )

    mass_shell = mass_shell_series(states, mass=mass)
    four_velocity_norm = four_velocity_norm_series(states, mass=mass)
    em_invariants = em_invariant_series(
        len(time),
        electric=electric_components,
        magnetic=magnetic_components,
    )
    series = {
        "mass_shell": mass_shell,
        "four_velocity_norm": four_velocity_norm,
        "coordinate_time": coordinate_time_series(states),
        **em_invariants,
    }
    metadata = {
        "system": "relativistic_charged_particle",
        "kind": "covariant-em",
        "parameters": {
            "m": float(mass),
            "q": float(charge),
        },
        "coordinateConvention": {
            "signature": "(-,+,+,+)",
            "timeCoordinate": "x0 = c t",
            "parameter": "proper time tau",
            "units": "c=1",
        },
        "fields": {
            "electric": {
                "kind": "uniform-electric-field",
                "components": list(electric_components),
            },
            "magnetic": {
                "kind": "uniform-magnetic-field",
                "components": list(magnetic_components),
            },
        },
        "worldline": worldline_payload(time, states, mass=mass),
        "rendererHints": spacetime_renderer_hints(states),
        "invariantResiduals": invariant_residual_records(
            {
                "mass_shell": mass_shell,
                "four_velocity_norm": four_velocity_norm,
                "faraday_scalar": em_invariants["faraday_scalar"],
                "electric_magnetic": em_invariants["electric_magnetic"],
            }
        ),
    }
    return Trajectory.from_arrays(
        time=time,
        states=states,
        state_names=[symbol.name for symbol in system.state],
        metadata=metadata,
        series=series,
    )


def write_relativistic_charged_particle_trajectory(
    output: Path,
    *,
    viewer_output: Path | None = None,
) -> Trajectory:
    trajectory = generate_relativistic_charged_particle()
    return write_trajectory_outputs(trajectory, output, viewer_output)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate a relativistic charged particle in a static EM field."
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/generated/relativistic_charged_particle.json"),
    )
    parser.add_argument(
        "--viewer-output",
        type=Path,
        default=Path("viewer/public/data/relativistic_charged_particle.json"),
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> None:
    args = parse_args(argv)
    write_relativistic_charged_particle_trajectory(
        args.output,
        viewer_output=args.viewer_output,
    )
    print(f"Wrote trajectory to {args.output}")


if __name__ == "__main__":
    main()
