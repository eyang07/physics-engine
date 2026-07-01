from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

import sympy as sp

from engine.export import Trajectory
from engine.numerics import integrate_fixed_step
from scripts.generation import invariant_residual_records, write_trajectory_outputs
from systems.relativistic_particle_in_potential import (
    coordinate_time_series,
    initial_state,
    mass_shell_series,
    proper_interval_rate_series,
    spacetime_renderer_hints,
    total_energy_series,
    worldline_payload,
)
from systems.relativistic_particle_in_potential import build_system


def generate_relativistic_particle_in_potential(
    *,
    mass: float = 1.0,
    light_speed: float = 1.0,
    stiffness: float = 0.35,
    position: float = 0.9,
    momentum: float = 0.32,
    t_span: tuple[float, float] = (0.0, 18.0),
    dt: float = 0.01,
) -> Trajectory:
    if mass <= 0.0:
        raise ValueError("mass must be positive")
    if light_speed <= 0.0:
        raise ValueError("light_speed must be positive")
    if stiffness <= 0.0:
        raise ValueError("stiffness must be positive")

    system = build_system()
    substitutions = {
        sp.Symbol("m", positive=True): mass,
        sp.Symbol("c", positive=True): light_speed,
        sp.Symbol("k", positive=True): stiffness,
    }
    time, states = integrate_fixed_step(
        system.numerical_rhs(substitutions),
        initial_state(
            position=position,
            momentum=momentum,
            mass=mass,
            light_speed=light_speed,
        ),
        t_span,
        dt,
    )
    total_energy = total_energy_series(
        states,
        stiffness=stiffness,
        light_speed=light_speed,
    )
    mass_shell = mass_shell_series(
        states,
        mass=mass,
        light_speed=light_speed,
    )
    interval_rate = proper_interval_rate_series(states, mass=mass)
    series = {
        "proper_interval_rate": interval_rate,
        "total_energy": total_energy,
        "mass_shell": mass_shell,
        "coordinate_time": coordinate_time_series(states, light_speed=light_speed),
    }
    metadata = {
        "system": "relativistic_particle_in_static_potential",
        "kind": "relativistic-worldline",
        "parameters": {
            "m": float(mass),
            "c": float(light_speed),
            "k": float(stiffness),
            "x1_0": float(position),
            "p_x1_0": float(momentum),
        },
        "coordinateConvention": {
            "signature": "(-,+)",
            "timeCoordinate": "x0 = c t",
            "parameter": "coordinate time t",
            "units": "c=1",
        },
        "potential": {
            "kind": "static-scalar-potential",
            "expression": "V(x1) = k x1^2 / 2",
        },
        "worldline": worldline_payload(
            time,
            states,
            mass=mass,
            light_speed=light_speed,
        ),
        "rendererHints": spacetime_renderer_hints(states),
        "invariantResiduals": invariant_residual_records(
            {
                "proper_interval_rate": interval_rate,
                "total_energy": total_energy,
                "mass_shell": mass_shell,
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


def write_relativistic_particle_in_potential_trajectory(
    output: Path,
    *,
    viewer_output: Path | None = None,
) -> Trajectory:
    trajectory = generate_relativistic_particle_in_potential()
    return write_trajectory_outputs(trajectory, output, viewer_output)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate a relativistic particle in a static potential."
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/generated/relativistic_particle_in_potential.json"),
    )
    parser.add_argument(
        "--viewer-output",
        type=Path,
        default=Path("viewer/public/data/relativistic_particle_in_potential.json"),
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> None:
    args = parse_args(argv)
    write_relativistic_particle_in_potential_trajectory(
        args.output,
        viewer_output=args.viewer_output,
    )
    print(f"Wrote trajectory to {args.output}")


if __name__ == "__main__":
    main()
