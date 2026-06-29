from __future__ import annotations

import numpy as np
import sympy as sp

from engine.dynamics import invariant_residuals
from engine.numerics import integrate_fixed_step
from engine.relativity import ProperTimeWorldline
from engine.verification import AssumptionSpec


def test_momentum_dynamics_integrates_four_force_and_preserves_mass_shell() -> None:
    worldline = ProperTimeWorldline(
        dimension=2,
        mass=sp.Integer(1),
        light_speed=sp.Integer(1),
    )
    a = sp.Symbol("a", real=True)
    p0, p1 = worldline.four_momentum_symbols
    system = worldline.momentum_dynamics((a * p1, a * p0))

    assert system.state == (*worldline.coordinates, *worldline.four_momentum_symbols)
    assert system.rhs == (p0, p1, a * p1, a * p0)
    assert system.parameters == (a,)

    _, states = integrate_fixed_step(
        system.numerical_rhs({a: 0.35}),
        initial_state=[0.0, 0.0, 1.0, 0.0],
        t_span=(0.0, 4.0),
        dt=0.005,
    )
    mass_shell = np.asarray(worldline.mass_shell_series(states), dtype=float)
    np.testing.assert_allclose(mass_shell, 0.0, atol=1e-9)
    residual = invariant_residuals({"mass_shell": mass_shell})["mass_shell"]
    assert residual.max_abs < 1e-9


def test_mass_shell_assumption_uses_verification_ir() -> None:
    worldline = ProperTimeWorldline()
    assumption = worldline.mass_shell_assumption()

    assert isinstance(assumption, AssumptionSpec)
    assert assumption.id == "mass-shell"
    assert assumption.role == "model"
    assert assumption.comparison == "="
    assert assumption.rhs == 0.0
    assert set(assumption.variables) == {
        "c",
        "m",
        "p_x0",
        "p_x1",
        "p_x2",
        "p_x3",
    }
    assert assumption.to_dict()["expression"]["format"] == "sympy-srepr"


def test_spatial_force_four_force_is_orthogonal_to_four_velocity() -> None:
    worldline = ProperTimeWorldline(dimension=3)
    vx, vy, fx, fy = sp.symbols("v_x v_y F_x F_y", real=True)

    four_velocity = worldline.four_velocity_from_velocity((vx, vy))
    four_force = worldline.four_force_from_spatial_force((vx, vy), (fx, fy))

    assert sp.simplify(four_velocity.lower().contract(four_force)) == 0


def test_spatial_force_low_velocity_limit_is_newtons_second_law() -> None:
    worldline = ProperTimeWorldline(dimension=2)
    v, force = sp.symbols("v F", real=True)

    four_force = worldline.four_force_from_spatial_force((v,), (force,))
    coordinate_force = worldline.coordinate_momentum_derivative_from_four_force(
        (v,),
        four_force,
    )

    assert sp.simplify(coordinate_force[0] - force) == 0
    # In the low-velocity limit p ~= m v, so dp/dt = F is m dv/dt = F.
    m, acceleration = sp.symbols("m a", positive=True)
    assert sp.solve(sp.Eq(m * acceleration, coordinate_force[0]), acceleration) == [
        force / m
    ]


def test_invalid_four_force_shapes_are_rejected() -> None:
    worldline = ProperTimeWorldline(dimension=3)

    try:
        worldline.momentum_dynamics((0, 0))
    except ValueError as exc:
        assert "four_force" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("expected four-force dimension validation")

    try:
        worldline.four_force_from_spatial_force((0.1,), (1.0, 0.0))
    except ValueError as exc:
        assert "velocity" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("expected velocity dimension validation")
