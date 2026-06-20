from __future__ import annotations

import numpy as np
import pytest
import sympy as sp

from engine.export import (
    FIELD_LINES_HINT,
    SCALAR_FIELD_HINT,
    VECTOR_FIELD_HINT,
    SystemSpec,
    field_lines,
    scalar_field_grid,
    system_entry,
    vector_field_grid,
)
from engine.export.manifest import Conserved, Parameter, StateVar
from engine.fields import ScalarField, VectorField


def test_scalar_field_grid_is_deterministic_and_labels_hint() -> None:
    x, y = sp.symbols("x y", real=True)
    field = ScalarField((x, y), x**2 + y)
    axes = [np.linspace(-1.0, 1.0, 5), np.linspace(0.0, 2.0, 4)]

    payload = scalar_field_grid(field, axes, name="phi")
    assert payload["rendererHint"] == SCALAR_FIELD_HINT
    assert payload["coordinates"] == ["x", "y"]
    assert payload["shape"] == [5, 4]
    assert payload["evaluation"] == "symbolic-exact"
    gx, gy = np.meshgrid(axes[0], axes[1], indexing="ij")
    assert np.allclose(np.asarray(payload["values"]), gx**2 + gy)
    # Determinism: same inputs reproduce the same payload exactly.
    assert scalar_field_grid(field, axes, name="phi") == payload


def test_vector_field_grid_carries_components_and_magnitude() -> None:
    x, y = sp.symbols("x y", real=True)
    field = VectorField((x, y), (-y, x))
    axes = [np.linspace(-1.0, 1.0, 3), np.linspace(-1.0, 1.0, 3)]

    payload = vector_field_grid(field, axes, name="circulation")
    assert payload["rendererHint"] == VECTOR_FIELD_HINT
    assert payload["dimension"] == 2
    components = np.asarray(payload["components"])
    magnitude = np.asarray(payload["magnitude"])
    assert components.shape == (3, 3, 2)
    assert np.allclose(magnitude, np.linalg.norm(components, axis=-1))


def test_field_lines_payload_validates_dimension() -> None:
    line = [[0.0, 0.0], [0.1, 0.2], [0.3, 0.25]]
    payload = field_lines([line], name="lines", dimension=2, seeds=[[0.0, 0.0]])
    assert payload["rendererHint"] == FIELD_LINES_HINT
    assert payload["count"] == 1
    assert payload["dimension"] == 2
    assert np.asarray(payload["lines"][0]).shape == (3, 2)
    assert payload["seeds"] == [[0.0, 0.0]]

    with pytest.raises(ValueError, match="shape"):
        field_lines([[[0.0, 0.0, 0.0]]], name="bad", dimension=2)


def test_manifest_declares_field_channels_and_hints() -> None:
    spec = SystemSpec(
        id="field-demo",
        title="Field Demo",
        category="Fields",
        description="A spec that declares field channels.",
        build=lambda: _stub_system(),
        parameters=(Parameter("m", "m", 1.0, 0.2, 3.0),),
        state=(StateVar("x", "x", "coordinate"), StateVar("x_dot", r"\dot{x}", "velocity")),
        projections={"phase": ("x", "x_dot")},
        conserved=(),
        lenses=(),
        data_path="/data/field_demo.json",
        fields=(
            {"name": "potential", "kind": SCALAR_FIELD_HINT, "rendererHint": SCALAR_FIELD_HINT,
             "source": "trajectory.metadata.fields.potential"},
            {"name": "fieldLines", "kind": FIELD_LINES_HINT, "rendererHint": FIELD_LINES_HINT,
             "source": "trajectory.metadata.fields.fieldLines"},
        ),
    )
    entry = system_entry(spec)
    assert [channel["rendererHint"] for channel in entry["fields"]] == [
        SCALAR_FIELD_HINT,
        FIELD_LINES_HINT,
    ]


def _stub_system():
    from engine.mechanics import LagrangianSystem
    from engine.mechanics.coordinates import CoordinateChart

    chart = CoordinateChart.from_names("x")
    (x,) = chart.coordinates
    (x_dot,) = chart.velocities
    return LagrangianSystem(
        coordinates=chart.coordinates,
        velocities=chart.velocities,
        lagrangian=sp.Rational(1, 2) * x_dot**2 - sp.Rational(1, 2) * x**2,
        time=chart.time,
    )
