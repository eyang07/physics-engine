from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

import numpy as np

from engine.export import Trajectory
from engine.mechanics import (
    InertiaTensor,
    angular_momentum_magnitude,
    body_angular_momentum,
    euler_equations_rhs,
    rotational_kinetic_energy,
)
from engine.numerics import integrate_adaptive
from scripts.example_specs import FREE_RIGID_BODY
from scripts.generation import invariant_residual_records, write_trajectory_outputs


DEFAULT_MOMENTS = (1.0, 2.0, 3.2)
DEFAULT_INITIAL_OMEGA = (0.02, 1.0, 0.02)
STATE_NAMES = ("omega_1", "omega_2", "omega_3")


def rigid_body_geometry(inertia: InertiaTensor, angular_velocity: np.ndarray) -> dict[str, object]:
    states = np.asarray(angular_velocity, dtype=float)
    if states.ndim != 2 or states.shape[1] != 3:
        raise ValueError("angular_velocity must have shape (sample, 3)")

    moments = np.diag(inertia.matrix)
    if not np.allclose(inertia.matrix, np.diag(moments), atol=1e-12, rtol=1e-12):
        raise ValueError("free rigid-body geometry expects principal-axis inertia")

    angular_momentum = np.array(
        [body_angular_momentum(inertia, omega) for omega in states],
        dtype=float,
    )
    energies = np.array(
        [rotational_kinetic_energy(inertia, omega) for omega in states],
        dtype=float,
    )
    momentum_norms = np.array(
        [angular_momentum_magnitude(inertia, omega) for omega in states],
        dtype=float,
    )
    energy = float(np.mean(energies))
    momentum_radius = float(np.mean(momentum_norms))

    return {
        "kind": "rigid-body-polhode",
        "rigor": "measured",
        "principalMoments": moments.astype(float).tolist(),
        "angularMomentumSphere": {
            "space": "body-angular-momentum",
            "radius": momentum_radius,
            "equation": "L1^2 + L2^2 + L3^2 = |L|^2",
        },
        "energyEllipsoid": {
            "space": "body-angular-momentum",
            "semiAxes": np.sqrt(2.0 * energy * moments).astype(float).tolist(),
            "equation": "L1^2/I1 + L2^2/I2 + L3^2/I3 = 2H",
        },
        "polhode": {
            "space": "body-angular-velocity",
            "stateNames": list(STATE_NAMES),
            "points": states.astype(float).tolist(),
        },
        "angularMomentumCurve": {
            "space": "body-angular-momentum",
            "points": angular_momentum.astype(float).tolist(),
        },
    }


def free_rigid_body_renderer_hints() -> dict[str, object]:
    return {
        "kind": "rigid-body-polhode",
        "geometry": "rigidBodyGeometry",
        "state": "angularVelocity",
        "invariantRigor": "measured",
    }


def generate_free_rigid_body_trajectory(
    *,
    moments: Sequence[float] = DEFAULT_MOMENTS,
    initial_omega: Sequence[float] = DEFAULT_INITIAL_OMEGA,
    t_span: tuple[float, float] = (0.0, 24.0),
    sample_dt: float = 0.02,
) -> Trajectory:
    inertia = InertiaTensor.diagonal(moments)
    initial = np.asarray(initial_omega, dtype=float)
    time, states = integrate_adaptive(
        euler_equations_rhs(inertia),
        initial_state=initial,
        t_span=t_span,
        sample_dt=sample_dt,
        rtol=1e-11,
        atol=1e-13,
        max_step=sample_dt,
    )
    physical_parameters = {
        f"I{index}": float(moment)
        for index, moment in enumerate(np.asarray(moments, dtype=float), start=1)
    }
    series = FREE_RIGID_BODY.series(physical_parameters, states)
    metadata = {
        "system": "free_rigid_body",
        "kind": "first-order-flow",
        "configuration": "intermediate-axis-instability",
        "rendererHints": free_rigid_body_renderer_hints(),
        "rigidBodyGeometry": rigid_body_geometry(inertia, states),
        "invariantResiduals": invariant_residual_records(series),
    }
    return Trajectory.from_arrays(
        time=time,
        states=states,
        state_names=STATE_NAMES,
        metadata=metadata,
        series=series,
    )


def write_free_rigid_body_trajectory(
    output: Path,
    *,
    viewer_output: Path | None = None,
    t_end: float = 24.0,
    sample_dt: float = 0.02,
) -> Trajectory:
    trajectory = generate_free_rigid_body_trajectory(
        t_span=(0.0, t_end),
        sample_dt=sample_dt,
    )
    return write_trajectory_outputs(trajectory, output, viewer_output)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate free rigid-body data.")
    parser.add_argument("--output", type=Path, default=Path("data/generated/free_rigid_body.json"))
    parser.add_argument("--viewer-output", type=Path, default=Path("viewer/public/data/free_rigid_body.json"))
    parser.add_argument("--t-end", type=float, default=24.0)
    parser.add_argument("--sample-dt", type=float, default=0.02)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> None:
    args = parse_args(argv)
    trajectory = write_free_rigid_body_trajectory(
        args.output,
        viewer_output=args.viewer_output,
        t_end=args.t_end,
        sample_dt=args.sample_dt,
    )
    print(f"Wrote {len(trajectory.time)} samples to {args.output}")
    if args.viewer_output is not None:
        print(f"Wrote viewer copy to {args.viewer_output}")


if __name__ == "__main__":
    main()
