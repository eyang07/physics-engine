import numpy as np
import sympy as sp

from metadata_assertions import assert_metadata_keys
from engine.export.manifest import system_entry
from scripts.example_specs import IDEAL_SPRING, KEPLER
from scripts.generate_ideal_spring import (
    generate_ideal_spring_trajectory,
    write_ideal_spring_variant_trajectories,
)
from scripts.generate_kepler_problem import generate_kepler_trajectory
from scripts.generate_uniform_gravity import generate_uniform_gravity_trajectory
from systems.ideal_spring import build_system as ideal_spring
from systems.kepler_problem import build_system as kepler_problem
from systems.uniform_gravity import build_system as uniform_gravity


def test_uniform_gravity_equations():
    m, g = sp.symbols("m g")
    system = uniform_gravity(mass=m, gravity=g)
    x_ddot, z_ddot = system.qddot
    x_equation, z_equation = system.euler_lagrange_expressions()

    assert sp.simplify(x_equation - m * x_ddot) == 0
    assert sp.simplify(z_equation - (g * m + m * z_ddot)) == 0


def test_uniform_gravity_generated_motion_is_parabolic():
    trajectory = generate_uniform_gravity_trajectory(t_span=(0.0, 0.5), dt=0.005)
    time = trajectory.time
    x, z, x_dot, z_dot = trajectory.states.T

    assert np.max(np.abs(x - x_dot[0] * time)) < 1e-12
    assert np.max(np.abs(z - (z_dot[0] * time - 0.5 * 9.81 * time**2))) < 1e-10
    assert np.max(np.abs(x_dot - x_dot[0])) < 1e-12
    assert np.max(np.abs(z_dot - (z_dot[0] - 9.81 * time))) < 1e-10
    assert trajectory.metadata is not None
    hints = trajectory.metadata["rendererHints"]
    assert hints["referenceGeometry"][0]["kind"] == "groundPlane"
    assert hints["flow"]["kind"] == "uniformGravity"


def test_ideal_spring_equation_and_energy():
    m, k = sp.symbols("m k")
    system = ideal_spring(mass=m, spring_constant=k)
    (x,) = system.q
    (x_dot,) = system.qdot
    (x_ddot,) = system.qddot

    assert system.euler_lagrange_expressions() == (k * x + m * x_ddot,)
    assert sp.simplify(system.energy() - (m * x_dot**2 / 2 + k * x**2 / 2)) == 0


def test_ideal_spring_generated_motion_conserves_energy():
    trajectory = generate_ideal_spring_trajectory(t_span=(0.0, 8.0), dt=0.01)
    x, x_dot = trajectory.states.T
    energy = 0.5 * x_dot**2 + 0.5 * x**2

    assert np.max(np.abs(energy - energy[0])) < 1e-8


def test_ideal_spring_manifest_and_variant_generation(tmp_path):
    entry = system_entry(IDEAL_SPRING)
    assert [variant["id"] for variant in entry["variants"]] == ["k-0-5", "k-1", "k-2"]
    assert entry["variants"][1]["dataPath"] == "/data/ideal_spring.json"

    output_dir = tmp_path / "data"
    viewer_output_dir = tmp_path / "viewer-data"
    trajectories = write_ideal_spring_variant_trajectories(
        output_dir,
        viewer_output_dir=viewer_output_dir,
    )
    written_variants = [
        variant
        for variant in IDEAL_SPRING.variants
        if variant.data_path != IDEAL_SPRING.data_path
    ]

    assert len(trajectories) == len(written_variants)
    for variant, trajectory in zip(written_variants, trajectories, strict=True):
        filename = variant.data_path.removeprefix("/data/")
        assert (output_dir / filename).exists()
        assert (viewer_output_dir / filename).exists()
        metadata = assert_metadata_keys(
            trajectory,
            {
                "invariantResiduals",
                "system",
                "mass",
                "spring_constant",
                "potentialPlots",
            },
        )
        assert metadata["system"] == "ideal_spring"
        assert metadata["mass"] == variant.parameters["m"]
        assert metadata["spring_constant"] == variant.parameters["k"]
        potential_plot = metadata["potentialPlots"][0]
        assert potential_plot["name"] == "spring_potential"
        assert potential_plot["coordinate"] == "x"
        assert potential_plot["coordinateLatex"] == "x"
        assert potential_plot["potentialLatex"] == "V"
        assert len(potential_plot["coordinateValues"]) == 260
        assert len(potential_plot["potentialValues"]) == 260
        assert trajectory.state_names == ("x", "x_dot")
        assert trajectory.series is not None
        x, x_dot = trajectory.states.T
        energy = (
            0.5 * variant.parameters["m"] * x_dot**2
            + 0.5 * variant.parameters["k"] * x**2
        )
        assert np.max(np.abs(energy - energy[0])) < 1e-8


