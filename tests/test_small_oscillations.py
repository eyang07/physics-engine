from __future__ import annotations

import json

import numpy as np
import pytest
import sympy as sp

from engine.dynamics import invariant_residuals
from engine.export.manifest import build_manifest
from engine.mechanics import normal_modes
from scripts.example_specs import COUPLED_OSCILLATORS, LENSES
from scripts.generate_coupled_oscillators import (
    generate_coupled_oscillator_trajectory,
    write_coupled_oscillator_trajectory,
)
from systems.coupled_oscillators import build_chain_system, build_system


def _expected_fixed_chain_frequencies(count: int, mass: float, spring: float) -> np.ndarray:
    indices = np.arange(1, count + 1, dtype=float)
    return 2.0 * np.sqrt(spring / mass) * np.sin(indices * np.pi / (2.0 * (count + 1)))


def _expected_fixed_chain_modes(count: int) -> np.ndarray:
    rows = np.arange(1, count + 1, dtype=float)[:, None]
    columns = np.arange(1, count + 1, dtype=float)[None, :]
    raw = np.sin(rows * columns * np.pi / (count + 1))
    return raw / np.linalg.norm(raw, axis=0, keepdims=True)


def test_small_oscillation_helper_recovers_two_mass_pair() -> None:
    m, k = sp.symbols("m k", positive=True)
    system = build_chain_system(count=2, mass=m, spring_constant=k)
    result = normal_modes(
        system,
        {coordinate: 0 for coordinate in system.q},
        substitutions={m: 2.0, k: 8.0},
    )

    assert np.allclose(result.mass_matrix, np.diag([2.0, 2.0]))
    assert np.allclose(result.stiffness_matrix, [[16.0, -8.0], [-8.0, 16.0]])
    assert np.allclose(result.frequencies, [2.0, np.sqrt(12.0)])
    assert np.allclose(np.abs(result.mode_shapes), np.full((2, 2), 0.5))


def test_small_oscillation_helper_recovers_fixed_chain_modes() -> None:
    count = 4
    system = build_chain_system(count=count, mass=1.0, spring_constant=1.0)
    result = normal_modes(system, {coordinate: 0.0 for coordinate in system.q})

    assert np.allclose(result.frequencies, _expected_fixed_chain_frequencies(count, 1.0, 1.0))
    assert np.allclose(
        np.abs(result.mode_shapes),
        np.abs(_expected_fixed_chain_modes(count)),
    )


def test_coupled_oscillator_manifest_carries_mode_shapes_and_frequencies() -> None:
    manifest = build_manifest((COUPLED_OSCILLATORS,), LENSES)
    entry = manifest["systems"][0]

    assert entry["id"] == "coupled-oscillators"
    modes = entry["normalModes"]
    assert modes["method"] == "small-oscillation-generalized-eigenproblem"
    assert modes["coordinates"] == ["x1", "x2", "x3", "x4"]
    assert np.allclose(modes["frequencies"], _expected_fixed_chain_frequencies(4, 1.0, 1.0))
    assert np.asarray(modes["modeShapes"], dtype=float).shape == (4, 4)


def test_coupled_oscillator_mode_superposition_conserves_energy_measured() -> None:
    trajectory = generate_coupled_oscillator_trajectory(t_span=(0.0, 12.0), dt=0.01)

    assert trajectory.state_names == (
        "x1",
        "x2",
        "x3",
        "x4",
        "x1_dot",
        "x2_dot",
        "x3_dot",
        "x4_dot",
    )
    assert trajectory.series is not None
    residual = invariant_residuals({"H": trajectory.series["H"]})["H"]
    assert residual.max_abs < 1e-8

    metadata = trajectory.metadata or {}
    records = {record["name"]: record for record in metadata["invariantResiduals"]}
    assert records["H"]["rigor"] == "measured"
    assert records["H"]["maxAbs"] < 1e-8
    assert metadata["normalModes"]["coordinates"] == ["x1", "x2", "x3", "x4"]


def test_generate_coupled_oscillator_script_writes_outputs(tmp_path) -> None:
    output = tmp_path / "data" / "coupled_oscillators.json"
    viewer_output = tmp_path / "viewer" / "public" / "data" / "coupled_oscillators.json"

    trajectory = write_coupled_oscillator_trajectory(
        output,
        viewer_output=viewer_output,
        t_end=0.05,
        dt=0.01,
    )

    assert output.exists()
    assert viewer_output.exists()
    assert json.loads(output.read_text(encoding="utf-8")) == json.loads(
        viewer_output.read_text(encoding="utf-8")
    )
    assert len(trajectory.time) == 6


def test_coupled_oscillator_system_rejects_empty_chain() -> None:
    with pytest.raises(ValueError, match="positive integer"):
        build_chain_system(count=0)


def test_default_coupled_oscillator_system_has_four_masses() -> None:
    system = build_system()
    assert [symbol.name for symbol in system.q] == ["x1", "x2", "x3", "x4"]
