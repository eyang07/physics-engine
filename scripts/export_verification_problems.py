"""Export verification-problem inspection artifacts (backend-only).

Builds the controlled-pendulum barrier verification problem and runs the
stub inspection adapter on it. The artifacts are for external inspection;
nothing here crosses the manifest/viewer boundary or claims proof discharge.
"""

from __future__ import annotations

import argparse
from collections.abc import Callable, Mapping
from dataclasses import dataclass, replace

import numpy as np
import sympy as sp

from engine.dynamics import BarrierCandidate, SafetySpecification, SublevelSet
from engine.numerics import integrate_fixed_step
from engine.verification import (
    VerificationProblem,
    scalar_field_region_geometries,
    sampled_region_proof_statuses,
    verification_problem_from_barrier,
    write_inspection_artifacts,
)
from systems.controlled_pendulum import build_system
from systems.controlled_spring import build_system as build_spring_system

DEFAULT_OUTPUT_DIR = "data/generated/verification"

# The verification world is self-contained: its phase plane is the problem's own
# (theta, omega) state, mapped to itself, with no dependency on any gallery
# manifest system.
_PHASE_AXES = {"theta": "theta", "omega": "omega"}
_SPRING_PHASE_AXES = {"x": "x", "v": "v"}


@dataclass(frozen=True)
class ViewerVerificationExample:
    """A self-contained verification problem plus the trajectory it animates."""

    problem_factory: Callable[[], VerificationProblem]
    trajectory_factory: Callable[[], tuple[np.ndarray, np.ndarray]]
    variable_to_state_axis: Mapping[str, str]


def upright_pendulum_closed_loop():
    """The PD-stabilized upright pendulum closed-loop system and its state.

    This is the single source of truth for both the verification problem and the
    controlled trajectory the viewer animates, so the obligations and the path
    describe the same system.
    """

    pendulum = build_system(mass=1.0, length=1.0, gravity=9.81, damping=0.1)
    theta, omega = pendulum.state
    (u,) = pendulum.controls
    closed = pendulum.closed_loop({u: -20 * (theta - sp.pi) - 5 * omega})
    return closed, theta, omega


def upright_pendulum_problem() -> VerificationProblem:
    """PD-stabilized upright pendulum with an energy-style barrier candidate."""

    closed, theta, omega = upright_pendulum_closed_loop()

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
        metadata={"verificationModel": "controlled-pendulum-closed-loop"},
    )
    geometry = scalar_field_region_geometries(
        problem.regions,
        projection="phase",
        plane_variables=("theta", "omega"),
        variable_to_state_axis=_PHASE_AXES,
        x_range=(-0.5, 4.0),
        y_range=(-3.0, 3.0),
        samples=(91, 91),
    )
    problem = replace(problem, region_geometry=geometry)
    return replace(problem, proof_statuses=sampled_region_proof_statuses(problem))


def upright_pendulum_trajectory(
    *,
    theta0: float = float(sp.pi) - 0.25,
    omega0: float = 0.0,
    t_span: tuple[float, float] = (0.0, 8.0),
    dt: float = 0.01,
) -> tuple[np.ndarray, np.ndarray]:
    """Integrate the closed loop from a point inside the initial set.

    Starting near upright, the PD controller holds the pole there, so the path
    stays in the safe corridor — the coherent motion the obligations are about.
    Returns ``(time, states)`` with state columns ``(theta, omega)``.
    """

    closed, _, _ = upright_pendulum_closed_loop()
    time, states = integrate_fixed_step(
        closed.numerical_rhs(),
        initial_state=[float(theta0), float(omega0)],
        t_span=t_span,
        dt=dt,
    )
    return time, states


def spring_mass_closed_loop():
    """The controlled spring-mass regulator closed-loop system and its state."""

    spring = build_spring_system(
        mass=sp.Integer(1),
        stiffness=sp.Integer(1),
        damping=sp.Rational(2, 5),
    )
    x, v = spring.state
    (u,) = spring.controls
    closed = spring.closed_loop({u: -x - sp.Rational(13, 5) * v})
    return closed, x, v


def controlled_spring_problem() -> VerificationProblem:
    """Controlled spring-mass regulator with a quadratic barrier candidate."""

    closed, x, v = spring_mass_closed_loop()

    regulated_energy = x**2 + x * v + v**2
    specification = SafetySpecification(
        state=(x, v),
        safe_set=SublevelSet(
            state=(x, v),
            expression=regulated_energy,
            level=1.0,
            name="regulated-energy",
        ),
        unsafe_sets=(
            SublevelSet(
                state=(x, v),
                expression=-regulated_energy,
                level=-1.5,
                name="outside-energy-envelope",
            ),
        ),
        initial_set=SublevelSet(
            state=(x, v),
            expression=regulated_energy,
            level=0.16,
            name="start-ellipse",
        ),
    )
    barrier = BarrierCandidate(
        state=(x, v),
        function=regulated_energy - 1,
        name="regulated-energy-barrier",
    )

    problem = verification_problem_from_barrier(
        "controlled spring regulator safety",
        closed,
        barrier,
        specification=specification,
        metadata={"verificationModel": "controlled-spring-regulator"},
    )
    geometry = scalar_field_region_geometries(
        problem.regions,
        projection="phase",
        plane_variables=("x", "v"),
        variable_to_state_axis=_SPRING_PHASE_AXES,
        x_range=(-1.8, 1.8),
        y_range=(-1.8, 1.8),
        samples=(81, 81),
    )
    problem = replace(problem, region_geometry=geometry)
    return replace(problem, proof_statuses=sampled_region_proof_statuses(problem))


def controlled_spring_trajectory(
    *,
    x0: float = 0.35,
    v0: float = -0.1,
    t_span: tuple[float, float] = (0.0, 8.0),
    dt: float = 0.01,
) -> tuple[np.ndarray, np.ndarray]:
    """Integrate the regulated spring-mass closed loop inside the initial set."""

    closed, _, _ = spring_mass_closed_loop()
    time, states = integrate_fixed_step(
        closed.numerical_rhs(),
        initial_state=[float(x0), float(v0)],
        t_span=t_span,
        dt=dt,
    )
    return time, states


def viewer_verification_examples() -> tuple[ViewerVerificationExample, ...]:
    """Every self-contained verification problem exported to the viewer."""

    return (
        ViewerVerificationExample(
            problem_factory=upright_pendulum_problem,
            trajectory_factory=upright_pendulum_trajectory,
            variable_to_state_axis=_PHASE_AXES,
        ),
        ViewerVerificationExample(
            problem_factory=controlled_spring_problem,
            trajectory_factory=controlled_spring_trajectory,
            variable_to_state_axis=_SPRING_PHASE_AXES,
        ),
    )


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        default=DEFAULT_OUTPUT_DIR,
        help="directory for inspection artifacts",
    )
    args = parser.parse_args(argv)

    for example in viewer_verification_examples():
        report = write_inspection_artifacts(example.problem_factory(), args.output_dir)
        for artifact in report.artifacts:
            print(f"wrote {artifact.kind}: {artifact.path}")
        print(report.note)


if __name__ == "__main__":
    main()
