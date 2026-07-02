from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

import numpy as np

from engine.export import SCALAR_FIELD_HINT, Trajectory
from scripts.generation import write_trajectory_outputs
from systems.scalar_field_density import build_system


DEFAULT_PARAMETERS = {
    "A": 0.35,
    "k": 1.25,
    "m": 1.0,
}


def _field_surface_payload(
    *,
    time: np.ndarray,
    x_axis: np.ndarray,
    values: np.ndarray,
) -> dict[str, object]:
    return {
        "kind": "scalar-field-series",
        "rendererHint": SCALAR_FIELD_HINT,
        "name": "fieldConfiguration",
        "coordinates": ["x"],
        "axes": [x_axis.astype(float).tolist()],
        "time": time.astype(float).tolist(),
        "shape": list(values.shape),
        "values": values.astype(float).tolist(),
        "evaluation": "analytic-on-shell-mode",
    }


def generate_scalar_field_density(
    *,
    time_count: int = 81,
    x_count: int = 73,
) -> Trajectory:
    if time_count < 3 or x_count < 3:
        raise ValueError("time_count and x_count must be at least 3")

    system = build_system()
    parameters = dict(DEFAULT_PARAMETERS)
    omega = float(
        system.angular_frequency.subs(
            {
                system.mass: parameters["m"],
                system.wavenumber: parameters["k"],
                system.amplitude: parameters["A"],
            }
        )
    )
    period = 2.0 * np.pi / omega
    wavelength = 2.0 * np.pi / parameters["k"]
    time = np.linspace(0.0, period, time_count)
    x_axis = np.linspace(-0.5 * wavelength, 0.5 * wavelength, x_count)
    values = system.field_values(time, x_axis, parameters=parameters)

    residual = system.density.measured_stress_energy_conservation_residual(
        system.configuration,
        (time, x_axis),
        parameter_values=parameters,
    )
    residual_payload = residual.to_dict()
    residual_payload["residualMaxAbs"] = float(np.max(np.abs(residual.values)))

    metadata = {
        "system": "scalar_field_density",
        "kind": "field-density",
        "parameters": {
            **parameters,
            "omega": omega,
        },
        "fieldDensity": system.manifest_metadata(),
        "fields": {
            "fieldConfiguration": _field_surface_payload(
                time=time,
                x_axis=x_axis,
                values=values,
            ),
        },
        "diagnostics": {
            "stressEnergyConservation": residual_payload,
        },
        "rendererHints": {
            "fieldSurface": "trajectory.metadata.fields.fieldConfiguration",
            "stressEnergyResidual": (
                "trajectory.metadata.diagnostics.stressEnergyConservation"
            ),
        },
    }
    return Trajectory.from_arrays(
        time=time,
        states=values,
        state_names=[f"phi_{index}" for index in range(x_count)],
        metadata=metadata,
    )


def write_scalar_field_density(
    output: Path,
    *,
    viewer_output: Path | None = None,
) -> Trajectory:
    trajectory = generate_scalar_field_density()
    return write_trajectory_outputs(trajectory, output, viewer_output)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate scalar field-density data.")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/generated/scalar_field_density.json"),
    )
    parser.add_argument(
        "--viewer-output",
        type=Path,
        default=Path("viewer/public/data/scalar_field_density.json"),
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> None:
    args = parse_args(argv)
    write_scalar_field_density(args.output, viewer_output=args.viewer_output)
    print(f"Wrote scalar field-density data to {args.output}")


if __name__ == "__main__":
    main()
