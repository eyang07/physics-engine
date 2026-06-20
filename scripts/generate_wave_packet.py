from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

import numpy as np

from engine.export import Trajectory
from systems.wave_packet import build_system, envelope_width, numeric_velocities, packet_fields


DEFAULT_PARAMETERS = {
    "alpha": 0.04,
    "k0": 6.0,
    "sigma": 0.45,
    "x0": -1.0,
}


def _series_payload(
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


def generate_wave_packet(
    *,
    sample_count: int = 181,
    time_count: int = 121,
) -> Trajectory:
    if sample_count < 3:
        raise ValueError("sample_count must be at least 3")
    if time_count < 2:
        raise ValueError("time_count must be at least 2")

    packet = build_system()
    parameters = dict(DEFAULT_PARAMETERS)
    x_axis = np.linspace(-3.0, 4.0, sample_count)
    time = np.linspace(0.0, 5.0, time_count)
    amplitude, intensity, widths = packet_fields(
        packet,
        x_axis,
        time,
        parameters=parameters,
    )
    phase_velocity, group_velocity = numeric_velocities(packet, parameters=parameters)
    centers = parameters["x0"] + group_velocity * time

    metadata = {
        "system": "wave_packet",
        "kind": "field-evolution",
        "parameters": parameters,
        "fields": {
            "amplitude": _series_payload(
                name="amplitude",
                x_axis=x_axis,
                time=time,
                values=amplitude,
                variant="quadratic-dispersion-real-amplitude",
            ),
            "intensity": _series_payload(
                name="intensity",
                x_axis=x_axis,
                time=time,
                values=intensity,
                variant="quadratic-dispersion-envelope-intensity",
            ),
        },
        "diagnostics": {
            "rigor": "measured",
            "phaseVelocity": phase_velocity,
            "groupVelocity": group_velocity,
            "center": centers.astype(float).tolist(),
            "width": widths.astype(float).tolist(),
            "widthModel": "sigma*sqrt(1+(2*alpha*t/sigma^2)^2)",
        },
    }
    return Trajectory.from_arrays(
        time=time,
        states=np.column_stack([centers, widths]),
        state_names=["center", "width"],
        metadata=metadata,
    )


def write_wave_packet(
    output: Path,
    *,
    viewer_output: Path | None = None,
) -> Trajectory:
    trajectory = generate_wave_packet()
    trajectory.write_json(output)
    if viewer_output is not None:
        trajectory.write_json(viewer_output)
    return trajectory


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate dispersive wave-packet field data.")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/generated/wave_packet.json"),
    )
    parser.add_argument(
        "--viewer-output",
        type=Path,
        default=Path("viewer/public/data/wave_packet.json"),
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> None:
    args = parse_args(argv)
    write_wave_packet(args.output, viewer_output=args.viewer_output)
    print(f"Wrote field data to {args.output}")


if __name__ == "__main__":
    main()
