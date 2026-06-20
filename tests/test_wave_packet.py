from __future__ import annotations

import numpy as np

from engine.export import SCALAR_FIELD_HINT, system_entry
from scripts.example_specs import WAVE_PACKET
from scripts.generate_wave_packet import DEFAULT_PARAMETERS, generate_wave_packet
from systems.wave_packet import build_system, envelope_width, numeric_velocities, packet_fields


def test_quadratic_dispersion_phase_and_group_velocities() -> None:
    packet = build_system(alpha=0.25, k0=4.0)
    phase_velocity, group_velocity = numeric_velocities(
        packet,
        parameters={"alpha": 0.25, "k0": 4.0, "sigma": 1.0, "x0": 0.0},
    )
    assert np.isclose(phase_velocity, 1.0)
    assert np.isclose(group_velocity, 2.0)


def test_gaussian_packet_spreading_matches_analytic_envelope() -> None:
    packet = build_system()
    time = np.linspace(0.0, 4.0, 11)
    widths = envelope_width(packet, time, parameters=DEFAULT_PARAMETERS)
    expected = DEFAULT_PARAMETERS["sigma"] * np.sqrt(
        1.0
        + (2.0 * DEFAULT_PARAMETERS["alpha"] * time / DEFAULT_PARAMETERS["sigma"] ** 2) ** 2
    )
    assert np.allclose(widths, expected)
    assert widths[-1] > widths[0]


def test_packet_fields_move_with_group_velocity() -> None:
    packet = build_system()
    x = np.linspace(-3.0, 4.0, 401)
    time = np.array([0.0, 3.0])
    _amplitude, intensity, _widths = packet_fields(packet, x, time, parameters=DEFAULT_PARAMETERS)
    _phase_velocity, group_velocity = numeric_velocities(packet, parameters=DEFAULT_PARAMETERS)
    peaks = x[np.argmax(intensity, axis=1)]
    assert np.allclose(peaks[1] - peaks[0], group_velocity * 3.0, atol=0.02)


def test_wave_packet_manifest_declares_amplitude_and_intensity() -> None:
    entry = system_entry(WAVE_PACKET)
    assert entry["systemKind"] == "field-evolution"
    assert "physics" not in entry
    assert "dynamics" not in entry
    assert [channel["name"] for channel in entry["fields"]] == ["amplitude", "intensity"]
    assert all(channel["rendererHint"] == SCALAR_FIELD_HINT for channel in entry["fields"])


def test_generated_wave_packet_exports_fields_and_diagnostics() -> None:
    trajectory = generate_wave_packet(sample_count=41, time_count=21)
    assert trajectory.metadata is not None
    assert trajectory.metadata["kind"] == "field-evolution"
    fields = trajectory.metadata["fields"]
    assert fields["amplitude"]["kind"] == "scalar-field-series"
    assert fields["amplitude"]["shape"] == [21, 41]
    assert fields["intensity"]["shape"] == [21, 41]
    diagnostics = trajectory.metadata["diagnostics"]
    assert diagnostics["rigor"] == "measured"
    assert diagnostics["groupVelocity"] == 2 * DEFAULT_PARAMETERS["alpha"] * DEFAULT_PARAMETERS["k0"]
    assert diagnostics["width"][-1] > diagnostics["width"][0]
