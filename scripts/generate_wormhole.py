from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

import numpy as np
import sympy as sp

from engine.export import Trajectory
from engine.numerics import integrate_fixed_step
from scripts.generation import invariant_residual_records, write_trajectory_outputs
from systems.wormhole import (
    WormholeGeodesicKind,
    build_system,
    classify_radial_geodesic,
    conserved_constants,
    conserved_series,
    domain_assumptions,
    ellis_wormhole_metric,
    embedding_xyz,
    geodesic_kind_from_norm,
    radial_effective_potential_values,
    radial_throat_initial_state,
)


def _mesh_axes(
    throat_radius: float,
    *,
    l_count: int = 73,
    phi_count: int = 65,
) -> tuple[np.ndarray, np.ndarray]:
    """Shared (l, phi) sampling for the embedding mesh and the curvature field.

    The proper radial axis is symmetric about the throat with an odd point count,
    so ``l = 0`` (proper radius ``a``) — where the curvature is extremal — is
    always one of the samples, and the curvature grid aligns vertex-for-vertex
    with the embedding mesh the viewer colors.
    """

    l_axis = np.linspace(-6.5 * throat_radius, 6.5 * throat_radius, l_count)
    phi_axis = np.linspace(0.0, 2.0 * np.pi, phi_count)
    return l_axis, phi_axis


def _wormhole_mesh(throat_radius: float, *, l_count: int = 73, phi_count: int = 65) -> dict[str, object]:
    l_axis, phi_axis = _mesh_axes(throat_radius, l_count=l_count, phi_count=phi_count)
    l_grid, phi_grid = np.meshgrid(l_axis, phi_axis, indexing="ij")
    rho = np.sqrt(l_grid**2 + throat_radius**2)
    z = throat_radius * np.arcsinh(l_grid / throat_radius)
    points = np.stack([rho * np.cos(phi_grid), rho * np.sin(phi_grid), z], axis=-1)
    triangles: list[list[int]] = []
    for l_index in range(l_count - 1):
        for phi_index in range(phi_count - 1):
            lower_left = l_index * phi_count + phi_index
            lower_right = lower_left + 1
            upper_left = lower_left + phi_count
            upper_right = upper_left + 1
            triangles.append([lower_left, upper_left, lower_right])
            triangles.append([lower_right, upper_left, upper_right])
    return {
        "kind": "surface-mesh",
        "rendererHint": "wormhole-geodesic",
        "coordinates": ["l", "phi"],
        "axes": [l_axis.astype(float).tolist(), phi_axis.astype(float).tolist()],
        "shape": [l_count, phi_count],
        "points": points.astype(float).tolist(),
        "triangles": triangles,
        "evaluation": "symbolic-exact",
    }


def _curvature_field(throat_radius: float, *, l_count: int = 73, phi_count: int = 65) -> dict[str, object]:
    """Scalar-curvature samples of the Ellis background over the throat grid.

    The values are exact samples of ``MetricGeometry.scalar_curvature()`` for the
    fixed background — deterministic given the axes, not measured numerical
    evidence — so the viewer can color the throat mesh from Python-owned data.
    The Ellis scalar curvature ``R = -2 a^2 / (a^2 + l^2)^2`` depends only on the
    proper radial coordinate ``l``; it is broadcast across ``phi`` to match the
    embedding-mesh grid, and is extremal at the throat (``l = 0``, ``R = -2/a^2``).
    """

    geometry = ellis_wormhole_metric(throat_radius)
    _t, ell, phi = geometry.coordinates
    scalar = geometry.scalar_curvature()
    function = sp.lambdify((ell, phi), scalar, modules="numpy")

    l_axis, phi_axis = _mesh_axes(throat_radius, l_count=l_count, phi_count=phi_count)
    l_grid, phi_grid = np.meshgrid(l_axis, phi_axis, indexing="ij")
    values = np.broadcast_to(
        np.asarray(function(l_grid, phi_grid), dtype=float),
        l_grid.shape,
    ).astype(float)

    throat_index = int(np.argmin(np.abs(l_axis)))
    return {
        "kind": "scalar-field",
        "rendererHint": "scalar-field",
        "name": "scalarCurvature",
        "coordinates": ["l", "phi"],
        "axes": [l_axis.astype(float).tolist(), phi_axis.astype(float).tolist()],
        "shape": [l_count, phi_count],
        "values": values.tolist(),
        "quantity": "scalar curvature",
        "throat": {
            "l": float(l_axis[throat_index]),
            "scalarCurvature": float(values[throat_index, 0]),
            "description": "curvature extremum at the throat (proper radius a)",
        },
        "evaluation": "symbolic-exact",
    }


