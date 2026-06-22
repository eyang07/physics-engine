from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

import numpy as np

from engine.dynamics import (
    classify_schwarzschild_orbit,
    schwarzschild_effective_potential_values,
    schwarzschild_equatorial_metric,
)
from engine.export import Trajectory
from engine.numerics import integrate_fixed_step
from scripts.generation import invariant_residual_records, write_trajectory_outputs
from systems.schwarzschild import (
    SchwarzschildGeodesicKind,
    assert_outside_horizon,
    build_system,
    conserved_series,
    domain_assumptions,
    embedding_xy,
    flamm_embedding_z,
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


def _embedding_mesh_axes(
    *,
    schwarzschild_radius: float,
    max_radius: float,
    r_count: int = 72,
    phi_count: int = 64,
) -> tuple[np.ndarray, np.ndarray]:
    """Shared ``(r, phi)`` sampling for the Flamm mesh and its curvature field.

    The radial axis starts just outside the horizon so the funnel throat is
    sampled while the mesh stays strictly in the exterior chart ``r > r_s``, and
    extends past the geodesic so the orbit sits on the rendered surface. The
    curvature grid reuses this axis so it aligns vertex-for-vertex with the mesh
    the viewer colors.
    """

    r_lower = schwarzschild_radius * 1.001
    r_upper = max(max_radius * 1.15, schwarzschild_radius * 6.0)
    r_axis = np.linspace(r_lower, r_upper, r_count)
    phi_axis = np.linspace(0.0, 2.0 * np.pi, phi_count)
    return r_axis, phi_axis


def _embedding_mesh(
    *,
    schwarzschild_radius: float,
    max_radius: float,
    r_count: int = 72,
    phi_count: int = 64,
) -> dict[str, object]:
    """Flamm-paraboloid embedding mesh of the exterior equatorial slice.

    The surface of revolution ``(r cos phi, r sin phi, z(r))`` with
    ``z(r) = 2 sqrt(r_s (r - r_s))`` is the exact isometric embedding of the
    exterior spatial slice; the points are deterministic given the axes, not
    measured numerical evidence.
    """

    r_axis, phi_axis = _embedding_mesh_axes(
        schwarzschild_radius=schwarzschild_radius,
        max_radius=max_radius,
        r_count=r_count,
        phi_count=phi_count,
    )
    r_grid, phi_grid = np.meshgrid(r_axis, phi_axis, indexing="ij")
    z = flamm_embedding_z(r_grid, schwarzschild_radius=schwarzschild_radius)
    points = np.stack(
        [r_grid * np.cos(phi_grid), r_grid * np.sin(phi_grid), z], axis=-1
    )
    triangles: list[list[int]] = []
    for r_index in range(r_count - 1):
        for phi_index in range(phi_count - 1):
            lower_left = r_index * phi_count + phi_index
            lower_right = lower_left + 1
            upper_left = lower_left + phi_count
            upper_right = upper_left + 1
            triangles.append([lower_left, upper_left, lower_right])
            triangles.append([lower_right, upper_left, upper_right])
    return {
        "kind": "surface-mesh",
        "rendererHint": "schwarzschild-geodesic",
        "coordinates": ["r", "phi"],
        "axes": [r_axis.astype(float).tolist(), phi_axis.astype(float).tolist()],
        "shape": [r_count, phi_count],
        "points": points.astype(float).tolist(),
        "triangles": triangles,
        "horizonRadius": float(schwarzschild_radius),
        "evaluation": "symbolic-exact",
    }


def _embedding_curvature_field(
    *,
    schwarzschild_radius: float,
    max_radius: float,
    r_count: int = 72,
    phi_count: int = 64,
) -> dict[str, object]:
    """Kretschmann scalar samples aligned to the Flamm embedding mesh.

    The Schwarzschild spacetime is vacuum, so the Ricci scalar vanishes and the
    Kretschmann invariant ``R_abcd R^abcd = 12 r_s^2 / r^6`` is the curvature
    used to color the funnel. The values depend only on ``r`` and are broadcast
    across ``phi`` to match the mesh grid; they are exact symbolic evaluations,
    extremal at the throat and decaying outward.
    """

    r_axis, phi_axis = _embedding_mesh_axes(
        schwarzschild_radius=schwarzschild_radius,
        max_radius=max_radius,
        r_count=r_count,
        phi_count=phi_count,
    )
    r_grid, _phi_grid = np.meshgrid(r_axis, phi_axis, indexing="ij")
    values = kretschmann_scalar_values(
        r_grid, schwarzschild_radius=schwarzschild_radius
    )
    return {
        "kind": "scalar-field",
        "rendererHint": "scalar-field",
        "name": "kretschmannScalar",
        "coordinates": ["r", "phi"],
        "axes": [r_axis.astype(float).tolist(), phi_axis.astype(float).tolist()],
        "shape": [r_count, phi_count],
        "values": values.astype(float).tolist(),
        "quantity": "Kretschmann scalar",
        "horizon": {
            "r": float(schwarzschild_radius),
            "kretschmannScalar": float(values[0, 0]),
            "description": "curvature peaks near the horizon and decays as r^-6",
        },
        "evaluation": "symbolic-exact",
    }


def _schwarzschild_geometry(
    intrinsic_states: np.ndarray,
    positions: np.ndarray,
    *,
    schwarzschild_radius: float,
) -> dict[str, object]:
    """Funnel embedding mesh, curvature field, and the geodesic on the funnel."""

    max_radius = float(np.max(intrinsic_states[:, 1]))
    funnel_z = flamm_embedding_z(
        intrinsic_states[:, 1], schwarzschild_radius=schwarzschild_radius
    )
    geodesic_points = np.column_stack([positions, funnel_z])
    return {
        "kind": "schwarzschild-geodesic",
        "rendererHint": "schwarzschild-geodesic",
        "schwarzschildRadius": schwarzschild_radius,
        "embeddingMesh": _embedding_mesh(
            schwarzschild_radius=schwarzschild_radius, max_radius=max_radius
        ),
        "curvature": _embedding_curvature_field(
            schwarzschild_radius=schwarzschild_radius, max_radius=max_radius
        ),
        "geodesic": {
            "kind": "embedded-polyline",
            "rendererHint": "schwarzschild-geodesic",
            "coordinates": ["x", "y", "z"],
            "source": "trajectory.metadata.schwarzschildGeometry.geodesic",
            "points": geodesic_points.astype(float).tolist(),
            "evaluation": "integrated-geodesic-embedding",
        },
    }


def _geodesic_deviation_payload(
    time: np.ndarray,
    intrinsic_states: np.ndarray,
    *,
    schwarzschild_radius: float,
    azimuthal_offset: float = 0.03,
) -> dict[str, object]:
    """Measured tidal separation between the bound orbit and a nearby geodesic.

    A neighbor launched from the same state but offset slightly in the azimuthal
    angle ``phi`` traces a congruent bound orbit; the metric separation breathes
    with the radius, converging at periapsis and diverging toward apoapsis. The
    reduction reuses ``MetricGeometry.geodesic_deviation_diagnostic`` on the
    equatorial Schwarzschild metric and is a finite-rollout diagnostic, not a
    symbolic Jacobi-field proof.
    """

    initial = intrinsic_states[0].copy()
    initial[2] += azimuthal_offset
    system = build_system(schwarzschild_radius=schwarzschild_radius)
    _neighbor_time, neighboring = integrate_fixed_step(
        system.numerical_rhs(),
        initial_state=initial,
        t_span=(float(time[0]), float(time[-1])),
        dt=float(time[1] - time[0]),
    )
    assert_outside_horizon(
        neighboring[:, 1],
        schwarzschild_radius=schwarzschild_radius,
        context="timelike Schwarzschild neighbor geodesic",
    )
    payload = schwarzschild_equatorial_metric(
        schwarzschild_radius
    ).geodesic_deviation_diagnostic(time, intrinsic_states, neighboring)
    payload["neighborInitialOffset"] = {"phi": azimuthal_offset}
    return payload


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

    domain = domain_assumptions(schwarzschild_radius=schwarzschild_radius)
    assert_outside_horizon(
        [initial_state[1]],
        schwarzschild_radius=schwarzschild_radius,
        context=f"{kind} Schwarzschild initial state",
    )
    system = build_system(schwarzschild_radius=schwarzschild_radius)
    time, intrinsic_states = integrate_fixed_step(
        system.numerical_rhs(),
        initial_state=initial_state,
        t_span=span,
        dt=step,
    )
    assert_outside_horizon(
        intrinsic_states[:, 1],
        schwarzschild_radius=schwarzschild_radius,
        context=f"{kind} Schwarzschild geodesic",
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
        diagnostics["geodesicDeviation"] = _geodesic_deviation_payload(
            time,
            intrinsic_states,
            schwarzschild_radius=schwarzschild_radius,
        )
    else:
        diagnostics["lightBending"] = null_light_bending(
            schwarzschild_radius=schwarzschild_radius,
            impact_parameter=impact_parameter,
        )

    metadata = {
        "system": "schwarzschild",
        "kind": kind,
        "schwarzschildRadius": schwarzschild_radius,
        "domain": domain,
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
        "schwarzschildGeometry": _schwarzschild_geometry(
            intrinsic_states,
            positions,
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
