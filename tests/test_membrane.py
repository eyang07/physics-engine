from __future__ import annotations

import numpy as np
from scipy.special import jn_zeros

from engine.export import SCALAR_FIELD_HINT, system_entry
from scripts.example_specs import MEMBRANE
from scripts.generate_membrane import generate_membrane
from systems.membrane import (
    CircularMode,
    RectangularMode,
    build_system,
    circular_mode_values,
    rectangular_mode_values,
)


def test_rectangular_membrane_frequency_matches_closed_form() -> None:
    system = build_system(width=2.0, height=1.0, wave_speed=3.0)
    mode = RectangularMode(2, 3)
    expected = 3.0 / 2.0 * np.sqrt((2 / 2.0) ** 2 + (3 / 1.0) ** 2)
    assert np.isclose(float(system.rectangular_frequency(mode)), expected)


def test_circular_membrane_frequency_uses_bessel_zero() -> None:
    system = build_system(radius=2.0, wave_speed=3.0)
    mode = CircularMode(1, 2)
    zero = jn_zeros(1, 2)[-1]
    assert np.isclose(system.circular_bessel_zero(mode), zero)
    assert np.isclose(float(system.circular_frequency(mode)), 3.0 * zero / (4.0 * np.pi))


def test_mode_shape_grids_have_expected_boundary_values() -> None:
    system = build_system(width=1.0, height=1.0, radius=1.0, wave_speed=1.0)
    axis = np.linspace(0.0, 1.0, 25)
    rectangle = rectangular_mode_values(
        system, RectangularMode(1, 1), axis, axis, parameters={"Lx": 1.0, "Ly": 1.0, "R": 1.0, "c": 1.0}
    )
    assert np.allclose(rectangle[0, :], 0.0)
    assert np.allclose(rectangle[-1, :], 0.0, atol=1e-15)

    circle_axis = np.linspace(-1.0, 1.0, 25)
    circle = circular_mode_values(
        system, CircularMode(0, 1), circle_axis, circle_axis, parameters={"Lx": 1.0, "Ly": 1.0, "R": 1.0, "c": 1.0}
    )
    assert np.isnan(circle[0, 0])
    assert abs(circle[12, 12] - 1.0) < 1e-12


def test_membrane_manifest_declares_modes_and_field_channels() -> None:
    entry = system_entry(MEMBRANE)
    assert entry["systemKind"] == "field-evolution"
    assert entry["normalModes"]["method"] == "analytic-membrane-eigenmodes"
    assert len(entry["normalModes"]["rectangular"]) == 3
    assert len(entry["normalModes"]["circular"]) == 3
    assert [channel["rendererHint"] for channel in entry["fields"]] == [
        SCALAR_FIELD_HINT,
        SCALAR_FIELD_HINT,
        SCALAR_FIELD_HINT,
        SCALAR_FIELD_HINT,
    ]


def test_generated_membrane_exports_static_and_animated_fields() -> None:
    trajectory = generate_membrane(
        rectangular_x_count=13,
        rectangular_y_count=11,
        circular_count=15,
        time_count=9,
    )
    assert trajectory.metadata is not None
    fields = trajectory.metadata["fields"]

    assert fields["rectangularMode11"]["kind"] == "scalar-field"
    assert fields["rectangularMode11"]["shape"] == [13, 11]
    assert fields["circularMode01"]["kind"] == "scalar-field"
    assert fields["circularMode01"]["shape"] == [15, 15]
    assert fields["circularMode01"]["finiteMask"][0][0] is False
    assert fields["rectangularDisplacement"]["kind"] == "scalar-field-series"
    assert fields["rectangularDisplacement"]["shape"] == [9, 13, 11]
    assert fields["circularDisplacement"]["shape"] == [9, 15, 15]
