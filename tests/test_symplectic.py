import sympy as sp

from engine.mechanics import CoordinateChart, HamiltonianSystem, legendre_transform
from engine.mechanics.poisson import (
    is_conserved,
    poisson_bracket,
    poisson_bracket_matrix,
    time_evolution,
)
from engine.mechanics.symplectic import (
    canonical_symplectic_form_matrix,
    canonical_symplectic_matrix,
    hamiltonian_vector_field,
    is_canonical_transformation,
    liouville_divergence,
    phase_space_divergence,
    satisfies_liouville_theorem,
)
from systems.pendulum import build_system as pendulum


def test_poisson_bracket_canonical_relations():
    chart = CoordinateChart.from_names("q1 q2")
    q1, q2 = chart.coordinates
    p1, p2 = chart.cotangent_bundle().momenta

    assert poisson_bracket(q1, p1, chart.coordinates, (p1, p2)) == 1
    assert poisson_bracket(q1, p2, chart.coordinates, (p1, p2)) == 0
    assert poisson_bracket(q1, q2, chart.coordinates, (p1, p2)) == 0
    assert poisson_bracket(p1, p2, chart.coordinates, (p1, p2)) == 0


def test_poisson_bracket_matrix_for_phase_space_coordinates():
    chart = CoordinateChart.from_names("q")
    (q,) = chart.coordinates
    (p,) = chart.cotangent_bundle().momenta

    bracket_matrix = poisson_bracket_matrix((q, p), chart.coordinates, (p,))

    assert bracket_matrix == canonical_symplectic_matrix(1)


def test_hamiltonian_flow_is_poisson_evolution():
    chart = CoordinateChart.from_names("q")
    (q,) = chart.coordinates
    (p,) = chart.cotangent_bundle().momenta
    hamiltonian = p**2 / 2 + q**2 / 2

    assert time_evolution(q, hamiltonian, chart.coordinates, (p,), time=chart.time) == p
    assert time_evolution(p, hamiltonian, chart.coordinates, (p,), time=chart.time) == -q
    assert is_conserved(hamiltonian, hamiltonian, chart.coordinates, (p,), time=chart.time)


def test_symplectic_matrix_and_hamiltonian_vector_field():
    chart = CoordinateChart.from_names("q1 q2")
    q1, q2 = chart.coordinates
    p1, p2 = chart.cotangent_bundle().momenta
    hamiltonian = (p1**2 + p2**2) / 2 + (q1**2 + q2**2) / 2

    assert canonical_symplectic_matrix(2) == sp.Matrix(
        [
            [0, 0, 1, 0],
            [0, 0, 0, 1],
            [-1, 0, 0, 0],
            [0, -1, 0, 0],
        ]
    )
    assert canonical_symplectic_form_matrix(2) == -canonical_symplectic_matrix(2)
    assert hamiltonian_vector_field(hamiltonian, chart.coordinates, (p1, p2)) == sp.Matrix(
        [p1, p2, -q1, -q2]
    )


def test_liouville_theorem_for_general_symbolic_hamiltonian():
    chart = CoordinateChart.from_names("q1 q2")
    q1, q2 = chart.coordinates
    p1, p2 = chart.cotangent_bundle().momenta
    hamiltonian = sp.Function("H")(q1, q2, p1, p2)
    vector_field = hamiltonian_vector_field(hamiltonian, chart.coordinates, (p1, p2))

    assert phase_space_divergence(vector_field, chart.coordinates, (p1, p2)) == 0
    assert liouville_divergence(hamiltonian, chart.coordinates, (p1, p2)) == 0
    assert satisfies_liouville_theorem(hamiltonian, chart.coordinates, (p1, p2))


def test_hamiltonian_system_exposes_geometry_helpers():
    lagrangian_system = pendulum(mass=1.0, length=1.0, gravity=9.81)
    hamiltonian_system = legendre_transform(lagrangian_system).hamiltonian_system
    (theta,) = hamiltonian_system.q
    (p_theta,) = hamiltonian_system.p

    assert hamiltonian_system.poisson_bracket(theta, p_theta) == 1
    assert sp.simplify(hamiltonian_system.time_evolution(theta) - p_theta) == 0
    assert hamiltonian_system.liouville_divergence() == 0


def test_canonical_transformation_checks():
    chart = CoordinateChart.from_names("q")
    (q,) = chart.coordinates
    (p,) = chart.cotangent_bundle().momenta

    assert is_canonical_transformation((p, -q), chart.coordinates, (p,))
    assert not is_canonical_transformation((2 * q, p), chart.coordinates, (p,))


def test_hamiltonian_system_equations_match_vector_field():
    chart = CoordinateChart.from_names("q")
    (q,) = chart.coordinates
    (p,) = chart.cotangent_bundle().momenta
    system = HamiltonianSystem(chart.coordinates, (p,), p**2 / 2 + q**2 / 2, chart.time)

    assert system.hamilton_equations() == (p, -q)