def test_kepler_equations():
    m, mu = sp.symbols("m mu")
    system = kepler_problem(mass=m, gravitational_parameter=mu)
    r, _phi = system.q
    r_dot, phi_dot = system.qdot
    r_ddot, phi_ddot = system.qddot

    radial, angular = system.euler_lagrange_expressions()

    assert sp.simplify(radial - (m * r_ddot - m * r * phi_dot**2 + m * mu / r**2)) == 0
    assert sp.simplify(angular - (m * r**2 * phi_ddot + 2 * m * r * r_dot * phi_dot)) == 0


def test_kepler_generated_motion_conserves_energy_and_angular_momentum():
    trajectory = generate_kepler_trajectory(t_span=(0.0, 8.0), dt=0.01)
    r, _phi, r_dot, phi_dot, _x, _y = trajectory.states.T
    angular_momentum = r**2 * phi_dot
    energy = 0.5 * (r_dot**2 + r**2 * phi_dot**2) - 1.0 / r

    assert np.max(np.abs(angular_momentum - angular_momentum[0])) < 1e-8
    assert np.max(np.abs(energy - energy[0])) < 1e-8
    assert trajectory.metadata is not None
    hints = trajectory.metadata["rendererHints"]
    assert hints["camera"]["position"][1] > 0
    assert hints["referenceGeometry"][0]["kind"] == "centralBody"
    assert hints["flow"]["kind"] == "centralAttraction"
    classification = trajectory.metadata["orbitClassification"]
    assert classification["classification"] == "bound"
    plot = trajectory.metadata["potentialPlots"][0]
    assert plot["name"] == "kepler_radial"
    assert plot["rendererHint"] == "effective-potential"
    assert plot["classification"] == "bound"
    turning_points = np.asarray(plot["turningPoints"], dtype=float)
    assert turning_points.shape == (2,)
    potential_at_roots = turning_points ** -2 * 0.5 * plot["angularMomentum"] ** 2 - (
        1.0 / turning_points
    )
    assert np.allclose(potential_at_roots, plot["energy"])


def test_kepler_effective_potential_matches_radial_energy_reduction():
    system = KEPLER.build()
    r, _phi = system.q
    r_dot, phi_dot = system.qdot
    m = next(symbol for symbol in system.lagrangian.free_symbols if symbol.name == "m")
    mu = next(symbol for symbol in system.lagrangian.free_symbols if symbol.name == "mu")
    ell = sp.Symbol("ell")
    (effective_potential,) = KEPLER.effective_potentials

    expected = ell**2 / (2 * m * r**2) - mu * m / r
    assert sp.simplify(effective_potential.expression_for(system) - expected) == 0
    assert effective_potential.turning_points_source is not None
    assert effective_potential.classification_source == "trajectory.metadata.orbitClassification"

    radial_energy = sp.simplify(system.energy().subs({phi_dot: ell / (m * r**2)}))
    radial_kinetic = m * r_dot**2 / 2
    assert sp.simplify(radial_energy - (radial_kinetic + expected)) == 0
