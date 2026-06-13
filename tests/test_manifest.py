"""The manifest is a contract; these tests guard it against drift.

The most valuable check is structural: a spec's declared state schema and
projections must agree with the system the engine actually builds, so adding or
editing a system can't silently desync the viewer.
"""

from __future__ import annotations

from dataclasses import replace

import pytest

from engine.export import validate_viewer_verification_problems
from engine.export.manifest import build_manifest, system_entry
from engine.dynamics import CotangentHamiltonianSystem
from engine.mechanics.lagrangian import LagrangianSystem
from scripts.example_specs import LENSES, SPECS
from scripts.export_verification_problems import upright_pendulum_problem


@pytest.fixture(scope="module")
def manifest() -> dict:
    return build_manifest(SPECS, LENSES)


def test_ids_are_unique() -> None:
    ids = [spec.id for spec in SPECS]
    assert len(ids) == len(set(ids))


def test_lens_ids_are_unique() -> None:
    ids = [lens.id for lens in LENSES]
    assert len(ids) == len(set(ids))


def test_system_lenses_are_registered() -> None:
    registered = {lens.id for lens in LENSES}
    for spec in SPECS:
        assert set(spec.lenses) <= registered


def test_manifest_has_no_verification_coupling(manifest) -> None:
    # The Systems and Verification worlds are separate: no gallery system carries
    # a verification cross-link, so the manifest stays pure physics.
    for entry in manifest["systems"]:
        assert entry.get("verificationProblems", []) == [], entry["id"]


def test_verification_problems_validate_standalone() -> None:
    validate_viewer_verification_problems((upright_pendulum_problem(),))


def test_verification_problem_is_self_contained() -> None:
    # The verification world does not depend on any gallery system.
    problem = upright_pendulum_problem()
    assert problem.system is None
    geometry = problem.region_geometry[0]
    assert geometry.variable_to_state_axis == {"theta": "theta", "omega": "omega"}


def test_verification_contract_rejects_incomplete_region_geometry() -> None:
    problem = upright_pendulum_problem()
    # Drop one region's geometry so it no longer covers every region.
    bad_problem = replace(problem, region_geometry=problem.region_geometry[1:])

    with pytest.raises(ValueError, match="must cover every region"):
        validate_viewer_verification_problems((bad_problem,))


def test_registered_lens_requirements_match_system_specs() -> None:
    lenses_by_id = {lens.id: lens for lens in LENSES}

    for spec in SPECS:
        projection_names = set(spec.projections)
        conserved_names = {quantity.name for quantity in spec.conserved}
        potential_names = {potential.name for potential in spec.effective_potentials}

        for lens_id in spec.lenses:
            lens = lenses_by_id[lens_id]
            assert set(lens.projections) <= projection_names
            assert set(lens.conserved) <= conserved_names
            assert set(lens.effective_potentials) <= potential_names


@pytest.mark.parametrize("spec", SPECS, ids=[spec.id for spec in SPECS])
def test_state_schema_matches_system(spec) -> None:
    """The coordinate/velocity prefix of the state must match the system's q, qdot."""

    system = spec.build()
    coordinates = [variable.name for variable in spec.state if variable.kind == "coordinate"]
    velocities = [variable.name for variable in spec.state if variable.kind == "velocity"]

    if isinstance(system, LagrangianSystem):
        assert coordinates == [symbol.name for symbol in system.q]
        assert velocities == [symbol.name for symbol in system.qdot]
    elif isinstance(system, CotangentHamiltonianSystem):
        momenta = [variable.name for variable in spec.state if variable.kind == "momentum"]
        assert coordinates == [symbol.name for symbol in system.coordinates]
        assert momenta == [symbol.name for symbol in system.momenta]
        assert velocities == []
    else:
        assert coordinates == [symbol.name for symbol in system.state_symbols]
        assert velocities == []


@pytest.mark.parametrize("spec", SPECS, ids=[spec.id for spec in SPECS])
def test_projections_reference_known_state(spec) -> None:
    known = {variable.name for variable in spec.state}
    for group in spec.projections.values():
        assert set(group) <= known


@pytest.mark.parametrize("spec", SPECS, ids=[spec.id for spec in SPECS])
def test_physical_parameters_appear_in_lagrangian(spec) -> None:
    system = spec.build()
    if isinstance(system, LagrangianSystem):
        free_names = {symbol.name for symbol in system.lagrangian.free_symbols}
    elif isinstance(system, CotangentHamiltonianSystem):
        expressions = system.rhs()
        free_names = {symbol.name for symbol in set().union(*(expr.free_symbols for expr in expressions))}
    else:
        expressions = tuple(system.rhs)
        free_names = {symbol.name for symbol in set().union(*(expr.free_symbols for expr in expressions))}
    for parameter in spec.parameters:
        if parameter.role == "physical":
            assert parameter.name in free_names


@pytest.mark.parametrize("spec", SPECS, ids=[spec.id for spec in SPECS])
def test_parameter_defaults_within_range(spec) -> None:
    for parameter in spec.parameters:
        assert parameter.minimum <= parameter.default <= parameter.maximum


