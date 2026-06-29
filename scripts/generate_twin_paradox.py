from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

from engine.export import Trajectory
from scripts.generation import write_trajectory_outputs
from systems.twin_paradox import (
    state_series,
    twin_renderer_hints,
    twin_worldline_samples,
    worldline_records,
)


def generate_twin_paradox(
    *,
    coordinate_duration: float = 8.0,
    travel_speed: float = 0.6,
    sample_count: int = 401,
) -> Trajectory:
    samples = twin_worldline_samples(
        coordinate_duration=coordinate_duration,
        travel_speed=travel_speed,
        sample_count=sample_count,
    )
    coordinate_time = samples["coordinateTime"]
    inertial = samples["inertial"]
    traveler = samples["traveler"]
    proper_time_difference = [
        float(left - right)
        for left, right in zip(
            inertial["properTime"],
            traveler["properTime"],
            strict=True,
        )
    ]
    series = {
        "inertial_proper_time": inertial["properTime"],
        "traveler_proper_time": traveler["properTime"],
        "proper_time_difference": proper_time_difference,
    }
    metadata = {
        "system": "twin_paradox",
        "kind": "relativistic-worldline",
        "comparison": "twin-paradox",
        "parameters": {
            "coordinateDuration": coordinate_duration,
            "travelSpeed": travel_speed,
            "c": 1.0,
        },
        "coordinateConvention": {
            "signature": "(-,+)",
            "timeCoordinate": "x0 = c t",
            "units": "c=1",
        },
        "worldlines": worldline_records(samples),
        "turnaround": samples["turnaround"],
        "properTimeComparison": {
            "inertial": float(inertial["properTimeTotal"]),
            "traveler": float(traveler["properTimeTotal"]),
            "difference": float(samples["totals"]["difference"]),
            "gamma": float(samples["totals"]["gamma"]),
            "closedForm": {
                "inertial": "Delta tau = Delta t",
                "traveler": "Delta tau = Delta t / gamma",
            },
            "rigor": "measured",
            "evaluation": "sampled-against-closed-form",
        },
        "rendererHints": twin_renderer_hints(samples),
    }
    return Trajectory.from_arrays(
        time=coordinate_time,
        states=state_series(samples),
        state_names=(
            "x0",
            "x1",
            "x0_dot",
            "x1_dot",
        ),
        metadata=metadata,
        series=series,
    )


def write_twin_paradox_trajectory(
    output: Path,
    *,
    viewer_output: Path | None = None,
) -> Trajectory:
    trajectory = generate_twin_paradox()
    return write_trajectory_outputs(trajectory, output, viewer_output)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate twin-paradox worldlines.")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/generated/twin_paradox.json"),
    )
    parser.add_argument(
        "--viewer-output",
        type=Path,
        default=Path("viewer/public/data/twin_paradox.json"),
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> None:
    args = parse_args(argv)
    write_twin_paradox_trajectory(args.output, viewer_output=args.viewer_output)
    print(f"Wrote trajectory to {args.output}")


if __name__ == "__main__":
    main()
