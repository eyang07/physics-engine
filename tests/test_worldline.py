from __future__ import annotations

import numpy as np
import pytest
import sympy as sp

from engine.numerics import integrate_fixed_step
from engine.relativity import FourVector, ProperTimeWorldline


def test_four_velocity_norm_squared_is_minus_c_squared() -> None:
    # 1+1 dimensions with a symbolic coordinate velocity: u.u must equal -c^2.
    worldline = ProperTimeWorldline(dimension=2)
    v = sp.Symbol("v", real=True)
    c = worldline.light_speed
    four_velocity = worldline.four_velocity_from_velocity((v,))
    assert sp.simplify(four_velocity.norm_squared() + c**2) == 0


def test_four_velocity_norm_squared_in_3plus1() -> None:
    worldline = ProperTimeWorldline(dimension=4)
    vx, vy, vz = sp.symbols("v_x v_y v_z", real=True)
    c = worldline.light_speed
    four_velocity = worldline.four_velocity_from_velocity((vx, vy, vz))
    assert sp.simplify(four_velocity.norm_squared() + c**2) == 0
    # It is timelike for a sub-luminal velocity.
    assert four_velocity.norm_squared().subs({vx: 0, vy: 0, vz: 0, c: 1}) == -1


def test_four_momentum_is_on_the_mass_shell() -> None:
    worldline = ProperTimeWorldline(dimension=4)
    vx = sp.Symbol("v_x", real=True)
    m, c = worldline.mass, worldline.light_speed
    momentum = worldline.four_momentum_from_velocity((vx, 0, 0))
    # p.p = -(m c)^2.
    assert sp.simplify(momentum.norm_squared() + (m * c) ** 2) == 0


def test_rest_four_velocity_and_momentum() -> None:
    worldline = ProperTimeWorldline(dimension=4)
    m, c = worldline.mass, worldline.light_speed
    rest_velocity = worldline.four_velocity_from_velocity((0, 0, 0))
    # At rest u^mu = (c, 0, 0, 0).
    assert rest_velocity.components == (c, 0, 0, 0)
    rest_momentum = worldline.four_momentum_from_velocity((0, 0, 0))
    # Energy component p^0 = m c (so E = c p^0 = m c^2).
    assert rest_momentum.components[0] == m * c


def test_first_order_system_is_the_free_geodesic() -> None:
    worldline = ProperTimeWorldline(dimension=4)
    system = worldline.first_order_system()
    coordinates = worldline.coordinates
    velocities = worldline.four_velocity_symbols
    # State is (x^mu, u^mu); the proper time is the independent variable.
    assert system.state == (*coordinates, *velocities)
    assert system.time == worldline.proper_time
    # dx^mu/dtau = u^mu, du^mu/dtau = 0 (free particle).
    assert system.rhs == (*velocities, sp.Integer(0), sp.Integer(0), sp.Integer(0), sp.Integer(0))
    # No unresolved parameters in the free system.
    assert system.parameters == ()


def test_free_worldline_integrates_to_a_straight_line() -> None:
    worldline = ProperTimeWorldline(dimension=4)
    c_value = 1.0
    velocity = (0.6, 0.0, 0.0)  # 0.6 c along x
    four_velocity = worldline.four_velocity_from_velocity(velocity)
    u0 = [float(component.subs({worldline.light_speed: c_value})) for component in four_velocity.components]
    gamma = 1.0 / np.sqrt(1 - 0.6**2)

    system = worldline.first_order_system()
    rhs = system.numerical_rhs()
    initial_state = [0.0, 0.0, 0.0, 0.0, *u0]
    tau, states = integrate_fixed_step(rhs, initial_state, (0.0, 2.0), 0.01)

    # The four-velocity is conserved (free particle).
    np.testing.assert_allclose(states[:, 4:], np.broadcast_to(u0, states[:, 4:].shape), atol=1e-9)
    # x^mu(tau) = u^mu tau: a straight worldline.
    expected = np.outer(tau, u0)
    np.testing.assert_allclose(states[:, :4], expected, atol=1e-8)
    # Time dilation: x^0 = c gamma tau, i.e. coordinate time t = gamma tau > tau.
    np.testing.assert_allclose(states[:, 0], c_value * gamma * tau, atol=1e-8)


def test_measured_four_velocity_norm_stays_minus_c_squared_along_rollout() -> None:
    worldline = ProperTimeWorldline(dimension=4)
    c_value = 1.0
    four_velocity = worldline.four_velocity_from_velocity((0.6, 0.0, 0.0))
    u0 = [float(component.subs({worldline.light_speed: c_value})) for component in four_velocity.components]
    system = worldline.first_order_system()
    _, states = integrate_fixed_step(system.numerical_rhs(), [0.0, 0.0, 0.0, 0.0, *u0], (0.0, 2.0), 0.01)
    # Measured: norm^2 of the sampled four-velocity stays at -c^2.
    norms = -states[:, 4] ** 2 + states[:, 5] ** 2 + states[:, 6] ** 2 + states[:, 7] ** 2
    np.testing.assert_allclose(norms, -(c_value**2), atol=1e-9)


def test_first_order_system_accepts_a_four_acceleration() -> None:
    worldline = ProperTimeWorldline(dimension=2)
    a = sp.Symbol("a", real=True)
    velocities = worldline.four_velocity_symbols
    system = worldline.first_order_system(four_acceleration=(0, a))
    assert system.rhs == (*velocities, sp.Integer(0), a)
    # The free symbol that is not a state/time variable is surfaced as a parameter.
    assert system.parameters == (a,)


def test_invalid_constructions_are_rejected() -> None:
    with pytest.raises(ValueError):
        ProperTimeWorldline(dimension=1)
    worldline = ProperTimeWorldline(dimension=4)
    with pytest.raises(ValueError):
        worldline.four_velocity_from_velocity((0.1, 0.2))  # wrong spatial count
    with pytest.raises(ValueError):
        worldline.first_order_system(four_acceleration=(0, 0, 0))  # wrong length
