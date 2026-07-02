from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

import numpy as np
import sympy as sp

from engine.export import Trajectory
from engine.numerics import integrate_fixed_step
from scripts.generation import invariant_residual_records, write_trajectory_outputs
from systems.relativistic_cyclotron import (
    coordinate_time_series,
    em_invariant_series,
    four_velocity_norm_series,
    gyrofrequency_expression,
    initial_state,
    mass_shell_series,
    p_z_series,
    spacetime_renderer_hints,
    worldline_payload,
)
from systems.relativistic_cyclotron import build_system


def generate_relativistic_cyclotron(
    *,
    mass: float = 1.0,
    charge: float = 1.0,
    magnetic_field_z: float = 0.9,
    velocity: Sequence[float] = (0.0, 0.42, 0.18),
    position: Sequence[float] = (0.0, 0.85, 0.0, -1.2),
    tau_span: tuple[float, float] = (0.0, 18.0),
    dt: float = 0.01,
) -> Trajectory:
    """Generate the BE-128 relativistic uniform-B cyclotron export."""

    if mass <= 0.0:
        raise ValueError("mass must be positive")
    system = build_system()
    substitutions = {
        sp.Symbol("B_z", real=True): magnetic_field_z,
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
    p_z = p_z_series(states)
    em_invariants = em_invariant_series(
        len(time),
        magnetic_field_z=magnetic_field_z,
    )
    series = {
        "mass_shell": mass_shell,
        "four_velocity_norm": four_velocity_norm,
        "p_z": p_z,
        "coordinate_time": coordinate_time_series(states),
        **em_invariants,
    }

    initial_gamma = float(states[0, 4] / mass)
    expected_gyrofrequency = float(charge * magnetic_field_z / (initial_gamma * mass))
    metadata = {
        "system": "relativistic_cyclotron",
        "kind": "covariant-em",
        "parameters": {
            "m": float(mass),
            "q": float(charge),
            "B_z": float(magnetic_field_z),
            "gamma0": initial_gamma,
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
                "components": [0.0, 0.0, 0.0],
            },
            "magnetic": {
                "kind": "uniform-magnetic-field",
                "components": [0.0, 0.0, float(magnetic_field_z)],
            },
        },
        "gyrofrequency": {
            "expression": "q B_z / (gamma m)",
            "symbolicExpression": str(gyrofrequency_expression(system)),
            "expectedCoordinateTime": expected_gyrofrequency,
            "evaluation": "analytic-from-initial-gamma",
        },
        "worldline": worldline_payload(time, states, mass=mass),
        "rendererHints": spacetime_renderer_hints(states),
        "invariantResiduals": invariant_residual_records(
            {
                "mass_shell": mass_shell,
                "four_velocity_norm": four_velocity_norm,
                "p_z": p_z,
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


def write_relativistic_cyclotron_trajectory(
    output: Path,
    *,
    viewer_output: Path | None = None,
) -> Trajectory:
    trajectory = generate_relativistic_cyclotron()
    return write_trajectory_outputs(trajectory, output, viewer_output)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate a relativistic charged particle in a uniform magnetic field."
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/generated/relativistic_cyclotron.json"),
    )
    parser.add_argument(
        "--viewer-output",
        type=Path,
        default=Path("viewer/public/data/relativistic_cyclotron.json"),
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> None:
    args = parse_args(argv)
    write_relativistic_cyclotron_trajectory(
        args.output,
        viewer_output=args.viewer_output,
    )
    print(f"Wrote trajectory to {args.output}")


if __name__ == "__main__":
    main()
