from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

import numpy as np

from engine.dynamics import (
    classify_schwarzschild_orbit,
    schwarzschild_effective_potential_values,
)
from engine.export import Trajectory
from engine.numerics import integrate_fixed_step
from scripts.generation import invariant_residual_records, write_trajectory_outputs
from systems.schwarzschild import (
    SchwarzschildGeodesicKind,
    build_system,
    conserved_series,
    embedding_xy,
    kretschmann_scalar_values,
    null_light_bending,
    null_scattering_initial_state,
    periapsis_precession,
    ricci_scalar_values,
    timelike_bound_constants,
    timelike_bound_initial_state,
    weak_field_precession,
)


def schwarzschild_renderer_hints(states: np.ndarray, *, schwarzschild_radius: float) -> dict[str, object]:
    positions = states[:, 6:8]
    extent = float(max(np.max(np.abs(positions)), 4.0 * schwarzschild_radius))
    return {
        "bounds": {
            "x": [-extent, extent],
            "y": [0.0, 0.0],
            "z": [-extent, extent],
        },
        "camera": {
            "position": [1.25 * extent, 0.9 * extent, 1.5 * extent],
            "target": [0.0, 0.0, 0.0],
        },
        "referenceGeometry": [
            {
                "kind": "eventHorizon",
                "radius": schwarzschild_radius,
            },
            {
                "kind": "photonSphere",
                "radius": 1.5 * schwarzschild_radius,
            },
        ],
    }


def _potential_plot(
    *,
    radius_values: np.ndarray,
    schwarzschild_radius: float,
    energy: float,
    angular_momentum: float,
    kind: SchwarzschildGeodesicKind,
) -> tuple[dict[str, object], dict[str, object]]:
    classification = classify_schwarzschild_orbit(
        schwarzschild_radius=schwarzschild_radius,
        energy=energy,
        angular_momentum=angular_momentum,
        kind=kind,
    )
    turning_points = list(classification.turning_points)
    lower = max(schwarzschild_radius * 1.02, float(np.min(radius_values)) * 0.75)
    upper = max(float(np.max(radius_values)) * 1.2, *(1.1 * root for root in turning_points))
    coordinate_values = np.linspace(lower, upper, 360)
    potential_values = schwarzschild_effective_potential_values(
        coordinate_values,
        schwarzschild_radius=schwarzschild_radius,
        angular_momentum=angular_momentum,
        kind=kind,
    )
    return (
        {
            "name": "schwarzschild_radial",
            "coordinate": "r",
            "coordinateLatex": "r",
            "potentialLatex": r"V_{\mathrm{eff}}^2",
            "coordinateValues": coordinate_values.astype(float).tolist(),
            "potentialValues": potential_values.astype(float).tolist(),
            "energy": float(energy**2),
            "energyKind": "specific-energy-squared",
            "angularMomentum": float(angular_momentum),
            "turningPoints": turning_points,
            "classification": classification.classification,
            "rendererHint": "effective-potential",
            "evaluation": classification.evaluation,
        },
        classification.to_dict(),
    )


def _curvature_scalar_fields(
    *,
    radius_values: np.ndarray,
    schwarzschild_radius: float,
) -> dict[str, object]:
    lower = max(schwarzschild_radius * 1.02, float(np.min(radius_values)) * 0.75)
    upper = float(np.max(radius_values)) * 1.2
    coordinate_values = np.linspace(lower, upper, 360)
    return {
        "ricciScalar": {
            "kind": "scalar-field",
            "rendererHint": "scalar-field",
            "name": "ricciScalar",
            "coordinates": ["r"],
            "axes": [coordinate_values.astype(float).tolist()],
            "shape": [int(len(coordinate_values))],
            "values": ricci_scalar_values(
                coordinate_values,
                schwarzschild_radius=schwarzschild_radius,
            ).astype(float).tolist(),
            "quantity": "Ricci scalar",
            "evaluation": "symbolic-exact",
        },
        "kretschmannScalar": {
            "kind": "scalar-field",
            "rendererHint": "scalar-field",
            "name": "kretschmannScalar",
            "coordinates": ["r"],
            "axes": [coordinate_values.astype(float).tolist()],
            "shape": [int(len(coordinate_values))],
            "values": kretschmann_scalar_values(
                coordinate_values,
                schwarzschild_radius=schwarzschild_radius,
            ).astype(float).tolist(),
            "quantity": "Kretschmann scalar",
            "evaluation": "symbolic-exact",
        },
    }


