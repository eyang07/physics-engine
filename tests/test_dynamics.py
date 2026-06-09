from __future__ import annotations

import math

import numpy as np
import sympy as sp

from engine.numerics import integrate_adaptive
from scripts.example_specs import LORENZ
from scripts.generate_lorenz_attractor import generate_lorenz_trajectory
from engine.export.manifest import system_entry
from systems.lorenz_attractor import build_system


def test_lorenz_symbolic_rhs_divergence_and_jacobian() -> None:
    system = build_system()
    x, y, z = system.state
    sigma, rho, beta = system.parameters

    assert system.rhs == (
        sigma * (y - x),
        x * (rho - z) - y,
        x * y - beta * z,
    )
    assert sp.simplify(system.divergence() + sigma + beta + 1) == 0
    assert system.jacobian() == sp.Matrix(
        [
            [-sigma, sigma, 0],
            [rho - z, -1, -x],
            [y, x, -beta],
        ]
    )


def test_lorenz_fixed_points_and_eigenvalues() -> None:
    system = build_system(sigma=10, rho=28, beta=sp.Rational(8, 3))
    fixed_points = system.fixed_points()
    assert len(fixed_points) == 3

    x, y, z = system.state
    side = math.sqrt((8.0 / 3.0) * 27.0)
    coordinates = sorted(
        (round(float(point[x]), 6), round(float(point[y]), 6), round(float(point[z]), 6))
        for point in fixed_points
    )
    assert coordinates == [
        (-round(side, 6), -round(side, 6), 27.0),
        (0.0, 0.0, 0.0),
        (round(side, 6), round(side, 6), 27.0),
    ]

    for point in fixed_points:
        eigenvalues = system.eigenvalues_at(point)
        assert sum(eigenvalues.values()) == 3


def test_integrate_adaptive_discards_transient_and_samples_uniformly() -> None:
    time, states = integrate_adaptive(
        lambda _t, state: np.asarray([-state[0]], dtype=float),
        [1.0],
        (0.0, 2.0),
        transient=0.5,
        sample_dt=0.1,
    )

    assert time[0] == 0.0
    assert np.allclose(np.diff(time), 0.1)
    assert states.shape == (16, 1)
    assert states[0, 0] < 1.0


def test_lorenz_export_metadata_and_series() -> None:
    trajectory = generate_lorenz_trajectory(t_span=(0.0, 10.0), transient=2.0, sample_dt=0.02)

    assert trajectory.state_names == ("x", "y", "z")
    assert trajectory.states.shape[1] == 3
    assert set(trajectory.series or {}) == {"speed", "radius", "ftle", "lyapunov_local_growth"}
    assert len(trajectory.series["speed"]) == len(trajectory.time)
    assert len(trajectory.series["ftle"]) == len(trajectory.time)
    assert len(trajectory.series["lyapunov_local_growth"]) == len(trajectory.time)
    assert trajectory.series["ftle"][0] == 0.0
    assert trajectory.series["ftle"][-1] > 0.0
    assert trajectory.metadata["kind"] == "first-order-flow"
    assert trajectory.metadata["divergence"] == -(10.0 + 1.0 + 8.0 / 3.0)
    assert set(trajectory.metadata["bounds"]) == {"x", "y", "z"}
    assert len(trajectory.metadata["fixedPoints"]) == 3
    lyapunov = trajectory.metadata["diagnostics"]["lyapunov"]
    assert lyapunov["kind"] == "finite-time-largest"
    assert lyapunov["method"] == "sampled-variational-jacobian"
    assert lyapunov["series"] == "ftle"
    assert lyapunov["localGrowthSeries"] == "lyapunov_local_growth"
    assert lyapunov["sampleCount"] == len(trajectory.time)
    assert lyapunov["finalEstimate"] == trajectory.series["ftle"][-1]
    hints = trajectory.metadata["rendererHints"]
    assert hints["transform"]["scale"] > 0
    assert hints["referenceGeometry"][0]["kind"] == "guideRings"
    assert hints["referenceGeometry"][1]["kind"] == "fixedPointMarkers"


def test_lorenz_manifest_registration() -> None:
    entry = system_entry(LORENZ)

    assert entry["id"] == "lorenz-attractor"
    assert entry["systemKind"] == "first-order-flow"
    assert entry["lenses"] == ["lorenzAttractor"]
    assert entry["conserved"] == []
    assert "physics" not in entry
    assert "derivation" not in entry
    assert len(entry["dynamics"]["vector_field"]) == 3
