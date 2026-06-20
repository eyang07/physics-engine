from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

import numpy as np

from engine.dynamics import classify_kepler_orbit, kepler_effective_potential_values
from engine.export import Trajectory
from scripts.example_specs import KEPLER
from scripts.generation import (
    generate_lagrangian_trajectory,
    potential_plot_metadata,
    write_trajectory_outputs,
)
from systems.kepler_problem import build_system


def kepler_renderer_hints(states: np.ndarray) -> dict[str, object]:
    """Return scene metadata that describes how to frame the rendered orbit."""

    x = states[:, 4]
    y = states[:, 5]
    extent = float(max(np.max(np.abs(x)), np.max(np.abs(y)), 1.0))
    plane_radius = extent * 1.18
    ring_radii = np.linspace(plane_radius * 0.28, plane_radius * 0.9, 4)
    flow_radius = plane_radius * 0.9

    return {
        "bounds": {
            "x": [float(np.min(x)), float(np.max(x))],
            "y": [0.0, 0.0],
            "z": [float(np.min(y)), float(np.max(y))],
        },
        "camera": {
            "position": [plane_radius * 1.35, plane_radius * 0.9, plane_radius * 1.65],
            "target": [0.0, 0.0, 0.0],
        },
        "referenceGeometry": [
            {
                "kind": "centralBody",
                "position": [0.0, 0.0, 0.0],
                "radius": plane_radius * 0.061,
            },
            {
                "kind": "orbitalPlane",
                "radius": plane_radius,
            },
            {
                "kind": "radialRings",
                "radii": [float(radius) for radius in ring_radii],
            },
            {
                "kind": "centralForceSamples",
                "radii": [float(radius) for radius in np.linspace(flow_radius * 0.36, flow_radius, 3)],
                "angles": 8,
            },
        ],
        "flow": {
            "kind": "centralAttraction",
            "bounds": {
                "x": [-flow_radius, flow_radius],
                "z": [-flow_radius, flow_radius],
            },
        },
    }


def kepler_effective_potential_plot(
    *,
    trajectory: Trajectory,
    mass: float,
    gravitational_parameter: float,
) -> tuple[dict[str, object], dict[str, object]]:
    if trajectory.series is None or "H" not in trajectory.series or "ell" not in trajectory.series:
        raise ValueError("Kepler trajectory must carry H and ell series")
    energy = float(np.mean(np.asarray(trajectory.series["H"], dtype=float)))
    angular_momentum = float(np.mean(np.asarray(trajectory.series["ell"], dtype=float)))
    classification = classify_kepler_orbit(
        mass=mass,
        gravitational_parameter=gravitational_parameter,
        energy=energy,
        angular_momentum=angular_momentum,
    )
    r_values = trajectory.states[:, 0]
    positive_turning_points = list(classification.turning_points)
    r_min_candidates = [float(np.min(r_values)) * 0.75, *(0.8 * r for r in positive_turning_points)]
    r_max_candidates = [float(np.max(r_values)) * 1.25, *(1.2 * r for r in positive_turning_points)]
    r_min = max(0.04, min(r_min_candidates))
    r_max = max(r_max_candidates)
    coordinate_values = np.linspace(r_min, r_max, 320)
    potential_values = kepler_effective_potential_values(
        coordinate_values,
        mass=mass,
        gravitational_parameter=gravitational_parameter,
        angular_momentum=angular_momentum,
    )
    plot = potential_plot_metadata(
        name="kepler_radial",
        coordinate="r",
        coordinate_latex="r",
        coordinate_values=coordinate_values,
        potential_values=potential_values,
        energy_series=trajectory.series["H"],
        potential_latex=r"V_{\mathrm{eff}}",
    )
    plot.update(
        {
            "rendererHint": "effective-potential",
            "angularMomentum": angular_momentum,
            "turningPoints": positive_turning_points,
            "classification": classification.classification,
            "evaluation": classification.evaluation,
        }
    )
    return plot, classification.to_dict()


def generate_kepler_trajectory(
    *,
    mass: float = 1.0,
    gravitational_parameter: float = 1.0,
    initial_state: Sequence[float] = (1.0, 0.0, 0.0, 1.05),
    t_span: tuple[float, float] = (0.0, 24.0),
    dt: float = 0.01,
) -> Trajectory:
    system = build_system(mass=mass, gravitational_parameter=gravitational_parameter)
    trajectory = generate_lagrangian_trajectory(
        spec=KEPLER,
        system=system,
        initial_state=initial_state,
        t_span=t_span,
        dt=dt,
        state_names=["r", "phi", "r_dot", "phi_dot", "x", "y"],
        physical_parameters={"m": mass, "mu": gravitational_parameter},
        metadata={
            "system": "kepler_problem",
            "mass": mass,
            "gravitational_parameter": gravitational_parameter,
        },
        state_transform=lambda _time, intrinsic_states: np.column_stack(
            [
                intrinsic_states,
                intrinsic_states[:, 0] * np.cos(intrinsic_states[:, 1]),
                intrinsic_states[:, 0] * np.sin(intrinsic_states[:, 1]),
            ]
        ),
    )
    metadata = dict(trajectory.metadata or {})
    metadata["rendererHints"] = kepler_renderer_hints(trajectory.states)
    potential_plot, orbit_classification = kepler_effective_potential_plot(
        trajectory=trajectory,
        mass=mass,
        gravitational_parameter=gravitational_parameter,
    )
    metadata["potentialPlots"] = [potential_plot]
    metadata["orbitClassification"] = orbit_classification
    return Trajectory.from_arrays(
        time=trajectory.time,
        states=trajectory.states,
        state_names=trajectory.state_names,
        metadata=metadata,
        series=trajectory.series,
    )


def write_kepler_trajectory(
    output: Path,
    *,
    viewer_output: Path | None = None,
) -> Trajectory:
    trajectory = generate_kepler_trajectory()
    return write_trajectory_outputs(trajectory, output, viewer_output)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate Kepler problem orbit data.")
    parser.add_argument("--output", type=Path, default=Path("data/generated/kepler_problem.json"))
    parser.add_argument("--viewer-output", type=Path, default=Path("viewer/public/data/kepler_problem.json"))
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> None:
    args = parse_args(argv)
    write_kepler_trajectory(args.output, viewer_output=args.viewer_output)
    print(f"Wrote trajectory to {args.output}")


if __name__ == "__main__":
    main()
