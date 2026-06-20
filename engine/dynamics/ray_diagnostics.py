"""Diagnostics for ray bundles: travel time, caustic proximity, envelopes.

These operate on the shared-time ray arrays produced by
:func:`engine.dynamics.ray_bundle.integrate_ray_bundle`:

- *travel time* is the optical path / eikonal phase ``phi(s) = int xi . dq``
  accumulated along each ray (trapezoidal in the stored samples). For a
  symbol that is homogeneous of degree ``m`` in ``xi``, Euler's theorem gives
  ``xi . dp/dxi = m * p``, so the exact phase is ``m * p0 * s`` and the
  difference is a measured integration residual;
- *caustic proximity* is a finite-difference geometric-spreading diagnostic:
  the separation of adjacent rays relative to their initial separation. A
  caustic is a singularity of the ray map, so small spreading factors mark
  approach to a caustic. This is measured evidence from a discrete bundle,
  not a root-find of the Jacobian;
- *wavefront envelope metadata* summarizes each wavefront snapshot: polyline
  arc length, spreading-factor range, and coordinate bounds.

Spreading, caustic, and envelope diagnostics require at least two rays;
travel time is defined per ray.
"""

from __future__ import annotations

import numpy as np

from engine.dynamics.ray_bundle import (
    RayBundleResult,
    ray_bundle_snapshot_indices,
)


def _positions_and_momenta(
    rays: np.ndarray, coordinate_count: int
) -> tuple[np.ndarray, np.ndarray]:
    ray_array = np.asarray(rays, dtype=float)
    if ray_array.ndim != 3:
        raise ValueError("rays must have shape (ray, sample, state)")
    if ray_array.shape[2] < 2 * coordinate_count:
        raise ValueError("rays must carry coordinates and conjugate momenta")
    positions = ray_array[:, :, :coordinate_count]
    momenta = ray_array[:, :, coordinate_count : 2 * coordinate_count]
    return positions, momenta


def ray_travel_times(rays: np.ndarray, *, coordinate_count: int) -> np.ndarray:
    """Cumulative eikonal phase ``int xi . dq`` per ray, shape (ray, sample)."""

    positions, momenta = _positions_and_momenta(rays, coordinate_count)
    dq = positions[:, 1:, :] - positions[:, :-1, :]
    midpoint_momenta = (momenta[:, 1:, :] + momenta[:, :-1, :]) / 2
    increments = np.sum(midpoint_momenta * dq, axis=2)
    phases = np.concatenate(
        [np.zeros((positions.shape[0], 1)), np.cumsum(increments, axis=1)],
        axis=1,
    )
    return phases


def ray_spreading_factors(rays: np.ndarray, *, coordinate_count: int) -> np.ndarray:
    """Adjacent-ray separations relative to t0, shape (ray - 1, sample)."""

    positions, _ = _positions_and_momenta(rays, coordinate_count)
    if positions.shape[0] < 2:
        raise ValueError("spreading factors require at least two rays")
    separations = np.linalg.norm(positions[1:] - positions[:-1], axis=2)
    initial = separations[:, [0]]
    if np.any(initial == 0.0):
        raise ValueError("adjacent rays must start at distinct positions")
    return separations / initial


def caustic_proximity(
    rays: np.ndarray,
    time: np.ndarray,
    *,
    coordinate_count: int,
) -> dict[str, object]:
    """Locate the strongest focusing of the bundle (minimum spreading)."""

    factors = ray_spreading_factors(rays, coordinate_count=coordinate_count)
    time_array = np.asarray(time, dtype=float)
    if factors.shape[1] != time_array.shape[0]:
        raise ValueError("time must match the ray sample count")

    positions, _ = _positions_and_momenta(rays, coordinate_count)
    pair_index, sample_index = np.unravel_index(np.argmin(factors), factors.shape)
    location = (
        positions[pair_index, sample_index, :] + positions[pair_index + 1, sample_index, :]
    ) / 2

    return {
        "method": "adjacent-ray finite-difference spreading factors",
        "minSpreadingFactor": float(factors[pair_index, sample_index]),
        "time": float(time_array[sample_index]),
        "pairIndex": int(pair_index),
        "location": location.astype(float).tolist(),
        "minSeries": np.min(factors, axis=0),
    }


def wavefront_envelope_records(
    rays: np.ndarray,
    time: np.ndarray,
    *,
    coordinate_count: int,
    snapshot_stride: int,
    coordinate_names: tuple[str, ...] | None = None,
) -> list[dict[str, object]]:
    """Per-snapshot wavefront summaries: arc length, spreading range, bounds."""

    positions, _ = _positions_and_momenta(rays, coordinate_count)
    factors = ray_spreading_factors(rays, coordinate_count=coordinate_count)
    time_array = np.asarray(time, dtype=float)
    names = coordinate_names or _envelope_coordinate_names(coordinate_count)

    records: list[dict[str, object]] = []
    for index in ray_bundle_snapshot_indices(len(time_array), snapshot_stride):
        points = positions[:, index, :]
        segment_lengths = np.linalg.norm(points[1:] - points[:-1], axis=1)
        records.append(
            {
                "time": float(time_array[index]),
                "arcLength": float(np.sum(segment_lengths)),
                "minSpreadingFactor": float(np.min(factors[:, index])),
                "maxSpreadingFactor": float(np.max(factors[:, index])),
                "bounds": {
                    name: [float(points[:, axis].min()), float(points[:, axis].max())]
                    for axis, name in enumerate(names)
                },
            }
        )
    return records


