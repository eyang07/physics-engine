from __future__ import annotations

import numpy as np
import pytest
import sympy as sp

from engine.dynamics import (
    ScalarSpeedMedium,
    caustic_proximity,
    integrate_ray_bundle,
    ray_bundle_diagnostics,
    ray_bundle_snapshot_indices,
    ray_spreading_factors,
    ray_travel_times,
    wavefront_envelope_records,
)
from scripts.generate_variable_speed_wavefront import generate_variable_speed_wavefront
from systems.variable_speed_wavefront import build_system, wave_speed


def _homogeneous_bundle(speed: float = 2.0, ray_count: int = 5):
    x, y = sp.symbols("x y", real=True)
    medium = ScalarSpeedMedium(coordinates=(x, y), speed=sp.Float(speed))
    system = medium.to_system()
    initial_states = [
        [0.0, float(y0), 1.0 / speed, 0.0]
        for y0 in np.linspace(-1.0, 1.0, ray_count)
    ]
    return integrate_ray_bundle(
        system,
        initial_states,
        t_span=(0.0, 1.0),
        dt=0.05,
        state_names=["x", "y", "xi_x", "xi_y"],
    )


def _lens_bundle(t_span=(0.0, 8.0), ray_count: int = 9):
    system = build_system(base_speed=1.0, lens_strength=0.42, lens_width=0.85)
    initial_states = []
    for y0 in np.linspace(-0.8, 0.8, ray_count):
        speed = float(
            wave_speed(
                sp.Float(-3.0),
                sp.Float(y0),
                base_speed=1.0,
                lens_strength=0.42,
                lens_width=0.85,
            )
        )
        initial_states.append([-3.0, float(y0), 1.0 / speed, 0.0])
    return integrate_ray_bundle(
        system,
        initial_states,
        t_span=t_span,
        dt=0.01,
        state_names=["x", "y", "xi", "eta"],
    )


def test_travel_time_in_homogeneous_medium_equals_flow_parameter() -> None:
    # On the level set p = 1/2 (|xi| = 1/c), the flow parameter is the
    # physical travel time, and with constant integrand the trapezoid rule
    # is exact up to floating point.
    bundle = _homogeneous_bundle()
    phases = ray_travel_times(bundle.rays, coordinate_count=2)

    assert phases.shape == bundle.rays.shape[:2]
    assert np.allclose(phases, bundle.time[None, :], atol=1e-12)


def test_travel_time_matches_degree_two_homogeneous_model() -> None:
    # For p = c(q)^2 |xi|^2 / 2 (degree 2 in xi), the exact phase is
    # 2 * p0 * s; the measured deviation is integration error only.
    bundle = _lens_bundle()
    phases = ray_travel_times(bundle.rays, coordinate_count=2)
    expected = 2.0 * bundle.hamiltonian_initials[:, None] * bundle.time[None, :]

    assert float(np.max(np.abs(phases - expected))) < 1e-4


def test_parallel_bundle_keeps_unit_spreading_and_constant_envelope() -> None:
    bundle = _homogeneous_bundle()

    factors = ray_spreading_factors(bundle.rays, coordinate_count=2)
    assert factors.shape == (4, len(bundle.time))
    assert np.allclose(factors, 1.0, atol=1e-12)

    records = wavefront_envelope_records(
        bundle.rays,
        bundle.time,
        coordinate_count=2,
        snapshot_stride=5,
    )
    assert [record["time"] for record in records][-1] == bundle.time[-1]
    for record in records:
        assert np.isclose(record["arcLength"], 2.0, atol=1e-12)
        assert record["minSpreadingFactor"] == pytest.approx(1.0)
        assert record["maxSpreadingFactor"] == pytest.approx(1.0)
        assert set(record["bounds"]) == {"x", "y"}
        assert record["bounds"]["y"] == pytest.approx([-1.0, 1.0])


def test_gaussian_lens_bundle_focuses_downstream_of_lens() -> None:
    # Measured behavior: the slow-speed lens is converging, so the bundle
    # passes near a caustic behind the lens (x > 0) close to the axis.
    bundle = _lens_bundle()
    caustic = caustic_proximity(bundle.rays, bundle.time, coordinate_count=2)

    assert caustic["minSpreadingFactor"] < 0.01
    assert 0.0 < caustic["time"] < bundle.time[-1]
    assert caustic["location"][0] > 0.0
    assert abs(caustic["location"][1]) < 0.05
    assert len(caustic["minSeries"]) == len(bundle.time)


def test_ray_diagnostics_validation() -> None:
    bundle = _homogeneous_bundle(ray_count=5)

    with pytest.raises(ValueError, match="at least two rays"):
        ray_spreading_factors(bundle.rays[:1], coordinate_count=2)

    coincident = np.stack([bundle.rays[0], bundle.rays[0]], axis=0)
    with pytest.raises(ValueError, match="distinct positions"):
        ray_spreading_factors(coincident, coordinate_count=2)

    with pytest.raises(ValueError, match="shape"):
        ray_travel_times(bundle.rays[0], coordinate_count=2)


def test_ray_bundle_diagnostics_export_shape() -> None:
    bundle = _homogeneous_bundle()
    diagnostics = ray_bundle_diagnostics(bundle, snapshot_stride=5, symbol_degree=2)

    assert set(diagnostics) == {"travelTime", "causticProximity", "wavefrontEnvelope"}

    travel_time = diagnostics["travelTime"]
    assert len(travel_time["final"]) == bundle.rays.shape[0]
    assert travel_time["residualMax"] < 1e-12
    snapshot_count = len(ray_bundle_snapshot_indices(len(bundle.time), 5))
    assert len(travel_time["center"]["time"]) == snapshot_count
    assert len(travel_time["center"]["value"]) == snapshot_count

    caustic = diagnostics["causticProximity"]
    assert caustic["method"] == "adjacent-ray finite-difference spreading factors"
    assert len(caustic["minSeries"]["time"]) == snapshot_count
    assert len(caustic["minSeries"]["value"]) == snapshot_count

    assert len(diagnostics["wavefrontEnvelope"]) == snapshot_count


def test_wavefront_generator_exports_ray_diagnostics() -> None:
    trajectory = generate_variable_speed_wavefront(
        ray_count=9,
        t_span=(0.0, 1.0),
        dt=0.01,
        snapshot_stride=20,
    )

    diagnostics = trajectory.metadata["rayDiagnostics"]
    assert set(diagnostics) == {"travelTime", "causticProximity", "wavefrontEnvelope"}
    assert diagnostics["travelTime"]["residualMax"] < 1e-4
    assert len(diagnostics["wavefrontEnvelope"]) == len(trajectory.metadata["wavefronts"])
    for envelope, wavefront in zip(
        diagnostics["wavefrontEnvelope"], trajectory.metadata["wavefronts"], strict=True
    ):
        assert envelope["time"] == pytest.approx(wavefront["time"])
