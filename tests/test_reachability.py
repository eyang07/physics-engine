"""Tests for one-step image enclosure of a discrete map (BE-066).

The contract is the image-containment property: the returned box contains the
true successor of every state sampled from the input box. For the drone, the
open-loop horizontal-axis map enclosed over the control interval
``u1 in [-thrust, thrust]`` must contain every guard-band *closed-loop*
successor, since the guard-band law's output always lies in that interval.
"""

from __future__ import annotations

import random

import sympy as sp

import pytest

from engine.dynamics.discrete import DiscreteSystem
from engine.numerics import Interval
from engine.verification import UnsupportedExpressionError, one_step_image
from systems.drone_point_mass import (
    DroneParams,
    horizontal_axis_closed_loop,
    horizontal_axis_system,
)


def test_linear_map_image_is_exact_and_rational() -> None:
    x = sp.Symbol("x", real=True)
    system = DiscreteSystem(state=(x,), update=(2 * x + 1,))
    image = one_step_image(system, {"x": Interval(0, 1)})
    assert image["x"] == Interval(1, 3)
    assert isinstance(image["x"].lower, sp.Rational)


def test_bounded_parameter_carried_as_interval() -> None:
    x, p = sp.symbols("x p", real=True)
    # x_{k+1} = x + p, with p a bounded input carried as an interval
    system = DiscreteSystem(state=(x,), update=(x + p,), parameters=(p,))
    image = one_step_image(system, {"x": Interval(0, 2), "p": Interval(-1, 1)})
    assert image["x"] == Interval(-1, 3)


def test_missing_symbol_fails_closed() -> None:
    x, p = sp.symbols("x p", real=True)
    system = DiscreteSystem(state=(x,), update=(x + p,), parameters=(p,))
    with pytest.raises(ValueError, match="missing intervals"):
        one_step_image(system, {"x": Interval(0, 2)})


def test_piecewise_closed_loop_is_rejected() -> None:
    """The guard-band closed loop carries a Piecewise switch -> fail closed."""

    system = horizontal_axis_closed_loop()
    box = {"q1": Interval(-1, 1), "v1": Interval(-1, 1)}
    with pytest.raises(UnsupportedExpressionError):
        one_step_image(system, box)


def test_image_contains_sampled_open_loop_successors() -> None:
    params = DroneParams()
    system = horizontal_axis_system(params)  # open loop, control u1 free
    thrust = params.horizontal_thrust
    box = {
        "q1": Interval(-1, 1),
        "v1": Interval(-2, 2),
        "u1": Interval(sp.nsimplify(-thrust, rational=True), sp.nsimplify(thrust, rational=True)),
    }
    image = one_step_image(system, box)

    # lambdify the open-loop update directly for an explicit control value
    q1s, v1s = system.state
    (u1s,) = system.controls
    f = sp.lambdify((q1s, v1s, u1s), list(system.update), "numpy")
    lo_q, hi_q = float(image["q1"].lower), float(image["q1"].upper)
    lo_v, hi_v = float(image["v1"].lower), float(image["v1"].upper)
    rng = random.Random(31)
    for _ in range(500):
        q1 = rng.uniform(-1, 1)
        v1 = rng.uniform(-2, 2)
        u1 = rng.uniform(-thrust, thrust)
        nxt = f(q1, v1, u1)
        assert lo_q <= nxt[0] <= hi_q
        assert lo_v <= nxt[1] <= hi_v


def test_image_over_approximates_closed_loop_successors() -> None:
    """The open-loop image over u1 in [-thrust, thrust] contains every
    guard-band closed-loop successor."""

    params = DroneParams()
    open_loop = horizontal_axis_system(params)
    thrust = params.horizontal_thrust
    box = {
        "q1": Interval(-1, 1),
        "v1": Interval(-2, 2),
        "u1": Interval(sp.nsimplify(-thrust, rational=True), sp.nsimplify(thrust, rational=True)),
    }
    image = one_step_image(open_loop, box)
    lo_q, hi_q = float(image["q1"].lower), float(image["q1"].upper)
    lo_v, hi_v = float(image["v1"].lower), float(image["v1"].upper)

    closed_loop = horizontal_axis_closed_loop(params)
    cl_update = closed_loop.numerical_update()  # F(k, q1, v1) with guard band
    rng = random.Random(32)
    for _ in range(500):
        q1 = rng.uniform(-1, 1)
        v1 = rng.uniform(-2, 2)
        nxt = cl_update(0, [q1, v1])
        assert lo_q <= nxt[0] <= hi_q
        assert lo_v <= nxt[1] <= hi_v
