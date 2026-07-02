from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

from engine.export import Trajectory
from engine.numerics import integrate_fixed_step
from engine.verification import VerificationProblem, worldline_conservation_verification_problem
from scripts.generation import invariant_residual_records, write_trajectory_outputs
from systems.relativistic_free_particle import (
    coordinate_time_series,
    initial_state_from_velocity,
    interval_rate_expression,
    invariant_interval_rate_series,
    spacetime_renderer_hints,
    worldline_payload,
)
from systems.relativistic_free_particle import build_system


def generate_relativistic_free_particle(
    *,
    velocity: Sequence[float] = (0.55, 0.18),
    tau_span: tuple[float, float] = (0.0, 6.0),
    dt: float = 0.02,
) -> Trajectory:
    system = build_system()
    time, states = integrate_fixed_step(
        system.numerical_rhs(),
        initial_state_from_velocity(velocity),
        tau_span,
        dt,
    )
    interval_rate = invariant_interval_rate_series(states)
    series = {
        "proper_interval_rate": interval_rate,
        "coordinate_time": coordinate_time_series(states),
        "proper_time": time.astype(float).tolist(),
    }
    metadata = {
        "system": "relativistic_free_particle",
        "kind": "relativistic-worldline",
        "parameters": {
            "velocity": [float(component) for component in velocity],
            "c": 1.0,
        },
        "coordinateConvention": {
            "signature": "(-,+,+)",
            "timeCoordinate": "x0 = c t",
            "properTime": "tau",
            "units": "c=1",
        },
        "worldline": worldline_payload(time, states),
        "rendererHints": spacetime_renderer_hints(states),
        "invariantResiduals": invariant_residual_records(
            {"proper_interval_rate": interval_rate}
        ),
    }
    return Trajectory.from_arrays(
        time=time,
        states=states,
        state_names=[symbol.name for symbol in system.state],
        metadata=metadata,
        series=series,
    )


def write_relativistic_free_particle_trajectory(
    output: Path,
    *,
    viewer_output: Path | None = None,
) -> Trajectory:
    trajectory = generate_relativistic_free_particle()
    return write_trajectory_outputs(trajectory, output, viewer_output)


def generate_relativistic_free_particle_verification(
    *,
    velocity: Sequence[float] = (0.55, 0.18),
    tau_span: tuple[float, float] = (0.0, 6.0),
    dt: float = 0.02,
    tolerance: float = 1e-6,
) -> VerificationProblem:
    """Mass-shell and four-momentum-conservation obligations for BE-124.

    The free particle's state is ``(x^mu, u^mu)`` at the system's implicit
    unit-mass, ``c = 1`` normalization, so the four-velocity components
    ``u^mu`` are proportional to the four-momentum ``p^mu = m u^mu``: bounding
    ``u^mu`` near its initial value is equivalent to bounding four-momentum
    conservation. The mass-shell claim reuses the same interval-rate
    expression the trajectory export already carries as ``proper_interval_rate``.
    """

    system = build_system()
    time, states = integrate_fixed_step(
        system.numerical_rhs(),
        initial_state_from_velocity(velocity),
        tau_span,
        dt,
    )
    dimension = len(system.state) // 2
    momentum_symbols = system.state[dimension:]
    mass_shell_expression = interval_rate_expression(system) + 1
    return worldline_conservation_verification_problem(
        id="relativistic-free-particle-conservation",
        name="Relativistic free-particle mass-shell and four-momentum conservation",
        system_id="relativistic_free_particle",
        system=system,
        mass_shell_expression=mass_shell_expression,
        momentum_symbols=momentum_symbols,
        time=time,
        states=states,
        tolerance=tolerance,
    )


def write_relativistic_free_particle_verification(
    output: Path,
    *,
    viewer_output: Path | None = None,
) -> VerificationProblem:
    problem = generate_relativistic_free_particle_verification()
    problem.write_json(output)
    if viewer_output is not None:
        problem.write_json(viewer_output)
    return problem


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate a relativistic free-particle worldline."
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/generated/relativistic_free_particle.json"),
    )
    parser.add_argument(
        "--viewer-output",
        type=Path,
        default=Path("viewer/public/data/relativistic_free_particle.json"),
    )
    parser.add_argument(
        "--verification-output",
        type=Path,
        default=Path("data/generated/relativistic_free_particle_verification.json"),
    )
    parser.add_argument(
        "--verification-viewer-output",
        type=Path,
        default=Path("viewer/public/data/relativistic_free_particle_verification.json"),
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> None:
    args = parse_args(argv)
    write_relativistic_free_particle_trajectory(
        args.output,
        viewer_output=args.viewer_output,
    )
    print(f"Wrote trajectory to {args.output}")
    write_relativistic_free_particle_verification(
        args.verification_output,
        viewer_output=args.verification_viewer_output,
    )
    print(f"Wrote verification problem to {args.verification_output}")


if __name__ == "__main__":
    main()
