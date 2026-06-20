"""Field-line and streamline integration for vector fields.

A field line is an integral curve of the *direction* of a vector field: it
solves ``dx/ds = V(x)/|V(x)|`` (unit speed in arc length ``s``), so the geometry
is independent of the field's magnitude. The same curve is the streamline of a
steady flow. Integration uses the shared RK4 step (`engine.numerics`) and
terminates cleanly when a line leaves the domain box, stalls at a stagnation
point (``|V| -> 0``), or enters the exclusion radius of a listed singularity.

Seeding strategy: seeds are explicit, caller-provided points (deterministic);
``seeds_on_segment`` builds an evenly spaced, endpoint-inclusive set along a line
segment for reproducible seeding.
"""

from __future__ import annotations

from typing import Mapping, Sequence

import numpy as np
import sympy as sp

from engine.fields.fields import VectorField
from engine.numerics.integrators import rk4_step


def seeds_on_segment(
    start: Sequence[float], end: Sequence[float], count: int
) -> np.ndarray:
    """Return ``count`` evenly spaced seeds along ``start``→``end`` (inclusive)."""

    if count < 1:
        raise ValueError("count must be positive")
    start_point = np.asarray(start, dtype=float)
    end_point = np.asarray(end, dtype=float)
    if start_point.shape != end_point.shape:
        raise ValueError("start and end must have the same dimension")
    fractions = np.linspace(0.0, 1.0, count)
    return np.array([(1.0 - t) * start_point + t * end_point for t in fractions])


def _vector_evaluator(
    field: VectorField, parameter_values: Mapping[str, float] | None
):
    values = dict(parameter_values or {})
    missing = {p.name for p in field.parameters} - set(values)
    if missing:
        raise ValueError(f"missing parameter values: {', '.join(sorted(missing))}")
    func = sp.lambdify(
        (*field.coordinates, *field.parameters), list(field.components), modules="numpy"
    )
    parameter_args = [float(values[p.name]) for p in field.parameters]

    def evaluate(point: np.ndarray) -> np.ndarray:
        raw = func(*point, *parameter_args)
        return np.asarray(raw, dtype=float).reshape(field.dimension)

    return evaluate


def _clip_to_bounds(
    start: np.ndarray, end: np.ndarray, bounds: Sequence[tuple[float, float]]
) -> np.ndarray:
    segment = end - start
    fraction = 1.0
    for coordinate, (low, high), delta in zip(start, bounds, segment):
        if delta > 0.0:
            fraction = min(fraction, (high - coordinate) / delta)
        elif delta < 0.0:
            fraction = min(fraction, (low - coordinate) / delta)
    return start + max(fraction, 0.0) * segment


def _within(point: np.ndarray, bounds: Sequence[tuple[float, float]]) -> bool:
    return all(low <= value <= high for value, (low, high) in zip(point, bounds))


def _near_singularity(
    point: np.ndarray, singularities: Sequence[np.ndarray], radius: float
) -> bool:
    return any(float(np.linalg.norm(point - center)) <= radius for center in singularities)


def _integrate_one(
    evaluate,
    seed: np.ndarray,
    *,
    sign: float,
    bounds: Sequence[tuple[float, float]],
    arc_step: float,
    max_steps: int,
    min_speed: float,
    singularities: Sequence[np.ndarray],
    stop_radius: float,
) -> np.ndarray:
    def rhs(_s: float, point: Sequence[float]) -> np.ndarray:
        vector = evaluate(np.asarray(point, dtype=float))
        speed = float(np.linalg.norm(vector))
        if speed < min_speed:
            return np.zeros_like(vector)
        return sign * vector / speed

    points = [np.asarray(seed, dtype=float)]
    current = points[0].copy()
    for _ in range(max_steps):
        if float(np.linalg.norm(evaluate(current))) < min_speed:
            break
        nxt = np.asarray(rk4_step(rhs, 0.0, current, arc_step), dtype=float)
        if not _within(nxt, bounds):
            points.append(_clip_to_bounds(current, nxt, bounds))
            break
        if singularities and _near_singularity(nxt, singularities, stop_radius):
            points.append(nxt)
            break
        points.append(nxt)
        current = nxt
    return np.array(points)


def integrate_field_lines(
    field: VectorField,
    seeds: Sequence[Sequence[float]],
    *,
    bounds: Sequence[tuple[float, float]],
    arc_step: float = 0.02,
    max_steps: int = 2000,
    both_directions: bool = True,
    parameter_values: Mapping[str, float] | None = None,
    min_speed: float = 1e-9,
    singularities: Sequence[Sequence[float]] = (),
    stop_radius: float = 1e-2,
) -> list[np.ndarray]:
    """Integrate field lines of ``field`` from each seed.

    Returns one polyline (``(point, dimension)`` array) per seed. With
    ``both_directions`` the seed is traced forward and backward and the two arcs
    are joined through the seed. ``bounds`` is one ``(low, high)`` pair per
    coordinate; ``singularities`` are points whose ``stop_radius`` ball ends a
    line (e.g. charges in a dipole field).
    """

    if len(bounds) != field.dimension:
        raise ValueError("one (low, high) bound is required per coordinate")
    evaluate = _vector_evaluator(field, parameter_values)
    singular_points = [np.asarray(center, dtype=float) for center in singularities]

    lines: list[np.ndarray] = []
    for seed in np.asarray(seeds, dtype=float):
        forward = _integrate_one(
            evaluate, seed, sign=1.0, bounds=bounds, arc_step=arc_step,
            max_steps=max_steps, min_speed=min_speed,
            singularities=singular_points, stop_radius=stop_radius,
        )
        if both_directions:
            backward = _integrate_one(
                evaluate, seed, sign=-1.0, bounds=bounds, arc_step=arc_step,
                max_steps=max_steps, min_speed=min_speed,
                singularities=singular_points, stop_radius=stop_radius,
            )
            if len(backward) > 1:
                lines.append(np.vstack([backward[::-1][:-1], forward]))
            else:
                lines.append(forward)
        else:
            lines.append(forward)
    return lines