def _potential_plot(
    *,
    l_values: np.ndarray,
    throat_radius: float,
    energy: float,
    angular_momentum: float,
    kind: WormholeGeodesicKind,
) -> tuple[dict[str, object], dict[str, object]]:
    """Radial effective potential over ``l`` plus its turning-point classification.

    The plot samples ``V_eff^2(l) = epsilon + L^2/(l^2 + a^2)`` symmetrically about
    the throat (``l = 0`` is always sampled) so the viewer can draw the throat
    barrier, the conserved ``E^2`` level, and any turning points without
    re-deriving the reduction.
    """

    reduction = classify_radial_geodesic(
        throat_radius=throat_radius,
        energy=energy,
        angular_momentum=angular_momentum,
        kind=kind,
    )
    turning_points = list(reduction.turning_points)
    extent = max(
        float(np.max(np.abs(l_values))) * 1.1,
        3.0 * throat_radius,
        *(1.2 * abs(point) for point in turning_points),
    )
    coordinate_values = np.linspace(-extent, extent, 361)
    potential_values = radial_effective_potential_values(
        coordinate_values,
        throat_radius=throat_radius,
        angular_momentum=angular_momentum,
        kind=kind,
    )
    return (
        {
            "name": "wormhole_radial",
            "coordinate": "l",
            "coordinateLatex": "l",
            "potentialLatex": r"V_{\mathrm{eff}}^2",
            "coordinateValues": coordinate_values.astype(float).tolist(),
            "potentialValues": potential_values.astype(float).tolist(),
            "energy": float(energy**2),
            "energyKind": "specific-energy-squared",
            "angularMomentum": float(angular_momentum),
            "throatBarrier": reduction.throat_barrier,
            "turningPoints": turning_points,
            "classification": reduction.classification,
            "rendererHint": "effective-potential",
            "evaluation": reduction.evaluation,
        },
        reduction.to_dict(),
    )


def _renderer_hints(states: np.ndarray, *, throat_radius: float) -> dict[str, object]:
    positions = states[:, 6:9]
    extent = float(max(np.max(np.abs(positions)), 2.0 * throat_radius))
    return {
        "bounds": {
            "x": [-extent, extent],
            "y": [-extent, extent],
            "z": [float(np.min(positions[:, 2])), float(np.max(positions[:, 2]))],
        },
        "camera": {
            "position": [1.4 * extent, -1.6 * extent, 0.8 * extent],
            "target": [0.0, 0.0, 0.0],
        },
        "referenceGeometry": [
            {
                "kind": "wormholeThroat",
                "radius": throat_radius,
            }
        ],
    }


def _throat_traversal(time: np.ndarray, intrinsic_states: np.ndarray) -> dict[str, object]:
    ell = intrinsic_states[:, 1]
    crossing_time = None
    for index in range(len(ell) - 1):
        left = float(ell[index])
        right = float(ell[index + 1])
        if left == 0.0:
            crossing_time = float(time[index])
            break
        if left * right < 0.0:
            fraction = -left / (right - left)
            crossing_time = float(time[index] + fraction * (time[index + 1] - time[index]))
            break
    return {
        "kind": "throat-traversal",
        "crossesThroat": crossing_time is not None,
        "crossingTime": crossing_time,
        "minAbsL": float(np.min(np.abs(ell))),
        "initialL": float(ell[0]),
        "finalL": float(ell[-1]),
        "evaluation": "measured-rollout-throat-crossing",
        "rigor": "measured",
    }


