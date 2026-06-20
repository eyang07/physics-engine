from __future__ import annotations

import numpy as np

from engine.export import SCALAR_FIELD_HINT, system_entry
from scripts.example_specs import VIBRATING_STRING
from scripts.generate_vibrating_string import generate_vibrating_string
from systems.vibrating_string import (
    BoundaryConditions,
    build_system,
    dalembert_solution,
    gaussian_profile,
    modal_energy,
    right_traveling_velocity_antiderivative,
)


def test_fixed_string_frequencies_match_closed_form() -> None:
    system = build_system(length=2.0, wave_speed=3.0)
    frequencies = [float(system.frequency(n)) for n in range(1, 5)]
    expected = [n * 3.0 / (2.0 * 2.0) for n in range(1, 5)]
    assert np.allclose(frequencies, expected)


def test_free_and_mixed_boundary_wavenumbers_match_closed_forms() -> None:
    free = build_system(length=2.0, boundary=BoundaryConditions("free", "free"))
    mixed = build_system(length=2.0, boundary=BoundaryConditions("fixed", "free"))

    assert np.isclose(float(free.mode_wavenumber(2)), np.pi)
    assert np.isclose(float(mixed.mode_wavenumber(1)), np.pi / 4.0)


def test_dalembert_solution_reproduces_right_traveling_profile() -> None:
    x = np.linspace(-1.0, 1.0, 200)
    time = np.linspace(0.0, 0.5, 20)
    wave_speed = 1.3
    profile = gaussian_profile(center=-0.2, width=0.15)
    solution = dalembert_solution(
        x,
        time,
        wave_speed=wave_speed,
        initial_displacement=profile,
        initial_velocity_antiderivative=right_traveling_velocity_antiderivative(
            wave_speed=wave_speed,
            profile=profile,
        ),
    )
    expected = profile(x[np.newaxis, :] - wave_speed * time[:, np.newaxis])
    assert np.allclose(solution, expected, atol=1e-12)


def test_modal_energy_is_measured_constant_to_tolerance() -> None:
    system = build_system()
    x = np.linspace(0.0, 1.0, 257)
    time = np.linspace(0.0, 2.0, 241)
    energy = modal_energy(
        system,
        x,
        time,
        [0.18, 0.08, 0.045],
        parameters={"L": 1.0, "c": 1.0, "rho": 1.0},
    )
    relative_drift = np.max(np.abs(energy - energy[0])) / energy[0]
    assert relative_drift < 2e-3


def test_vibrating_string_manifest_declares_field_series_and_modes() -> None:
    entry = system_entry(VIBRATING_STRING)
    assert entry["systemKind"] == "field-evolution"
    assert "physics" not in entry
    assert "dynamics" not in entry
    assert entry["normalModes"]["boundary"] == "fixed-fixed"
    assert [channel["kind"] for channel in entry["fields"]] == [
        "scalar-field-series",
        "scalar-field-series",
    ]
    assert all(channel["rendererHint"] == SCALAR_FIELD_HINT for channel in entry["fields"])


def test_generated_vibrating_string_exports_displacement_series_and_energy_metadata() -> None:
    trajectory = generate_vibrating_string(sample_count=33, time_count=31)
    assert trajectory.metadata is not None
    assert trajectory.metadata["kind"] == "field-evolution"
    assert trajectory.series is not None

    standing = trajectory.metadata["fields"]["standingDisplacement"]
    traveling = trajectory.metadata["fields"]["travelingDisplacement"]
    assert standing["rendererHint"] == SCALAR_FIELD_HINT
    assert standing["shape"] == [31, 33]
    assert np.asarray(standing["values"]).shape == (31, 33)
    assert traveling["variant"] == "dalembert-right-traveling-gaussian"
    assert trajectory.metadata["energyDiagnostics"]["rigor"] == "measured"
    assert trajectory.metadata["energyDiagnostics"]["residuals"][0]["maxRelative"] < 3e-3
