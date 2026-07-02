from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

import sympy as sp

from engine.export import Trajectory
from engine.numerics import integrate_fixed_step
from scripts.generation import invariant_residual_records, write_trajectory_outputs
from systems.crossed_eb_drift import (
    analytic_drift_velocity,
    coordinate_time_series,
    em_invariant_series,
    four_velocity_norm_series,
    initial_state,
    mass_shell_series,
    measured_drift_velocity,
    p_z_series,
    spacetime_renderer_hints,
    worldline_payload,
)
from systems.crossed_eb_drift import build_system


def generate_crossed_eb_drift(
    *,
    mass: float = 1.0,
    charge: float = 1.0,
    electric_field_x: float = 0.25,
    magnetic_field_z: float = 1.0,
    parallel_velocity_z: float = 0.0,
    tau_span: tuple[float, float] = (0.0, 16.0),
    dt: float = 0.01,
) -> Trajectory:
    """Generate the BE-129 crossed-field ``E x B`` drift export."""

    if mass <= 0.0:
        raise ValueError("mass must be positive")
    system = build_system()
    substitutions = {
        sp.Symbol("B_z", real=True, nonzero=True): magnetic_field_z,
        sp.Symbol("E_x", real=True): electric_field_x,
        sp.Symbol("m", positive=True): mass,
        sp.Symbol("q", real=True): charge,
    }
    time, states = integrate_fixed_step(
        system.numerical_rhs(substitutions),
        initial_state(
            electric_field_x=electric_field_x,
            magnetic_field_z=magnetic_field_z,
            parallel_velocity_z=parallel_velocity_z,
            mass=mass,
        ),
        tau_span,
        dt,
    )

    mass_shell = mass_shell_series(states, mass=mass)
    four_velocity_norm = four_velocity_norm_series(states, mass=mass)
    p_z = p_z_series(states)
    em_invariants = em_invariant_series(
        len(time),
        electric_field_x=electric_field_x,
        magnetic_field_z=magnetic_field_z,
    )
    series = {
        "mass_shell": mass_shell,
        "four_velocity_norm": four_velocity_norm,
        "p_z": p_z,
        "coordinate_time": coordinate_time_series(states),
        **em_invariants,
    }
    expected_drift = analytic_drift_velocity(
        electric_field_x=electric_field_x,
        magnetic_field_z=magnetic_field_z,
    )
    measured_drift = measured_drift_velocity(states)

    metadata = {
        "system": "crossed_eb_drift",
        "kind": "covariant-em",
        "parameters": {
            "m": float(mass),
            "q": float(charge),
            "E_x": float(electric_field_x),
            "B_z": float(magnetic_field_z),
            "parallel_velocity_z": float(parallel_velocity_z),
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
                "components": [float(electric_field_x), 0.0, 0.0],
            },
            "magnetic": {
                "kind": "uniform-magnetic-field",
                "components": [0.0, 0.0, float(magnetic_field_z)],
            },
        },
        "drift": {
            "expression": "E x B / B^2",
            "expectedVelocity": list(expected_drift),
            "measuredVelocity": list(measured_drift),
            "evaluation": "measured-rollout",
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


def write_crossed_eb_drift_trajectory(
    output: Path,
    *,
    viewer_output: Path | None = None,
) -> Trajectory:
    trajectory = generate_crossed_eb_drift()
    return write_trajectory_outputs(trajectory, output, viewer_output)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate a relativistic charged particle in crossed E and B fields."
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/generated/crossed_eb_drift.json"),
    )
    parser.add_argument(
        "--viewer-output",
        type=Path,
        default=Path("viewer/public/data/crossed_eb_drift.json"),
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> None:
    args = parse_args(argv)
    write_crossed_eb_drift_trajectory(args.output, viewer_output=args.viewer_output)
    print(f"Wrote trajectory to {args.output}")


if __name__ == "__main__":
    main()
