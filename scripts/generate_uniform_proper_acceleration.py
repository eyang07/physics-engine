from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

import sympy as sp

from engine.export import Trajectory
from engine.numerics import integrate_fixed_step
from scripts.generation import invariant_residual_records, write_trajectory_outputs
from systems.uniform_proper_acceleration import (
    closed_form_residual_series,
    closed_form_worldline,
    coordinate_time_series,
    hyperbola_residual_series,
    initial_state,
    invariant_interval_rate_series,
    rapidity_residual_series,
    spacetime_renderer_hints,
    worldline_payload,
)
from systems.uniform_proper_acceleration import build_system


def generate_uniform_proper_acceleration(
    *,
    acceleration: float = 0.35,
    tau_span: tuple[float, float] = (0.0, 6.0),
    dt: float = 0.01,
) -> Trajectory:
    if acceleration <= 0.0:
        raise ValueError("acceleration must be positive")
    system = build_system()
    time, states = integrate_fixed_step(
        system.numerical_rhs({sp.Symbol("a", real=True): acceleration}),
        initial_state(),
        tau_span,
        dt,
    )
    interval_rate = invariant_interval_rate_series(states)
    hyperbola_residual = hyperbola_residual_series(states, acceleration=acceleration)
    rapidity_residual = rapidity_residual_series(
        time,
        states,
        acceleration=acceleration,
    )
    closed_residuals = closed_form_residual_series(
        time,
        states,
        acceleration=acceleration,
    )
    closed = closed_form_worldline(time, acceleration=acceleration)
    series = {
        "proper_interval_rate": interval_rate,
        "hyperbola_residual": hyperbola_residual,
        "rapidity": closed["rapidity"],
        "rapidity_residual": rapidity_residual,
        "coordinate_time": coordinate_time_series(states),
        "proper_time": time.astype(float).tolist(),
        **closed_residuals,
    }
    measured_residuals = {
        "proper_interval_rate": interval_rate,
        "hyperbola_residual": hyperbola_residual,
        "rapidity_residual": rapidity_residual,
        **closed_residuals,
    }
    metadata = {
        "system": "uniform_proper_acceleration",
        "kind": "relativistic-worldline",
        "parameters": {
            "properAcceleration": float(acceleration),
            "c": 1.0,
        },
        "coordinateConvention": {
            "signature": "(-,+)",
            "timeCoordinate": "x0 = c t",
            "properTime": "tau",
            "units": "c=1",
        },
        "worldline": worldline_payload(time, states, acceleration=acceleration),
        "closedForm": {
            "kind": "uniform-proper-acceleration-hyperbola",
            "rapidity": "a * tau",
            "x0": "sinh(a*tau) / a",
            "x1": "(cosh(a*tau) - 1) / a",
            "u0": "cosh(a*tau)",
            "u1": "sinh(a*tau)",
            "evaluation": "measured-against-rollout",
        },
        "rendererHints": spacetime_renderer_hints(states, acceleration=acceleration),
        "invariantResiduals": invariant_residual_records(measured_residuals),
    }
    return Trajectory.from_arrays(
        time=time,
        states=states,
        state_names=[symbol.name for symbol in system.state],
        metadata=metadata,
        series=series,
    )


def write_uniform_proper_acceleration_trajectory(
    output: Path,
    *,
    viewer_output: Path | None = None,
) -> Trajectory:
    trajectory = generate_uniform_proper_acceleration()
    return write_trajectory_outputs(trajectory, output, viewer_output)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate a uniform-proper-acceleration worldline."
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/generated/uniform_proper_acceleration.json"),
    )
    parser.add_argument(
        "--viewer-output",
        type=Path,
        default=Path("viewer/public/data/uniform_proper_acceleration.json"),
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> None:
    args = parse_args(argv)
    write_uniform_proper_acceleration_trajectory(
        args.output,
        viewer_output=args.viewer_output,
    )
    print(f"Wrote trajectory to {args.output}")


if __name__ == "__main__":
    main()
