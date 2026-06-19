from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

import numpy as np

from engine.export import Trajectory
from engine.mechanics import normal_modes
from scripts.example_specs import COUPLED_OSCILLATORS
from scripts.generation import generate_lagrangian_trajectory, write_trajectory_outputs
from systems.coupled_oscillators import build_system


def coupled_mode_metadata(mass: float, spring_constant: float) -> dict[str, object]:
    system = build_system(mass=mass, spring_constant=spring_constant)
    equilibrium = {coordinate: 0.0 for coordinate in system.q}
    modes = normal_modes(system, equilibrium)
    payload = modes.to_dict()
    payload["method"] = "small-oscillation-generalized-eigenproblem"
    return payload


def generate_coupled_oscillator_trajectory(
    *,
    mass: float = 1.0,
    spring_constant: float = 1.0,
    t_span: tuple[float, float] = (0.0, 24.0),
    dt: float = 0.01,
) -> Trajectory:
    system = build_system(mass=mass, spring_constant=spring_constant)
    equilibrium = {coordinate: 0.0 for coordinate in system.q}
    modes = normal_modes(system, equilibrium)
    displacement = 0.6 * modes.mode_shapes[:, 0] + 0.28 * modes.mode_shapes[:, 1]
    velocity = np.zeros_like(displacement)
    initial_state = np.concatenate([displacement, velocity])
    coordinate_names = [symbol.name for symbol in system.q]
    velocity_names = [symbol.name for symbol in system.qdot]

    return generate_lagrangian_trajectory(
        spec=COUPLED_OSCILLATORS,
        system=system,
        initial_state=initial_state,
        t_span=t_span,
        dt=dt,
        state_names=[*coordinate_names, *velocity_names],
        physical_parameters={"m": mass, "k": spring_constant},
        metadata={
            "system": "coupled_oscillators",
            "mass": mass,
            "springConstant": spring_constant,
            "normalModes": coupled_mode_metadata(mass, spring_constant),
            "rendererHints": {
                "kind": "normal-mode-chain",
                "bodyCount": len(coordinate_names),
                "equilibriumPositions": [
                    float(index)
                    for index in np.linspace(-1.5, 1.5, len(coordinate_names))
                ],
            },
        },
    )


def write_coupled_oscillator_trajectory(
    output: Path,
    *,
    viewer_output: Path | None = None,
    mass: float = 1.0,
    spring_constant: float = 1.0,
    t_end: float = 24.0,
    dt: float = 0.01,
) -> Trajectory:
    trajectory = generate_coupled_oscillator_trajectory(
        mass=mass,
        spring_constant=spring_constant,
        t_span=(0.0, t_end),
        dt=dt,
    )
    return write_trajectory_outputs(trajectory, output, viewer_output)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate coupled-oscillator data.")
    parser.add_argument("--output", type=Path, default=Path("data/generated/coupled_oscillators.json"))
    parser.add_argument("--viewer-output", type=Path, default=Path("viewer/public/data/coupled_oscillators.json"))
    parser.add_argument("--mass", type=float, default=1.0)
    parser.add_argument("--spring-constant", type=float, default=1.0)
    parser.add_argument("--t-end", type=float, default=24.0)
    parser.add_argument("--dt", type=float, default=0.01)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> None:
    args = parse_args(argv)
    trajectory = write_coupled_oscillator_trajectory(
        args.output,
        viewer_output=args.viewer_output,
        mass=args.mass,
        spring_constant=args.spring_constant,
        t_end=args.t_end,
        dt=args.dt,
    )
    print(f"Wrote {len(trajectory.time)} samples to {args.output}")
    if args.viewer_output is not None:
        print(f"Wrote viewer copy to {args.viewer_output}")


if __name__ == "__main__":
    main()