def _geodesic_deviation_payload(
    time: np.ndarray,
    intrinsic_states: np.ndarray,
    *,
    throat_radius: float,
) -> dict[str, object]:
    initial = intrinsic_states[0].copy()
    initial[2] += 0.03
    system = build_system(throat_radius=throat_radius)
    _neighbor_time, neighboring = integrate_fixed_step(
        system.numerical_rhs(),
        initial_state=initial,
        t_span=(float(time[0]), float(time[-1])),
        dt=float(time[1] - time[0]),
    )
    payload = ellis_wormhole_metric(throat_radius).geodesic_deviation_diagnostic(
        time,
        intrinsic_states,
        neighboring,
    )
    payload["neighborInitialOffset"] = {"phi": 0.03}
    return payload


def generate_wormhole_trajectory(
    *,
    throat_radius: float = 1.0,
    initial_l: float = -6.0,
    l_dot: float = 0.4,
    t_span: tuple[float, float] = (0.0, 32.0),
    dt: float = 0.02,
) -> Trajectory:
    domain = domain_assumptions(throat_radius=throat_radius)
    system = build_system(throat_radius=throat_radius)
    time, intrinsic_states = integrate_fixed_step(
        system.numerical_rhs(),
        initial_state=radial_throat_initial_state(
            throat_radius=throat_radius,
            start_l=initial_l,
            l_dot=l_dot,
        ),
        t_span=t_span,
        dt=dt,
    )
    positions = embedding_xyz(intrinsic_states, throat_radius=throat_radius)
    states = np.column_stack([intrinsic_states, positions])
    series = conserved_series(intrinsic_states, throat_radius=throat_radius)
    energy, angular_momentum = conserved_constants(
        intrinsic_states[0], throat_radius=throat_radius
    )
    kind = geodesic_kind_from_norm(series["metricNorm"][0])
    potential_plot, classification = _potential_plot(
        l_values=intrinsic_states[:, 1],
        throat_radius=throat_radius,
        energy=energy,
        angular_momentum=angular_momentum,
        kind=kind,
    )
    metadata = {
        "system": "ellis_wormhole",
        "kind": "fixed-background",
        "throatRadius": throat_radius,
        "domain": domain,
        "rendererHints": _renderer_hints(states, throat_radius=throat_radius),
        "potentialPlots": [potential_plot],
        "orbitClassification": classification,
        "wormholeGeometry": {
            "kind": "wormhole-geodesic",
            "rendererHint": "wormhole-geodesic",
            "throatRadius": throat_radius,
            "embeddingMesh": _wormhole_mesh(throat_radius),
            "curvature": _curvature_field(throat_radius),
            "geodesic": {
                "kind": "embedded-polyline",
                "rendererHint": "wormhole-geodesic",
                "coordinates": ["x", "y", "z"],
                "source": "trajectory.states[x,y,z]",
                "points": positions.astype(float).tolist(),
                "evaluation": "integrated-geodesic-embedding",
            },
        },
        "diagnostics": {
            "throatTraversal": _throat_traversal(time, intrinsic_states),
            "geodesicDeviation": _geodesic_deviation_payload(
                time,
                intrinsic_states,
                throat_radius=throat_radius,
            ),
        },
        "invariantResiduals": invariant_residual_records(series),
    }
    return Trajectory.from_arrays(
        time=time,
        states=states,
        state_names=("t", "l", "phi", "t_dot", "l_dot", "phi_dot", "x", "y", "z"),
        metadata=metadata,
        series=series,
    )


def write_wormhole_trajectory(
    output: Path,
    *,
    viewer_output: Path | None = None,
) -> Trajectory:
    trajectory = generate_wormhole_trajectory()
    return write_trajectory_outputs(trajectory, output, viewer_output)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate Ellis wormhole geodesic data.")
    parser.add_argument("--output", type=Path, default=Path("data/generated/wormhole.json"))
    parser.add_argument(
        "--viewer-output",
        type=Path,
        default=Path("viewer/public/data/wormhole.json"),
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> None:
    args = parse_args(argv)
    trajectory = write_wormhole_trajectory(args.output, viewer_output=args.viewer_output)
    print(f"Wrote {len(trajectory.time)} samples to {args.output}")
    if args.viewer_output is not None:
        print(f"Wrote viewer copy to {args.viewer_output}")


if __name__ == "__main__":
    main()
