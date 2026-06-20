"""The manifest is a contract; these tests guard it against drift.

The most valuable check is structural: a spec's declared state schema and
projections must agree with the system the engine actually builds, so adding or
editing a system can't silently desync the viewer.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from pathlib import Path

import pytest

from engine.export import Trajectory, validate_viewer_verification_problems
from engine.export.manifest import SystemSpec, build_manifest, system_entry
from engine.dynamics import CotangentHamiltonianSystem
from engine.mechanics.lagrangian import LagrangianSystem
from scripts.example_specs import (
    DOUBLE_PENDULUM,
    IDEAL_SPRING,
    LENSES,
    LORENZ,
    N_BODY_GRAVITY,
    SPECS,
)
from scripts.export_verification_problems import upright_pendulum_problem
from scripts.generate_double_pendulum import write_double_pendulum_variant_trajectories
from scripts.generate_ideal_spring import write_ideal_spring_variant_trajectories
from scripts.generate_lorenz_attractor import write_lorenz_variant_trajectories
from scripts.generate_n_body_gravity import write_n_body_variant_trajectories


def _write_ideal_spring_variants(
    output_dir: Path,
    viewer_output_dir: Path,
) -> list[Trajectory]:
    return write_ideal_spring_variant_trajectories(
        output_dir,
        viewer_output_dir=viewer_output_dir,
    )


def _write_lorenz_variants(
    output_dir: Path,
    viewer_output_dir: Path,
) -> list[Trajectory]:
    return write_lorenz_variant_trajectories(
        output_dir,
        viewer_output_dir=viewer_output_dir,
    )


def _write_double_pendulum_variants(
    output_dir: Path,
    viewer_output_dir: Path,
) -> list[Trajectory]:
    return write_double_pendulum_variant_trajectories(
        output_dir,
        viewer_output_dir=viewer_output_dir,
    )


def _write_n_body_variants(
    output_dir: Path,
    viewer_output_dir: Path,
) -> list[Trajectory]:
    return write_n_body_variant_trajectories(
        output_dir,
        viewer_output_dir=viewer_output_dir,
    )


VARIANT_TRAJECTORY_WRITERS: dict[str, Callable[[Path, Path], list[Trajectory]]] = {
    DOUBLE_PENDULUM.id: _write_double_pendulum_variants,
    IDEAL_SPRING.id: _write_ideal_spring_variants,
    LORENZ.id: _write_lorenz_variants,
    N_BODY_GRAVITY.id: _write_n_body_variants,
}


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
    if spec.system_kind == "static-field":
        assert spec.state == ()
        assert hasattr(system, "electric_field")
        assert hasattr(system, "magnetic_field")
        return

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
        dynamic_state = [
            variable.name
            for variable in spec.state
            if variable.kind in {"coordinate", "velocity", "momentum"}
        ]
        assert dynamic_state == [symbol.name for symbol in system.state_symbols]


@pytest.mark.parametrize("spec", SPECS, ids=[spec.id for spec in SPECS])
def test_projections_reference_known_state(spec) -> None:
    known = {variable.name for variable in spec.state}
    for group in spec.projections.values():
        assert set(group) <= known


@pytest.mark.parametrize("spec", SPECS, ids=[spec.id for spec in SPECS])
def test_physical_parameters_appear_in_lagrangian(spec) -> None:
    system = spec.build()
    if spec.system_kind == "static-field":
        field_parameters = {
            symbol.name
            for field in (
                system.electric_potential,
                system.electric_field,
                system.magnetic_field,
            )
            for symbol in field.parameters
        }
        field_parameters.update(symbol.name for symbol in system.current_loop_axis_b.free_symbols)
        for parameter in spec.parameters:
            if parameter.role == "physical":
                assert parameter.name in field_parameters
        return

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


def test_variant_specs_have_one_default_variant_and_python_writer() -> None:
    variant_specs = [spec for spec in SPECS if spec.variants]

    assert set(VARIANT_TRAJECTORY_WRITERS) == {spec.id for spec in variant_specs}
    for spec in variant_specs:
        default_variants = [
            variant for variant in spec.variants if variant.data_path == spec.data_path
        ]
        assert len(default_variants) == 1, spec.id
        assert default_variants[0].parameters == {
            parameter.name: parameter.default for parameter in spec.parameters
        }


@pytest.mark.parametrize(
    "spec",
    [spec for spec in SPECS if spec.variants],
    ids=[spec.id for spec in SPECS if spec.variants],
)
def test_variant_python_writers_generate_non_default_manifest_paths(
    spec: SystemSpec,
    tmp_path: Path,
) -> None:
    writer = VARIANT_TRAJECTORY_WRITERS[spec.id]
    output_dir = tmp_path / "data"
    viewer_output_dir = tmp_path / "viewer-data"

    trajectories = writer(output_dir, viewer_output_dir)

    written_variants = [
        variant for variant in spec.variants if variant.data_path != spec.data_path
    ]
    expected_filenames = [
        variant.data_path.removeprefix("/data/") for variant in written_variants
    ]
    assert len(trajectories) == len(written_variants)
    assert sorted(path.relative_to(output_dir).as_posix() for path in output_dir.rglob("*.json")) == (
        sorted(expected_filenames)
    )
    assert sorted(
        path.relative_to(viewer_output_dir).as_posix()
        for path in viewer_output_dir.rglob("*.json")
    ) == sorted(expected_filenames)

    for variant, trajectory in zip(written_variants, trajectories, strict=True):
        filename = variant.data_path.removeprefix("/data/")
        assert trajectory.metadata is not None
        assert (output_dir / filename).exists()
        assert (viewer_output_dir / filename).exists()


def test_known_parameter_variant_manifest_metadata_is_stable() -> None:
    entries = {entry["id"]: entry for entry in build_manifest(SPECS, LENSES)["systems"]}

    assert entries[IDEAL_SPRING.id]["variants"] == [
        {
            "id": "k-0-5",
            "label": "k = 0.5",
            "parameters": {"m": 1.0, "k": 0.5, "x0": 1.0, "x_dot0": 0.0},
            "dataPath": "/data/ideal_spring_k_0_5.json",
        },
        {
            "id": "k-1",
            "label": "k = 1",
            "parameters": {"m": 1.0, "k": 1.0, "x0": 1.0, "x_dot0": 0.0},
            "dataPath": "/data/ideal_spring.json",
        },
        {
            "id": "k-2",
            "label": "k = 2",
            "parameters": {"m": 1.0, "k": 2.0, "x0": 1.0, "x_dot0": 0.0},
            "dataPath": "/data/ideal_spring_k_2.json",
        },
    ]
    assert entries[LORENZ.id]["variants"] == [
        {
            "id": "rho-20",
            "label": "rho = 20",
            "parameters": {
                "sigma": 10.0,
                "rho": 20.0,
                "beta": 8.0 / 3.0,
                "x0": 0.0,
                "y0": 1.0,
                "z0": 1.05,
            },
            "dataPath": "/data/lorenz_attractor_rho_20.json",
        },
        {
            "id": "rho-28",
            "label": "rho = 28",
            "parameters": {
                "sigma": 10.0,
                "rho": 28.0,
                "beta": 8.0 / 3.0,
                "x0": 0.0,
                "y0": 1.0,
                "z0": 1.05,
            },
            "dataPath": "/data/lorenz_attractor.json",
        },
        {
            "id": "rho-35",
            "label": "rho = 35",
            "parameters": {
                "sigma": 10.0,
                "rho": 35.0,
                "beta": 8.0 / 3.0,
                "x0": 0.0,
                "y0": 1.0,
                "z0": 1.05,
            },
            "dataPath": "/data/lorenz_attractor_rho_35.json",
        },
    ]


@pytest.mark.parametrize("spec", SPECS, ids=[spec.id for spec in SPECS])
def test_entry_carries_symbolic_physics(spec) -> None:
    entry = system_entry(spec)
    if entry.get("systemKind") == "static-field":
        assert "physics" not in entry
        assert "dynamics" not in entry
        assert entry["fields"] and all(channel["source"] for channel in entry["fields"])
        assert entry["fieldModel"]["kind"] == "electromagnetic-static"
        assert entry["lenses"], "every system needs at least one visualization lens"
        assert entry["dataPath"].startswith("/data/")
        return

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
    if entry.get("systemKind") == "static-field":
        assert "derivation" not in entry
        assert "physics" not in entry
        assert "dynamics" not in entry
        return

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

    if not spec.conserved:
        assert entry["conserved"] == []
        return
    assert entry["conserved"], "systems with invariants should declare them"
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
        assert [quantity["name"] for quantity in entry["conserved"]] == [
            quantity.name for quantity in spec.conserved
        ]
        for declared, rendered in zip(spec.conserved, entry["conserved"], strict=True):
            assert declared.expression is not None
            assert declared.generator is None
            assert rendered["expression_latex"]
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
