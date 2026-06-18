from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

import numpy as np

from engine.export import Trajectory
from engine.export.manifest import ParameterVariant
from engine.numerics import integrate_fixed_step
from scripts.example_specs import N_BODY_GRAVITY
from scripts.generation import (
    invariant_residual_records,
    write_parameter_variant_trajectories,
    write_trajectory_outputs,
)
from systems.n_body_gravity import NBodyLayout, build_system


@dataclass(frozen=True)
class NBodyInitialState:
    """Masses, positions, and velocities for one planar N-body scenario."""

    masses: tuple[float, ...]
    positions: np.ndarray
    velocities: np.ndarray
    gravitational_constant: float = 1.0
    name: str = "custom"

    def __post_init__(self) -> None:
        positions = np.asarray(self.positions, dtype=float)
        velocities = np.asarray(self.velocities, dtype=float)
        if positions.ndim != 2 or positions.shape[1] != 2:
            raise ValueError("positions must have shape (N, 2)")
        if velocities.shape != positions.shape:
            raise ValueError("velocities must match positions")
        if len(self.masses) != positions.shape[0]:
            raise ValueError("masses must match positions")
        if any(mass <= 0.0 for mass in self.masses):
            raise ValueError("masses must be positive")
        if self.gravitational_constant <= 0.0:
            raise ValueError("gravitational_constant must be positive")

    @property
    def body_count(self) -> int:
        return len(self.masses)

    def centered(self) -> "NBodyInitialState":
        masses = np.asarray(self.masses, dtype=float)
        total_mass = float(masses.sum())
        position_center = (masses[:, None] * self.positions).sum(axis=0) / total_mass
        velocity_center = (masses[:, None] * self.velocities).sum(axis=0) / total_mass
        return NBodyInitialState(
            masses=self.masses,
            positions=np.asarray(self.positions, dtype=float) - position_center,
            velocities=np.asarray(self.velocities, dtype=float) - velocity_center,
            gravitational_constant=self.gravitational_constant,
            name=self.name,
        )

    def state_vector(self) -> np.ndarray:
        centered = self.centered()
        return np.concatenate(
            [
                centered.positions.reshape(-1),
                centered.velocities.reshape(-1),
            ]
        )


def figure_eight_initial_state() -> NBodyInitialState:
    return NBodyInitialState(
        masses=(1.0, 1.0, 1.0),
        positions=np.array(
            [
                [-0.97000436, 0.24308753],
                [0.97000436, -0.24308753],
                [0.0, 0.0],
            ],
            dtype=float,
        ),
        velocities=np.array(
            [
                [0.466203685, 0.43236573],
                [0.466203685, 0.43236573],
                [-0.93240737, -0.86473146],
            ],
            dtype=float,
        ),
        gravitational_constant=1.0,
        name="figure-eight",
    )


def sun_two_planets_initial_state() -> NBodyInitialState:
    return NBodyInitialState(
        masses=(1.0, 0.001, 0.0005),
        positions=np.array(
            [
                [0.0, 0.0],
                [1.0, 0.0],
                [1.65, 0.0],
            ],
            dtype=float,
        ),
        velocities=np.array(
            [
                [0.0, 0.0],
                [0.0, 1.0],
                [0.0, 0.78],
            ],
            dtype=float,
        ),
        gravitational_constant=1.0,
        name="sun-two-planets",
    )


def _parameters_from_initial_state(initial: NBodyInitialState) -> dict[str, float]:
    centered = initial.centered()
    parameters: dict[str, float] = {"G": initial.gravitational_constant}
    for index, mass in enumerate(centered.masses, start=1):
        parameters[f"m{index}"] = mass
    for index, (x, y) in enumerate(centered.positions, start=1):
        parameters[f"x{index}_0"] = float(x)
        parameters[f"y{index}_0"] = float(y)
    for index, (vx, vy) in enumerate(centered.velocities, start=1):
        parameters[f"vx{index}_0"] = float(vx)
        parameters[f"vy{index}_0"] = float(vy)
    return parameters


def n_body_renderer_hints(states: np.ndarray, body_count: int) -> dict[str, object]:
    positions = states[:, : 2 * body_count].reshape(len(states), body_count, 2)
    minimum = positions.min(axis=(0, 1))
    maximum = positions.max(axis=(0, 1))
    center = (minimum + maximum) / 2
    span = maximum - minimum
    radius = float(max(span.max() / 2, 1.0))
    return {
        "kind": "n-body-orbits",
        "centerOfMassFrame": True,
        "bodyCount": body_count,
        "bounds": {
            "x": [float(center[0] - radius), float(center[0] + radius)],
            "y": [float(center[1] - radius), float(center[1] + radius)],
        },
        "bodyColors": ["primary", "secondary", "accent"][:body_count],
    }


