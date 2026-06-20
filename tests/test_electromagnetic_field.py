from __future__ import annotations

import numpy as np
import sympy as sp

from engine.export import FIELD_LINES_HINT, SCALAR_FIELD_HINT, VECTOR_FIELD_HINT, system_entry
from scripts.example_specs import ELECTROMAGNETIC_FIELD
from scripts.generate_electromagnetic_field import generate_electromagnetic_field
from systems.electromagnetic_field import (
    current_loop_axis_field,
    magnetic_dipole_field,
    point_charge_electric_field,
    point_charge_potential,
)


def test_point_charge_closed_forms_match_coulomb_law() -> None:
    x, y = sp.symbols("x y", real=True)
    potential = point_charge_potential(
        (x, y),
        charge=sp.Integer(2),
        position=(sp.Integer(0), sp.Integer(0)),
        epsilon0=sp.Integer(1),
    )
    electric = point_charge_electric_field(
        (x, y),
        charge=sp.Integer(2),
        position=(sp.Integer(0), sp.Integer(0)),
        epsilon0=sp.Integer(1),
    )

    assert sp.simplify(potential.expression.subs({x: 2, y: 0}) - 1 / (4 * sp.pi)) == 0
    assert sp.simplify(electric.components[0].subs({x: 2, y: 0}) - 1 / (8 * sp.pi)) == 0
    assert sp.simplify(electric.components[1].subs({x: 2, y: 0})) == 0
    assert electric.components == tuple(-component for component in potential.gradient().components)


def test_magnetic_dipole_and_current_loop_closed_forms() -> None:
    x, y, z = sp.symbols("x y z", real=True)
    magnetic = magnetic_dipole_field((x, y), moment=sp.Integer(3), mu0=sp.Integer(1))
    assert sp.simplify(magnetic.components[0].subs({x: 0, y: 2})) == 0
    assert sp.simplify(magnetic.components[1].subs({x: 0, y: 2}) - 3 / (16 * sp.pi)) == 0

    axis_field = current_loop_axis_field(
        z,
        current=sp.Integer(5),
        radius=sp.Integer(2),
        mu0=sp.Integer(7),
    )
    assert sp.simplify(axis_field.subs(z, 0) - sp.Rational(35, 4)) == 0


def test_static_field_manifest_declares_channels_without_dynamics() -> None:
    entry = system_entry(ELECTROMAGNETIC_FIELD)

    assert entry["systemKind"] == "static-field"
    assert "physics" not in entry
    assert "dynamics" not in entry
    assert entry["fieldModel"]["kind"] == "electromagnetic-static"
    assert [channel["rendererHint"] for channel in entry["fields"]] == [
        SCALAR_FIELD_HINT,
        VECTOR_FIELD_HINT,
        FIELD_LINES_HINT,
        VECTOR_FIELD_HINT,
        FIELD_LINES_HINT,
    ]


def test_generated_electromagnetic_field_payload_is_finite_and_directed() -> None:
    trajectory = generate_electromagnetic_field()
    assert trajectory.metadata is not None
    assert trajectory.metadata["kind"] == "static-field"

    fields = trajectory.metadata["fields"]
    potential = fields["electricPotential"]
    electric = fields["electricField"]
    magnetic = fields["magneticField"]
    electric_lines = fields["electricFieldLines"]

    assert potential["rendererHint"] == SCALAR_FIELD_HINT
    assert electric["rendererHint"] == VECTOR_FIELD_HINT
    assert magnetic["rendererHint"] == VECTOR_FIELD_HINT
    assert electric_lines["rendererHint"] == FIELD_LINES_HINT
    assert np.all(np.isfinite(np.asarray(potential["values"], dtype=float)))
    assert np.all(np.isfinite(np.asarray(electric["components"], dtype=float)))
    assert np.all(np.isfinite(np.asarray(magnetic["components"], dtype=float)))

    parameters = trajectory.metadata["parameters"]
    positive_charge = np.array([-parameters["d"] / 2.0, 0.0])
    negative_charge = np.array([parameters["d"] / 2.0, 0.0])
    middle_line = np.asarray(electric_lines["lines"][len(electric_lines["lines"]) // 2])

    assert np.linalg.norm(middle_line[0] - positive_charge) < 0.25
    assert np.linalg.norm(middle_line[-1] - negative_charge) < 0.12
    assert middle_line[-1, 0] > middle_line[0, 0]
