from __future__ import annotations

import numpy as np
import pytest
import sympy as sp

from engine.fields import (
    VectorField,
    integrate_field_lines,
    seeds_on_segment,
)


def _xy() -> tuple[sp.Symbol, sp.Symbol]:
    return sp.symbols("x y", real=True)


def test_circulation_field_lines_are_circles() -> None:
    x, y = _xy()
    # V = (-y, x): field lines are circles centred at the origin.
    field = VectorField((x, y), (-y, x))
    bounds = [(-2.0, 2.0), (-2.0, 2.0)]
    [line] = integrate_field_lines(
        field, [[1.0, 0.0]], bounds=bounds, arc_step=0.02, max_steps=2000,
        both_directions=False,
    )
    radii = np.linalg.norm(line, axis=1)
    # The radius stays 1 along the whole integrated line.
    assert np.allclose(radii, 1.0, atol=1e-3)
    # It traces (at least) a full loop back near the seed.
    assert np.min(np.linalg.norm(line[1:] - line[0], axis=1)) < 1e-2


def test_radial_field_lines_are_straight_rays() -> None:
    x, y = _xy()
    # V = (x, y): field lines are rays through the origin.
    field = VectorField((x, y), (x, y))
    bounds = [(-3.0, 3.0), (-3.0, 3.0)]
    seed = np.array([1.0, 1.0])
    [line] = integrate_field_lines(
        field, [seed], bounds=bounds, arc_step=0.02, max_steps=2000,
    )
    # Every point is collinear with the origin and the seed (zero cross product).
    cross = line[:, 0] * seed[1] - line[:, 1] * seed[0]
    assert np.allclose(cross, 0.0, atol=1e-6)


def test_line_terminates_cleanly_on_the_domain_boundary() -> None:
    x, y = _xy()
    field = VectorField((x, y), (sp.Integer(1), sp.Integer(0)))  # uniform +x flow
    bounds = [(-1.0, 1.0), (-1.0, 1.0)]
    [line] = integrate_field_lines(
        field, [[0.0, 0.0]], bounds=bounds, arc_step=0.05, max_steps=1000,
        both_directions=False,
    )
    # Stays inside the box and ends on the +x face.
    assert np.all(line[:, 0] <= 1.0 + 1e-9)
    assert np.isclose(line[-1, 0], 1.0, atol=1e-6)


def test_singularity_radius_stops_a_field_line() -> None:
    x, y = _xy()
    # Sink toward the origin; backward integration would otherwise crawl in forever.
    field = VectorField((x, y), (-x, -y))
    bounds = [(-3.0, 3.0), (-3.0, 3.0)]
    [line] = integrate_field_lines(
        field, [[2.0, 0.0]], bounds=bounds, arc_step=0.02, max_steps=5000,
        both_directions=False, singularities=[[0.0, 0.0]], stop_radius=0.05,
    )
    assert np.linalg.norm(line[-1]) <= 0.05 + 1e-9


def test_integration_is_deterministic() -> None:
    x, y = _xy()
    field = VectorField((x, y), (-y, x))
    bounds = [(-2.0, 2.0), (-2.0, 2.0)]
    first = integrate_field_lines(field, [[1.0, 0.0]], bounds=bounds, both_directions=False)
    second = integrate_field_lines(field, [[1.0, 0.0]], bounds=bounds, both_directions=False)
    assert np.array_equal(first[0], second[0])


def test_seeds_on_segment_is_deterministic_and_inclusive() -> None:
    seeds = seeds_on_segment([0.0, -1.0], [0.0, 1.0], 5)
    assert seeds.shape == (5, 2)
    assert np.allclose(seeds[0], [0.0, -1.0])
    assert np.allclose(seeds[-1], [0.0, 1.0])
    assert np.array_equal(seeds, seeds_on_segment([0.0, -1.0], [0.0, 1.0], 5))
    with pytest.raises(ValueError, match="positive"):
        seeds_on_segment([0.0, 0.0], [1.0, 1.0], 0)
