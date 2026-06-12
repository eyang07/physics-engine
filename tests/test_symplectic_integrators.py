from __future__ import annotations

import numpy as np
import pytest
import sympy as sp

from engine.mechanics import HamiltonianSystem, legendre_transform
from engine.numerics import (
    integrate_symplectic,
    stormer_verlet_step,
    symplectic_euler_step,
)
from systems.pendulum import build_system as build_pendulum


def _harmonic_oscillator() -> HamiltonianSystem:
    q, p = sp.symbols("q p", real=True)
    return HamiltonianSystem(
        coordinates=(q,), momenta=(p,), hamiltonian=(p**2 + q**2) / 2
    )


def _pendulum_hamiltonian() -> HamiltonianSystem:
    lagrangian = build_pendulum(mass=1.0, length=1.0, gravity=9.81)
    return legendre_transform(lagrangian).hamiltonian_system


def _final_error(dt: float, method: str) -> float:
    velocity, force = _harmonic_oscillator().separable_split()
    times, states = integrate_symplectic(
        velocity, force, (1.0,), (0.0,), (0.0, 10.0), dt, method=method
    )
    exact_q, exact_p = np.cos(times[-1]), -np.sin(times[-1])
    return float(np.hypot(states[-1, 0] - exact_q, states[-1, 1] - exact_p))


def test_stormer_verlet_is_second_order() -> None:
    ratio = _final_error(0.01, "stormer-verlet") / _final_error(0.005, "stormer-verlet")
    assert 3.5 < ratio < 4.5


def test_symplectic_euler_is_first_order() -> None:
    ratio = _final_error(0.01, "symplectic-euler") / _final_error(0.005, "symplectic-euler")
    assert 1.6 < ratio < 2.4


def test_energy_error_stays_bounded_over_long_runs() -> None:
    velocity, force = _harmonic_oscillator().separable_split()
    _, states = integrate_symplectic(
        velocity, force, (1.0,), (0.0,), (0.0, 500.0), 0.05
    )
    energy = (states[:, 0] ** 2 + states[:, 1] ** 2) / 2
    deviation = np.abs(energy - energy[0])

    half = len(deviation) // 2
    assert float(np.max(deviation)) < 5e-3
    # Bounded oscillation, not secular drift: the late-time error envelope
    # must not exceed the early-time envelope.
    assert float(np.max(deviation[half:])) <= float(np.max(deviation[:half])) * 1.1


def test_stormer_verlet_is_time_reversible() -> None:
    velocity, force = _pendulum_hamiltonian().separable_split()
    initial_position, initial_momentum = (1.0,), (0.3,)

    _, forward = integrate_symplectic(
        velocity, force, initial_position, initial_momentum, (0.0, 25.0), 0.01
    )
    _, backward = integrate_symplectic(
        velocity, force, (forward[-1, 0],), (-forward[-1, 1],), (0.0, 25.0), 0.01
    )
    returned = np.array([backward[-1, 0], -backward[-1, 1]])
    assert np.allclose(returned, [1.0, 0.3], atol=1e-9)


@pytest.mark.parametrize("stepper", [stormer_verlet_step, symplectic_euler_step])
def test_step_jacobian_has_unit_determinant(stepper) -> None:
    velocity, force = _pendulum_hamiltonian().separable_split()
    point = np.array([0.7, 0.4])
    dt, eps = 0.1, 1e-6

    def step(state: np.ndarray) -> np.ndarray:
        position, momentum = stepper(velocity, force, state[:1], state[1:], dt)
        return np.concatenate([position, momentum])

    jacobian = np.empty((2, 2))
    for column in range(2):
        offset = np.zeros(2)
        offset[column] = eps
        jacobian[:, column] = (step(point + offset) - step(point - offset)) / (2 * eps)
    assert float(np.linalg.det(jacobian)) == pytest.approx(1.0, abs=1e-7)


def test_pendulum_energy_residual_is_small() -> None:
    system = _pendulum_hamiltonian()
    velocity, force = system.separable_split()
    times, states = integrate_symplectic(
        velocity, force, (2.0,), (0.0,), (0.0, 20.0), 0.001
    )

    hamiltonian = sp.lambdify((*system.q, *system.p), system.hamiltonian, modules="numpy")
    energy = hamiltonian(states[:, 0], states[:, 1])
    assert float(np.max(np.abs(energy - energy[0]))) < 1e-4
    assert times[-1] == 20.0


def test_separable_split_validation() -> None:
    q, p = sp.symbols("q p", real=True)
    t = sp.Symbol("t", real=True)
    k = sp.Symbol("k", positive=True)

    coupled = HamiltonianSystem(coordinates=(q,), momenta=(p,), hamiltonian=q * p)
    assert not coupled.is_separable()
    with pytest.raises(ValueError, match="not separable"):
        coupled.separable_split()

    driven = HamiltonianSystem(
        coordinates=(q,), momenta=(p,), hamiltonian=p**2 / 2 + sp.sin(t) * q, time=t
    )
    with pytest.raises(ValueError, match="autonomous"):
        driven.separable_split()

    parametric = HamiltonianSystem(
        coordinates=(q,), momenta=(p,), hamiltonian=p**2 / 2 + k * q**2
    )
    assert parametric.is_separable()
    with pytest.raises(ValueError, match="unresolved"):
        parametric.separable_split()
    velocity, force = parametric.separable_split(substitutions={k: 2.0})
    assert velocity((3.0,)) == pytest.approx([3.0])
    assert force((1.5,)) == pytest.approx([-6.0])

    with pytest.raises(ValueError, match="unknown symplectic method"):
        integrate_symplectic(velocity, force, (1.0,), (0.0,), (0.0, 1.0), 0.1, method="rk4")
    with pytest.raises(ValueError, match="same dimension"):
        integrate_symplectic(velocity, force, (1.0, 2.0), (0.0,), (0.0, 1.0), 0.1)