@pytest.mark.parametrize("spec", SPECS, ids=[spec.id for spec in SPECS])
def test_parameter_variants_are_well_formed(spec) -> None:
    entry = system_entry(spec)
    variants = entry.get("variants", [])
    assert len(variants) == len(spec.variants)

    parameter_by_name = {parameter.name: parameter for parameter in spec.parameters}
    ids = [variant["id"] for variant in variants]
    paths = [variant["dataPath"] for variant in variants]
    assert len(ids) == len(set(ids))
    assert len(paths) == len(set(paths))

    for declared, rendered in zip(spec.variants, variants, strict=True):
        assert rendered["id"] == declared.id
        assert rendered["label"] == declared.label
        assert rendered["dataPath"] == declared.data_path
        assert rendered["dataPath"].startswith("/data/")
        assert rendered["dataPath"].endswith(".json")
        assert rendered["parameters"] == declared.parameters
        assert set(rendered["parameters"]) <= set(parameter_by_name)
        for name, value in rendered["parameters"].items():
            parameter = parameter_by_name[name]
            assert parameter.minimum <= value <= parameter.maximum


@pytest.mark.parametrize("spec", SPECS, ids=[spec.id for spec in SPECS])
def test_entry_carries_symbolic_physics(spec) -> None:
    entry = system_entry(spec)
    if entry.get("dynamics"):
        dynamics = entry["dynamics"]
        assert dynamics["vector_field"] and all(
            equation["equation_latex"] for equation in dynamics["vector_field"]
        )
        assert isinstance(dynamics["divergence_latex"], str) and dynamics["divergence_latex"]
        assert isinstance(dynamics["jacobian_latex"], str) and dynamics["jacobian_latex"]
        assert entry["lenses"], "every system needs at least one visualization lens"
        assert entry["dataPath"].startswith("/data/")
        return

    physics = entry["physics"]

    assert isinstance(physics["lagrangian"], str) and physics["lagrangian"]
    assert isinstance(physics["energy"], str) and physics["energy"]
    assert physics["euler_lagrange"] and all(isinstance(eq, str) for eq in physics["euler_lagrange"])
    # Every example here is a regular Lagrangian, so the Legendre transform exists.
    assert isinstance(physics["hamiltonian"], str) and physics["hamiltonian"]

    assert entry["lenses"], "every system needs at least one visualization lens"
    assert entry["dataPath"].startswith("/data/")


@pytest.mark.parametrize("spec", SPECS, ids=[spec.id for spec in SPECS])
def test_effective_potentials_render_when_declared(spec) -> None:
    entry = system_entry(spec)
    assert len(entry["effectivePotentials"]) == len(spec.effective_potentials)

    for declared, rendered in zip(spec.effective_potentials, entry["effectivePotentials"], strict=True):
        state_names = {variable.name for variable in spec.state}
        conserved_names = {quantity.name for quantity in spec.conserved}

        assert rendered["name"] == declared.name
        assert rendered["coordinate"] in state_names
        assert rendered["conserved"] in conserved_names
        assert rendered["latex"]
        assert rendered["conserved_latex"]
        assert rendered["expression_latex"]


@pytest.mark.parametrize("spec", SPECS, ids=[spec.id for spec in SPECS])
def test_entry_carries_structured_derivation(spec) -> None:
    entry = system_entry(spec)
    if entry.get("dynamics"):
        assert "derivation" not in entry
        assert "physics" not in entry
        return

    system = spec.build()
    derivation = entry["derivation"]

    assert derivation["lagrangian"]["expression_latex"] == entry["physics"]["lagrangian"]
    assert len(derivation["generalized_momenta"]) == len(system.q)
    assert len(derivation["euler_lagrange"]) == len(system.q)

    for momentum in derivation["generalized_momenta"]:
        assert momentum["coordinate"]
        assert momentum["velocity"]
        assert momentum["momentum"]
        assert momentum["momentum_latex"]
        assert momentum["expression_latex"]
        assert momentum["equation_latex"]

    for equation in derivation["euler_lagrange"]:
        assert equation["coordinate"]
        assert equation["equation_latex"]

    legendre = derivation["legendre_transform"]
    assert legendre["regular"] is True
    assert len(legendre["velocity_solutions"]) == len(system.qdot)
    assert derivation["hamiltonian"]["expression_latex"] == entry["physics"]["hamiltonian"]
    assert len(derivation["hamiltonian"]["equations"]) == 2 * len(system.q)

    conserved = derivation["conserved_quantities"]
    assert [quantity["name"] for quantity in conserved] == [
        quantity.name for quantity in spec.conserved
    ]
    for quantity in conserved:
        assert quantity["symbol_latex"]
        assert quantity["symmetry"]
        assert quantity["charge_latex"]
        assert "generator_latex" in quantity

    assert derivation["effective_potentials"] == entry["effectivePotentials"]


@pytest.mark.parametrize("spec", SPECS, ids=[spec.id for spec in SPECS])
def test_conserved_quantities_render(spec) -> None:
    entry = system_entry(spec)
    if entry.get("dynamics"):
        assert entry["conserved"] == []
        return

    assert entry["conserved"], "each system should declare at least one invariant"
    for quantity in entry["conserved"]:
        assert quantity["latex"]
        assert quantity["symmetry"]
        if "expression_latex" in quantity:
            assert quantity["expression_latex"]


@pytest.mark.parametrize("spec", SPECS, ids=[spec.id for spec in SPECS])
def test_conserved_quantities_use_noether_generators(spec) -> None:
    system = spec.build()
    entry = system_entry(spec)
    if not isinstance(system, LagrangianSystem):
        assert entry["conserved"] == []
        return

    for declared, rendered in zip(spec.conserved, entry["conserved"], strict=True):
        assert declared.generator is not None
        assert declared.expression_for(system) is not None
        assert rendered["expression_latex"]
        assert "generator_latex" in rendered


def test_manifest_lists_every_spec(manifest) -> None:
    assert manifest["version"] == 1
    assert [entry["id"] for entry in manifest["lenses"]] == [lens.id for lens in LENSES]
    assert [entry["id"] for entry in manifest["systems"]] == [spec.id for spec in SPECS]