def generate_n_body_trajectory(
    *,
    initial: NBodyInitialState | None = None,
    t_span: tuple[float, float] = (0.0, 6.3259),
    dt: float = 0.0025,
) -> Trajectory:
    initial_state = figure_eight_initial_state() if initial is None else initial
    centered = initial_state.centered()
    layout = NBodyLayout(centered.body_count)
    system = build_system(
        body_count=centered.body_count,
        masses=centered.masses,
        gravitational_constant=centered.gravitational_constant,
    )
    time, states = integrate_fixed_step(
        system.numerical_rhs(),
        initial_state=centered.state_vector(),
        t_span=t_span,
        dt=dt,
    )
    physical_parameters = {
        f"m{index}": mass
        for index, mass in enumerate(centered.masses, start=1)
    }
    physical_parameters["G"] = centered.gravitational_constant
    series = N_BODY_GRAVITY.series(physical_parameters, states)
    metadata = {
        "system": "n_body_gravity",
        "kind": "first-order-flow",
        "configuration": centered.name,
        "bodyCount": centered.body_count,
        "masses": list(centered.masses),
        "gravitationalConstant": centered.gravitational_constant,
        "centerOfMassFrame": True,
        "invariantResiduals": invariant_residual_records(series),
        "rendererHints": n_body_renderer_hints(states, centered.body_count),
    }
    return Trajectory.from_arrays(
        time=time,
        states=states,
        state_names=layout.state_names,
        metadata=metadata,
        series=series,
    )


def write_n_body_trajectory(
    output: Path,
    *,
    viewer_output: Path | None = None,
    initial: NBodyInitialState | None = None,
    t_end: float = 6.3259,
    dt: float = 0.0025,
) -> Trajectory:
    trajectory = generate_n_body_trajectory(
        initial=initial,
        t_span=(0.0, t_end),
        dt=dt,
    )
    return write_trajectory_outputs(trajectory, output, viewer_output)


def _initial_from_variant(variant: ParameterVariant) -> NBodyInitialState:
    parameters = variant.parameters
    masses = tuple(float(parameters[f"m{index}"]) for index in range(1, 4))
    positions = np.array(
        [
            [parameters[f"x{index}_0"], parameters[f"y{index}_0"]]
            for index in range(1, 4)
        ],
        dtype=float,
    )
    velocities = np.array(
        [
            [parameters[f"vx{index}_0"], parameters[f"vy{index}_0"]]
            for index in range(1, 4)
        ],
        dtype=float,
    )
    return NBodyInitialState(
        masses=masses,
        positions=positions,
        velocities=velocities,
        gravitational_constant=float(parameters["G"]),
        name=variant.id,
    )


def _write_variant(
    variant: ParameterVariant,
    output: Path,
    viewer_output: Path | None,
) -> Trajectory:
    return write_n_body_trajectory(
        output,
        viewer_output=viewer_output,
        initial=_initial_from_variant(variant),
    )


def write_n_body_variant_trajectories(
    output_dir: Path,
    *,
    viewer_output_dir: Path | None = None,
) -> list[Trajectory]:
    return write_parameter_variant_trajectories(
        N_BODY_GRAVITY,
        output_dir,
        write_variant=_write_variant,
        viewer_output_dir=viewer_output_dir,
        system_name="N-body gravity",
    )


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate N-body gravity data.")
    parser.add_argument("--output", type=Path, default=Path("data/generated/n_body_gravity.json"))
    parser.add_argument("--viewer-output", type=Path, default=Path("viewer/public/data/n_body_gravity.json"))
    parser.add_argument(
        "--configuration",
        choices=("figure-eight", "sun-two-planets"),
        default="figure-eight",
    )
    parser.add_argument("--t-end", type=float, default=6.3259)
    parser.add_argument("--dt", type=float, default=0.0025)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> None:
    args = parse_args(argv)
    initial = (
        figure_eight_initial_state()
        if args.configuration == "figure-eight"
        else sun_two_planets_initial_state()
    )
    trajectory = write_n_body_trajectory(
        args.output,
        viewer_output=args.viewer_output,
        initial=initial,
        t_end=args.t_end,
        dt=args.dt,
    )
    print(f"Wrote {len(trajectory.time)} samples to {args.output}")
    if args.viewer_output is not None:
        print(f"Wrote viewer copy to {args.viewer_output}")


if __name__ == "__main__":
    main()
