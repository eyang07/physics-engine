"""The manifest is a contract; these tests guard it against drift.

The most valuable check is structural: a spec's declared state schema and
projections must agree with the system the engine actually builds, so adding or
editing a system can't silently desync the viewer.
"""

from __future__ import annotations

import pytest

from engine.export.manifest import build_manifest, system_entry
from scripts.example_specs import SPECS


@pytest.fixture(scope="module")
def manifest() -> dict:
    return build_manifest(SPECS)


def test_ids_are_unique() -> None:
    ids = [spec.id for spec in SPECS]
    assert len(ids) == len(set(ids))


@pytest.mark.parametrize("spec", SPECS, ids=[spec.id for spec in SPECS])
def test_state_schema_matches_system(spec) -> None:
    """The coordinate/velocity prefix of the state must match the system's q, qdot."""

    system = spec.build()
    coordinates = [variable.name for variable in spec.state if variable.kind == "coordinate"]
    velocities = [variable.name for variable in spec.state if variable.kind == "velocity"]

    assert coordinates == [symbol.name for symbol in system.q]
    assert velocities == [symbol.name for symbol in system.qdot]


@pytest.mark.parametrize("spec", SPECS, ids=[spec.id for spec in SPECS])
def test_projections_reference_known_state(spec) -> None:
    known = {variable.name for variable in spec.state}
    for group in spec.projections.values():
        assert set(group) <= known


@pytest.mark.parametrize("spec", SPECS, ids=[spec.id for spec in SPECS])
def test_physical_parameters_appear_in_lagrangian(spec) -> None:
    system = spec.build()
    free_names = {symbol.name for symbol in system.lagrangian.free_symbols}
    for parameter in spec.parameters:
        if parameter.role == "physical":
            assert parameter.name in free_names


@pytest.mark.parametrize("spec", SPECS, ids=[spec.id for spec in SPECS])
def test_parameter_defaults_within_range(spec) -> None:
    for parameter in spec.parameters:
        assert parameter.minimum <= parameter.default <= parameter.maximum


@pytest.mark.parametrize("spec", SPECS, ids=[spec.id for spec in SPECS])
def test_entry_carries_symbolic_physics(spec) -> None:
    entry = system_entry(spec)
    physics = entry["physics"]

    assert isinstance(physics["lagrangian"], str) and physics["lagrangian"]
    assert isinstance(physics["energy"], str) and physics["energy"]
    assert physics["euler_lagrange"] and all(isinstance(eq, str) for eq in physics["euler_lagrange"])
    # Every example here is a regular Lagrangian, so the Legendre transform exists.
    assert isinstance(physics["hamiltonian"], str) and physics["hamiltonian"]

    assert entry["lenses"], "every system needs at least one visualization lens"
    assert entry["dataPath"].startswith("/data/")


@pytest.mark.parametrize("spec", SPECS, ids=[spec.id for spec in SPECS])
def test_conserved_quantities_render(spec) -> None:
    entry = system_entry(spec)
    assert entry["conserved"], "each system should declare at least one invariant"
    for quantity in entry["conserved"]:
        assert quantity["latex"]
        assert quantity["symmetry"]
        if "expression_latex" in quantity:
            assert quantity["expression_latex"]


def test_manifest_lists_every_spec(manifest) -> None:
    assert manifest["version"] == 1
    assert [entry["id"] for entry in manifest["systems"]] == [spec.id for spec in SPECS]