def wavefront_surface_payload(
    bundle: RayBundleResult,
    *,
    snapshot_stride: int,
) -> dict[str, object]:
    """Export sampled wavefront points with their measured eikonal phase."""

    phases = ray_travel_times(bundle.rays, coordinate_count=bundle.coordinate_count)
    indices = ray_bundle_snapshot_indices(len(bundle.time), snapshot_stride)
    return {
        "kind": "wavefront-surface",
        "rendererHint": "scalar-field",
        "name": "wavefrontSurface",
        "coordinates": ["ray"],
        "time": bundle.time[list(indices)].astype(float).tolist(),
        "points": [
            bundle.rays[:, index, : bundle.coordinate_count].astype(float).tolist()
            for index in indices
        ],
        "travelTime": [
            phases[:, index].astype(float).tolist()
            for index in indices
        ],
        "evaluation": "measured-ray-bundle",
        "rigor": "measured",
    }


def wavefront_intensity_payload(
    bundle: RayBundleResult,
    *,
    snapshot_stride: int,
    floor: float = 1e-3,
) -> dict[str, object]:
    """Export a measured intensity proxy from finite-difference ray spreading."""

    if floor <= 0.0:
        raise ValueError("floor must be positive")
    factors = ray_spreading_factors(bundle.rays, coordinate_count=bundle.coordinate_count)
    indices = ray_bundle_snapshot_indices(len(bundle.time), snapshot_stride)
    positions, _ = _positions_and_momenta(bundle.rays, bundle.coordinate_count)
    initial_midpoints = 0.5 * (positions[:-1, 0, :] + positions[1:, 0, :])
    initial_axis = initial_midpoints[:, 1 if bundle.coordinate_count > 1 else 0]
    sampled = factors[:, list(indices)].T
    intensity = 1.0 / np.maximum(sampled, floor)
    return {
        "kind": "scalar-field-series",
        "rendererHint": "scalar-field",
        "name": "wavefrontIntensity",
        "coordinates": ["initialY" if bundle.coordinate_count > 1 else "initialCoordinate"],
        "axes": [initial_axis.astype(float).tolist()],
        "time": bundle.time[list(indices)].astype(float).tolist(),
        "shape": list(intensity.shape),
        "values": intensity.astype(float).tolist(),
        "source": "adjacent-ray finite-difference spreading factors",
        "evaluation": "measured-ray-bundle",
        "rigor": "measured",
    }


def ray_bundle_diagnostics(
    bundle: RayBundleResult,
    *,
    snapshot_stride: int,
    symbol_degree: int | None = None,
) -> dict[str, object]:
    """Assemble exportable travel-time, caustic, and envelope diagnostics.

    If ``symbol_degree`` is given, the symbol is asserted to be homogeneous of
    that degree in the momenta, and the measured phase is compared against the
    exact model ``degree * p0 * s`` as a residual.
    """

    phases = ray_travel_times(bundle.rays, coordinate_count=bundle.coordinate_count)
    caustic = caustic_proximity(
        bundle.rays, bundle.time, coordinate_count=bundle.coordinate_count
    )
    snapshot_indices = ray_bundle_snapshot_indices(len(bundle.time), snapshot_stride)
    sampled_times = bundle.time[list(snapshot_indices)]

    travel_time: dict[str, object] = {
        "definition": "cumulative optical path integral of xi . dq along each ray",
        "final": phases[:, -1].astype(float).tolist(),
        "center": {
            "time": sampled_times.astype(float).tolist(),
            "value": phases[bundle.center_index, list(snapshot_indices)].astype(float).tolist(),
        },
    }
    if symbol_degree is not None:
        expected = symbol_degree * bundle.hamiltonian_initials[:, None] * bundle.time[None, :]
        travel_time["expectedModel"] = (
            f"phase = {symbol_degree} * p0 * s for a degree-{symbol_degree} homogeneous symbol"
        )
        travel_time["residualMax"] = float(np.max(np.abs(phases - expected)))

    min_series = caustic.pop("minSeries")
    caustic["minSeries"] = {
        "time": sampled_times.astype(float).tolist(),
        "value": np.asarray(min_series, dtype=float)[list(snapshot_indices)].tolist(),
    }

    return {
        "travelTime": travel_time,
        "causticProximity": caustic,
        "wavefrontEnvelope": wavefront_envelope_records(
            bundle.rays,
            bundle.time,
            coordinate_count=bundle.coordinate_count,
            snapshot_stride=snapshot_stride,
        ),
    }


def _envelope_coordinate_names(coordinate_count: int) -> tuple[str, ...]:
    names = ("x", "y", "z")
    if coordinate_count <= len(names):
        return names[:coordinate_count]
    return tuple(f"q{index}" for index in range(coordinate_count))


__all__ = [
    "caustic_proximity",
    "ray_bundle_diagnostics",
    "ray_spreading_factors",
    "ray_travel_times",
    "wavefront_envelope_records",
    "wavefront_intensity_payload",
    "wavefront_surface_payload",
]
