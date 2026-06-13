"""Export verification-problem inspection artifacts (backend-only).

Builds the controlled-pendulum barrier verification problem and runs the
stub inspection adapter on it. The artifacts are for external inspection;
nothing here crosses the manifest/viewer boundary or claims proof discharge.
"""

from __future__ import annotations

import argparse
from dataclasses import replace

import sympy as sp

from engine.dynamics import BarrierCandidate, SafetySpecification, SublevelSet
from engine.verification import (
    VerificationProblem,
    scalar_field_region_geometries,
    sampled_region_proof_statuses,
    verification_problem_from_barrier,
    write_inspection_artifacts,
)
from systems.controlled_pendulum import build_system

DEFAULT_OUTPUT_DIR = "data/generated/verification"


def upright_pendulum_problem() -> VerificationProblem:
    """PD-stabilized upright pendulum with an energy-style barrier candidate."""

    pendulum = build_system(mass=1.0, length=1.0, gravity=9.81, damping=0.1)
    theta, omega = pendulum.state
    (u,) = pendulum.controls
    closed = pendulum.closed_loop({u: -20 * (theta - sp.pi) - 5 * omega})

    d = theta - sp.pi
    energy = omega**2 / 2 + 10 * d**2 + sp.Rational(981, 100) * (sp.cos(d) - 1)
    specification = SafetySpecification(
        state=(theta, omega),
        safe_set=SublevelSet(
            state=(theta, omega), expression=d**2, level=0.25, name="corridor"
        ),
        unsafe_sets=(
            SublevelSet(
                state=(theta, omega), expression=theta, level=0.2, name="near-bottom"
            ),
        ),
        initial_set=SublevelSet(
            state=(theta, omega),
            expression=d**2 + omega**2,
            level=0.09,
            name="start-ball",
        ),
    )
    barrier = BarrierCandidate(
        state=(theta, omega),
        function=energy - sp.Rational(12, 10),
        name="energy-barrier",
    )

    problem = verification_problem_from_barrier(
        "upright pendulum safety",
        closed,
        barrier,
        specification=specification,
        metadata={
            "system": "pendulum",
            "verificationModel": "controlled-pendulum-closed-loop",
        },
    )
    geometry = scalar_field_region_geometries(
        problem.regions,
        projection="phase",
        plane_variables=("theta", "omega"),
        variable_to_state_axis={"theta": "theta", "omega": "theta_dot"},
        x_range=(-0.5, 4.0),
        y_range=(-3.0, 3.0),
        samples=(91, 91),
    )
    problem = replace(problem, region_geometry=geometry)
    return replace(problem, proof_statuses=sampled_region_proof_statuses(problem))


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        default=DEFAULT_OUTPUT_DIR,
        help="directory for inspection artifacts",
    )
    args = parser.parse_args(argv)

    report = write_inspection_artifacts(upright_pendulum_problem(), args.output_dir)
    for artifact in report.artifacts:
        print(f"wrote {artifact.kind}: {artifact.path}")
    print(report.note)


if __name__ == "__main__":
    main()
