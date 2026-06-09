from __future__ import annotations

import numpy as np
import sympy as sp

from engine.dynamics import (
    CotangentHamiltonianSystem,
    integrate_ray_bundle,
    ray_bundle_coordinate_bounds,
)
from scripts.generate_variable_speed_wavefront import generate_variable_speed_wavefront
from systems.variable_speed_wavefront import build_system, wave_speed


def test_cotangent_hamiltonian_system_equations() -> None:
    x, y, xi, eta = sp.symbols("x y xi eta", real=True)
    symbol = (xi**2 + eta**2) / 2 + x * y
    system = CotangentHamiltonianSystem(
        coordinates=(x, y),
        momenta=(xi, eta),
        symbol=symbol,
    )

    assert system.state_symbols == (x, y, xi, eta)
    assert system.rhs() == (xi, eta, -y, -x)
    assert system.first_order_system().rhs == (xi, eta, -y, -x)


def test_variable_speed_wavefront_symbol_and_rhs() -> None:
    c0, alpha, sigma = sp.symbols("c0 alpha sigma", positive=True)
    system = build_system(base_speed=c0, lens_strength=alpha, lens_width=sigma)
    x, y = system.coordinates
    xi, eta = system.momenta

    speed = wave_speed(x, y, base_speed=c0, lens_strength=alpha, lens_width=sigma)
    expected_symbol = speed**2 * (xi**2 + eta**2) / 2

    assert sp.simplify(system.symbol - expected_symbol) == 0
    assert sp.simplify(system.rhs()[0] - speed**2 * xi) == 0
    assert sp.simplify(system.rhs()[1] - speed**2 * eta) == 0


def test_ray_bundle_helper_is_deterministic_and_reports_drift() -> None:
    x, y, xi, eta = sp.symbols("x y xi eta", real=True)
    system = CotangentHamiltonianSystem(
        coordinates=(x, y),
        momenta=(xi, eta),
        symbol=(xi**2 + eta**2) / 2,
    )
    initial_states = [
        [-1.0, -0.25, 1.0, 0.0],
        [-1.0, 0.25, 2.0, 0.0],
    ]

    first = integrate_ray_bundle(
        system,
        initial_states,
        t_span=(0.0, 0.2),
        dt=0.05,
        state_names=["x", "y", "xi", "eta"],
    )
    second = integrate_ray_bundle(
        system,
        initial_states,
        t_span=(0.0, 0.2),
        dt=0.05,
        state_names=["x", "y", "xi", "eta"],
    )

    assert np.array_equal(first.time, second.time)
    assert np.array_equal(first.rays, second.rays)
    assert first.rays.shape == (2, 5, 4)
    assert first.state_names == ("x", "y", "xi", "eta")
    assert np.allclose(first.hamiltonian_initials, [0.5, 2.0])
    assert first.max_hamiltonian_drift < 1e-12
    assert np.isclose(first.wavefront_records(snapshot_stride=2)[-1]["time"], 0.2)

    bounds = ray_bundle_coordinate_bounds(first.rays, coordinate_count=2)
    assert set(bounds) == {"x", "y", "z"}
    assert np.allclose(bounds["x"], [-1.0, -0.6])


def test_variable_speed_wavefront_export_shape_and_hamiltonian_drift() -> None:
    trajectory = generate_variable_speed_wavefront(
        ray_count=9,
        t_span=(0.0, 1.0),
        dt=0.01,
        snapshot_stride=20,
    )

    assert trajectory.state_names == ("x", "y", "xi", "eta")
    assert trajectory.states.shape == (101, 4)
    assert trajectory.metadata is not None
    assert trajectory.metadata["kind"] == "ray-bundle"

    bundle = trajectory.metadata["rayBundle"]
    assert bundle["stateNames"] == ["x", "y", "xi", "eta"]
    assert len(bundle["rays"]) == 9
    assert np.asarray(bundle["rays"][0]["states"], dtype=float).shape == (101, 4)

    wavefronts = trajectory.metadata["wavefronts"]
    assert len(wavefronts) == 6
    assert np.asarray(wavefronts[0]["points"], dtype=float).shape == (9, 2)

    hints = trajectory.metadata["rendererHints"]
    assert set(hints["bounds"]) == {"x", "y", "z"}
    assert hints["referenceGeometry"][0]["kind"] == "slowSpeedLens"

    assert trajectory.metadata["hamiltonian"]["maxDrift"] < 1e-8
    assert max(trajectory.series["p"]) - min(trajectory.series["p"]) < 1e-8


def test_variable_speed_wavefront_bundle_is_symmetric() -> None:
    trajectory = generate_variable_speed_wavefront(
        ray_count=7,
        y_span=(-1.2, 1.2),
        t_span=(0.0, 1.2),
        dt=0.01,
    )
    rays = [
        np.asarray(ray["states"], dtype=float)
        for ray in trajectory.metadata["rayBundle"]["rays"]
    ]

    lower = rays[0]
    upper = rays[-1]
    assert np.max(np.abs(lower[:, 0] - upper[:, 0])) < 1e-10
    assert np.max(np.abs(lower[:, 1] + upper[:, 1])) < 1e-10
    assert np.max(np.abs(lower[:, 2] - upper[:, 2])) < 1e-10
    assert np.max(np.abs(lower[:, 3] + upper[:, 3])) < 1e-10
