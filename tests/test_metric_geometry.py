from __future__ import annotations

import numpy as np
import pytest
import sympy as sp

from engine.dynamics import (
    MetricGeometry,
    schwarzschild_equatorial_metric,
    two_sphere_metric,
)
from engine.numerics import integrate_fixed_step
from systems.sphere_geodesic import build_system as build_sphere_geodesic


def _zero_array(dimension: int) -> sp.ImmutableDenseNDimArray:
    return sp.ImmutableDenseNDimArray(
        [[[0] * dimension] * dimension] * dimension
    )


def test_flat_polar_christoffel_symbols() -> None:
    r, theta = sp.symbols("r theta", positive=True)
    polar = MetricGeometry(coordinates=(r, theta), metric=sp.diag(1, r**2))
    gamma = polar.christoffel_symbols()

    assert gamma[0, 1, 1] == -r
    assert gamma[1, 0, 1] == 1 / r
    assert gamma[1, 1, 0] == 1 / r
    assert gamma[0, 0, 0] == 0


def test_two_sphere_christoffel_symbols_match_reference() -> None:
    sphere = two_sphere_metric()
    theta = sphere.coordinates[0]
    gamma = sphere.christoffel_symbols()

    assert sp.simplify(gamma[0, 1, 1] + sp.sin(theta) * sp.cos(theta)) == 0
    assert sp.simplify(gamma[1, 0, 1] - sp.cos(theta) / sp.sin(theta)) == 0
    # Christoffel symbols are symmetric in the lower indices.
    for k in range(2):
        for i in range(2):
            for j in range(2):
                assert sp.simplify(gamma[k, i, j] - gamma[k, j, i]) == 0


def test_metric_compatibility_residual_vanishes() -> None:
    r, theta = sp.symbols("r theta", positive=True)
    polar = MetricGeometry(coordinates=(r, theta), metric=sp.diag(1, r**2))

    assert polar.metric_compatibility_residual() == _zero_array(2)
    assert two_sphere_metric().metric_compatibility_residual() == _zero_array(2)
    assert (
        schwarzschild_equatorial_metric().metric_compatibility_residual()
        == _zero_array(3)
    )


def test_geodesic_flow_conserves_kinetic_energy_on_sphere() -> None:
    sphere = two_sphere_metric()
    system = sphere.geodesic_system()
    energy = sphere.kinetic_energy()

    derivative = sum(
        sp.diff(energy, state) * rhs
        for state, rhs in zip(system.state, system.rhs, strict=True)
    )
    assert sp.simplify(sp.expand_trig(derivative)) == 0


def test_sphere_geodesics_match_lagrangian_route() -> None:
    radius = sp.Symbol("R", positive=True)
    sphere = two_sphere_metric(radius=radius)
    lagrangian_system = build_sphere_geodesic(mass=1, radius=radius)

    for metric_accel, lagrangian_accel in zip(
        sphere.geodesic_accelerations(),
        lagrangian_system.acceleration_expressions(),
        strict=True,
    ):
        assert sp.simplify(metric_accel - lagrangian_accel) == 0


def test_cogeodesic_medium_matches_geodesic_flow_under_legendre() -> None:
    # Tangent side: p_i = g_ij qdot^j differentiated along the geodesic flow.
    # Cotangent side: pdot_i = -dH/dq^i with H = p^T g^{-1} p / 2.
    sphere = two_sphere_metric()
    momenta = sp.symbols("pi_theta pi_phi", real=True)
    hamiltonian_system = sphere.cogeodesic_medium().to_system(momenta=momenta)

    velocities = sp.Matrix(sphere.velocities)
    momenta_of_velocity = sphere.metric * velocities
    substitutions = dict(zip(momenta, momenta_of_velocity, strict=True))
    accelerations = sphere.geodesic_accelerations()

    for i in range(2):
        tangent_side = sum(
            sp.diff(momenta_of_velocity[i], q) * v
            for q, v in zip(sphere.coordinates, sphere.velocities, strict=True)
        ) + sum(
            sp.diff(momenta_of_velocity[i], v) * a
            for v, a in zip(sphere.velocities, accelerations, strict=True)
        )
        cotangent_side = hamiltonian_system.rhs()[2 + i].subs(substitutions)
        assert sp.simplify(sp.expand_trig(tangent_side - cotangent_side)) == 0


