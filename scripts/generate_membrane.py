from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

import numpy as np

from engine.export import Trajectory
from systems.membrane import (
    CircularMode,
    RectangularMode,
    build_system,
    circular_mode_values,
    circular_superposition,
    rectangular_mode_values,
    rectangular_superposition,
)


DEFAULT_PARAMETERS = {
    "Lx": 1.4,
    "Ly": 1.0,
    "R": 1.0,
    "c": 1.0,
}


def _grid_payload(
    *,
    name: str,
    coordinates: Sequence[str],
    axes: Sequence[np.ndarray],
    values: np.ndarray,
    time: np.ndarray | None = None,
    variant: str,
) -> dict[str, object]:
    finite = np.isfinite(values)
    payload: dict[str, object] = {
        "kind": "scalar-field" if time is None else "scalar-field-series",
        "rendererHint": "scalar-field",
        "name": name,
        "coordinates": list(coordinates),
        "axes": [axis.astype(float).tolist() for axis in axes],
        "shape": list(values.shape),
        "values": np.where(finite, values, 0.0).astype(float).tolist(),
        "finiteMask": finite.tolist(),
        "variant": variant,
        "evaluation": "analytic-exact",
    }
    if time is not None:
        payload["time"] = time.astype(float).tolist()
    return payload


def generate_membrane(
    *,
    rectangular_x_count: int = 45,
    rectangular_y_count: int = 35,
    circular_count: int = 49,
    time_count: int = 81,
) -> Trajectory:
    if rectangular_x_count < 3 or rectangular_y_count < 3 or circular_count < 3:
        raise ValueError("grid counts must be at least 3")
    if time_count < 2:
        raise ValueError("time_count must be at least 2")

    system = build_system()
    parameters = dict(DEFAULT_PARAMETERS)
    x_rect = np.linspace(0.0, parameters["Lx"], rectangular_x_count)
    y_rect = np.linspace(0.0, parameters["Ly"], rectangular_y_count)
    xy_circle = np.linspace(-parameters["R"], parameters["R"], circular_count)
    time = np.linspace(0.0, 2.0, time_count)

    rect_modes = [
        (RectangularMode(1, 1), 0.16),
        (RectangularMode(2, 1), 0.07),
        (RectangularMode(1, 2), 0.045),
    ]
    circ_modes = [
        (CircularMode(0, 1), 0.14),
        (CircularMode(1, 1), 0.055),
    ]

    rectangular_series = rectangular_superposition(
        system,
        rect_modes,
        x_rect,
        y_rect,
        time,
        parameters=parameters,
    )
    circular_series = circular_superposition(
        system,
        circ_modes,
        xy_circle,
        xy_circle,
        time,
        parameters=parameters,
    )

    fields = {
        "rectangularMode11": _grid_payload(
            name="rectangularMode11",
            coordinates=("x", "y"),
            axes=(x_rect, y_rect),
            values=rectangular_mode_values(
                system, RectangularMode(1, 1), x_rect, y_rect, parameters=parameters
            ),
            variant="rectangular-fixed-fixed-mode",
        ),
        "circularMode01": _grid_payload(
            name="circularMode01",
            coordinates=("x", "y"),
            axes=(xy_circle, xy_circle),
            values=circular_mode_values(
                system, CircularMode(0, 1), xy_circle, xy_circle, parameters=parameters
            ),
            variant="circular-dirichlet-bessel-mode",
        ),
        "rectangularDisplacement": _grid_payload(
            name="rectangularDisplacement",
            coordinates=("x", "y"),
            axes=(x_rect, y_rect),
            values=rectangular_series,
            time=time,
            variant="rectangular-modal-superposition",
        ),
        "circularDisplacement": _grid_payload(
            name="circularDisplacement",
            coordinates=("x", "y"),
            axes=(xy_circle, xy_circle),
            values=circular_series,
            time=time,
            variant="circular-bessel-modal-superposition",
        ),
    }

    metadata = {
        "system": "membrane",
        "kind": "field-evolution",
        "parameters": parameters,
        "fields": fields,
    }
    centerline = rectangular_series[:, :, rectangular_y_count // 2]
    return Trajectory.from_arrays(
        time=time,
        states=centerline,
        state_names=[f"u_{index}" for index in range(rectangular_x_count)],
        metadata=metadata,
    )


def write_membrane(
    output: Path,
    *,
    viewer_output: Path | None = None,
) -> Trajectory:
    trajectory = generate_membrane()
    trajectory.write_json(output)
    if viewer_output is not None:
        trajectory.write_json(viewer_output)
    return trajectory


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate membrane mode field data.")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/generated/membrane.json"),
    )
    parser.add_argument(
        "--viewer-output",
        type=Path,
        default=Path("viewer/public/data/membrane.json"),
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> None:
    args = parse_args(argv)
    write_membrane(args.output, viewer_output=args.viewer_output)
    print(f"Wrote field data to {args.output}")


if __name__ == "__main__":
    main()