def generate_schwarzschild_trajectory(
    *,
    kind: SchwarzschildGeodesicKind = "timelike",
    schwarzschild_radius: float = 2.0,
    semi_latus_rectum: float = 40.0,
    eccentricity: float = 0.1,
    impact_parameter: float = 30.0,
    start_radius: float = 300.0,
    t_span: tuple[float, float] | None = None,
    dt: float | None = None,
) -> Trajectory:
    if kind == "timelike":
        initial_state = timelike_bound_initial_state(
            schwarzschild_radius=schwarzschild_radius,
            semi_latus_rectum=semi_latus_rectum,
            eccentricity=eccentricity,
        )
        energy, angular_momentum = timelike_bound_constants(
            semi_latus_rectum=semi_latus_rectum,
            eccentricity=eccentricity,
            mass_parameter=schwarzschild_radius / 2.0,
        )
        span = t_span or (0.0, 5000.0)
        step = 0.2 if dt is None else dt
    elif kind == "null":
        initial_state = null_scattering_initial_state(
            schwarzschild_radius=schwarzschild_radius,
            impact_parameter=impact_parameter,
            start_radius=start_radius,
        )
        energy, angular_momentum = 1.0, impact_parameter
        span = t_span or (0.0, 750.0)
        step = 0.1 if dt is None else dt
    else:
        raise ValueError(f"unknown Schwarzschild geodesic kind: {kind!r}")

    system = build_system(schwarzschild_radius=schwarzschild_radius)
    time, intrinsic_states = integrate_fixed_step(
        system.numerical_rhs(),
        initial_state=initial_state,
        t_span=span,
        dt=step,
    )
    positions = embedding_xy(intrinsic_states)
    states = np.column_stack([intrinsic_states, positions])
    series = conserved_series(intrinsic_states, schwarzschild_radius=schwarzschild_radius)
    potential_plot, classification = _potential_plot(
        radius_values=intrinsic_states[:, 1],
        schwarzschild_radius=schwarzschild_radius,
        energy=energy,
        angular_momentum=angular_momentum,
        kind=kind,
    )
    diagnostics: dict[str, object] = {}
    if kind == "timelike":
        precession = periapsis_precession(intrinsic_states)
        precession["weakFieldPrediction"] = weak_field_precession(
            semi_latus_rectum=semi_latus_rectum
        )
        diagnostics["perihelionPrecession"] = precession
    else:
        diagnostics["lightBending"] = null_light_bending(
            schwarzschild_radius=schwarzschild_radius,
            impact_parameter=impact_parameter,
        )

    metadata = {
        "system": "schwarzschild",
        "kind": kind,
        "schwarzschildRadius": schwarzschild_radius,
        "parameters": {
            "r_s": schwarzschild_radius,
            "semi_latus_rectum": semi_latus_rectum,
            "eccentricity": eccentricity,
            "impact_parameter": impact_parameter,
        },
        "rendererHints": schwarzschild_renderer_hints(
            states,
            schwarzschild_radius=schwarzschild_radius,
        ),
        "potentialPlots": [potential_plot],
        "orbitClassification": classification,
        "curvatureScalars": _curvature_scalar_fields(
            radius_values=intrinsic_states[:, 1],
            schwarzschild_radius=schwarzschild_radius,
        ),
        "diagnostics": diagnostics,
        "invariantResiduals": invariant_residual_records(series),
    }
    return Trajectory.from_arrays(
        time=time,
        states=states,
        state_names=("t", "r", "phi", "t_dot", "r_dot", "phi_dot", "x", "y"),
        metadata=metadata,
        series=series,
    )


def write_schwarzschild_trajectory(
    output: Path,
    *,
    viewer_output: Path | None = None,
    kind: SchwarzschildGeodesicKind = "timelike",
) -> Trajectory:
    trajectory = generate_schwarzschild_trajectory(kind=kind)
    return write_trajectory_outputs(trajectory, output, viewer_output)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate Schwarzschild geodesic data.")
    parser.add_argument("--output", type=Path, default=Path("data/generated/schwarzschild.json"))
    parser.add_argument(
        "--viewer-output",
        type=Path,
        default=Path("viewer/public/data/schwarzschild.json"),
    )
    parser.add_argument("--kind", choices=("timelike", "null"), default="timelike")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> None:
    args = parse_args(argv)
    trajectory = write_schwarzschild_trajectory(
        args.output,
        viewer_output=args.viewer_output,
        kind=args.kind,
    )
    print(f"Wrote {len(trajectory.time)} samples to {args.output}")
    if args.viewer_output is not None:
        print(f"Wrote viewer copy to {args.viewer_output}")


if __name__ == "__main__":
    main()