def test_schwarzschild_christoffel_reference_values() -> None:
    geometry = schwarzschild_equatorial_metric()
    _t, r, _phi = geometry.coordinates
    (rs,) = geometry.parameters
    gamma = geometry.christoffel_symbols()

    expected = {
        (0, 0, 1): rs / (2 * r**2 * (1 - rs / r)),
        (1, 0, 0): rs * (r - rs) / (2 * r**3),
        (1, 1, 1): -rs / (2 * r * (r - rs)),
        (1, 2, 2): -(r - rs),
        (2, 1, 2): 1 / r,
    }
    for index, value in expected.items():
        assert sp.simplify(gamma[index] - value) == 0


def test_schwarzschild_cogeodesic_hamiltonian() -> None:
    geometry = schwarzschild_equatorial_metric()
    _t, r, _phi = geometry.coordinates
    (rs,) = geometry.parameters
    p_t, p_r, p_phi = sp.symbols("p_t p_r p_phi", real=True)

    symbol = geometry.cogeodesic_medium().symbol((p_t, p_r, p_phi))
    factor = 1 - rs / r
    expected = (-p_t**2 / factor + factor * p_r**2 + p_phi**2 / r**2) / 2
    assert sp.simplify(symbol - expected) == 0


def test_schwarzschild_circular_orbit_stays_circular() -> None:
    # Exact circular-orbit condition: phi_dot^2 = M t_dot^2 / r^3 with
    # M = rs / 2 (geometrized units), so the radial acceleration vanishes.
    geometry = schwarzschild_equatorial_metric()
    (rs,) = geometry.parameters
    rhs = geometry.geodesic_system().numerical_rhs({rs: 1.0})

    mass, radius = 0.5, 4.0
    omega = np.sqrt(mass / radius**3)
    initial_state = [0.0, radius, 0.0, 1.0, 0.0, omega]
    _time, states = integrate_fixed_step(
        rhs, initial_state=initial_state, t_span=(0.0, 50.0), dt=0.01
    )

    assert np.max(np.abs(states[:, 1] - radius)) < 1e-12
    assert np.max(np.abs(states[:, 4])) < 1e-12

    # Killing charges of the cyclic coordinates t and phi are conserved.
    energy = (1 - 1.0 / states[:, 1]) * states[:, 3]
    angular_momentum = states[:, 1] ** 2 * states[:, 5]
    assert np.max(np.abs(energy - energy[0])) < 1e-12
    assert np.max(np.abs(angular_momentum - angular_momentum[0])) < 1e-12


def test_metric_geometry_validation() -> None:
    x, y = sp.symbols("x y", real=True)

    with pytest.raises(ValueError, match="square"):
        MetricGeometry(coordinates=(x, y), metric=sp.eye(3))
    with pytest.raises(ValueError, match="symmetric"):
        MetricGeometry(coordinates=(x, y), metric=sp.Matrix([[1, x], [0, 1]]))
    with pytest.raises(ValueError, match="non-degenerate"):
        MetricGeometry(coordinates=(x, y), metric=sp.Matrix([[1, 1], [1, 1]]))


def test_metric_geometry_parameter_detection() -> None:
    geometry = schwarzschild_equatorial_metric()
    assert tuple(symbol.name for symbol in geometry.parameters) == ("r_s",)

    numeric = schwarzschild_equatorial_metric(schwarzschild_radius=1)
    assert numeric.parameters == ()
    assert numeric.geodesic_system().parameters == ()
