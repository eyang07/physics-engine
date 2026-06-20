from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

import numpy as np

from engine.export import Trajectory
from scripts.generation import invariant_residual_records
from systems.vibrating_string import (
    dalembert_solution,
    gaussian_profile,
    modal_displacement,
    modal_energy,
    right_traveling_velocity_antiderivative,
    build_system,
)


DEFAULT_PARAMETERS = {
    "L": 1.0,
    "c": 1.0,
    "rho": 1.0,
}
DEFAULT_AMPLITUDES = [0.18, 0.08, 0.045]


def _displacement_series_payload(
    *,
    name: str,
    x_axis: np.ndarray,
    time: np.ndarray,
    values: np.ndarray,
    variant: str,
) -> dict[str, object]:
    return {
        "kind": "scalar-field-series",
        "rendererHint": "scalar-field",
        "name": name,
        "coordinates": ["x"],
        "axes": [x_axis.astype(float).tolist()],
        "time": time.astype(float).tolist(),
        "shape": list(values.shape),
        "values": values.astype(float).tolist(),
        "variant": variant,
        "evaluation": "analytic-exact",
    }


def generate_vibrating_string(
    *,
    sample_count: int = 129,
    time_count: int = 121,
) -> Trajectory:
    if sample_count < 3:
        raise ValueError("sample_count must be at least 3")
    if time_count < 2:
        raise ValueError("time_count must be at least 2")

    system = build_system()
    length = DEFAULT_PARAMETERS["L"]
    wave_speed = DEFAULT_PARAMETERS["c"]
    x_axis = np.linspace(0.0, length, sample_count)
    time = np.linspace(0.0, 2.0 * length / wave_speed, time_count)
    standing = modal_displacement(
        system,
        x_axis,
        time,
        DEFAULT_AMPLITUDES,
        parameters=DEFAULT_PARAMETERS,
    )
    energy = modal_energy(
        system,
        x_axis,
        time,
        DEFAULT_AMPLITUDES,
        parameters=DEFAULT_PARAMETERS,
    )

    profile = gaussian_profile(center=0.25, width=0.07)
    traveling = dalembert_solution(
        x_axis,
        time,
        wave_speed=wave_speed,
        initial_displacement=profile,
        initial_velocity_antiderivative=right_traveling_velocity_antiderivative(
            wave_speed=wave_speed,
            profile=profile,
        ),
    )

    metadata = {
        "system": "vibrating_string",
        "kind": "field-evolution",
        "parameters": dict(DEFAULT_PARAMETERS),
        "boundary": system.boundary.kind,
        "fields": {
            "standingDisplacement": _displacement_series_payload(
                name="standingDisplacement",
                x_axis=x_axis,
                time=time,
                values=standing,
                variant="fixed-fixed-modal-superposition",
            ),
            "travelingDisplacement": _displacement_series_payload(
                name="travelingDisplacement",
                x_axis=x_axis,
                time=time,
                values=traveling,
                variant="dalembert-right-traveling-gaussian",
            ),
        },
        "modeAmplitudes": list(DEFAULT_AMPLITUDES),
        "energyDiagnostics": {
            "rigor": "measured",
            "series": "energy",
            "residuals": invariant_residual_records({"energy": energy}),
        },
    }

    return Trajectory.from_arrays(
        time=time,
        states=standing,
        state_names=[f"u_{index}" for index in range(sample_count)],
        metadata=metadata,
        series={"energy": energy.astype(float).tolist()},
    )


def write_vibrating_string(
    output: Path,
    *,
    viewer_output: Path | None = None,
) -> Trajectory:
    trajectory = generate_vibrating_string()
    trajectory.write_json(output)
    if viewer_output is not None:
        trajectory.write_json(viewer_output)
    return trajectory


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate vibrating-string field data.")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/generated/vibrating_string.json"),
    )
    parser.add_argument(
        "--viewer-output",
        type=Path,
        default=Path("viewer/public/data/vibrating_string.json"),
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> None:
    args = parse_args(argv)
    write_vibrating_string(args.output, viewer_output=args.viewer_output)
    print(f"Wrote field data to {args.output}")


if __name__ == "__main__":
    main()
