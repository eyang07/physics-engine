from __future__ import annotations

import numpy as np
import sympy as sp

from engine.export.manifest import system_entry
from scripts.example_specs import SYMMETRIC_TOP
from scripts.generate_symmetric_top import generate_symmetric_top_trajectory
from systems.symmetric_top import build_system, effective_potential


def test_phi_and_psi_are_cyclic_so_their_momenta_conserve() -> None:
    system = build_system()
    theta, phi, psi = system.q

    # phi and psi do not appear in the Lagrangian; theta does.
    assert phi not in system.lagrangian.free_symbols
    assert psi not in system.lagrangian.free_symbols
    assert theta in system.lagrangian.free_symbols

    # The Noether charges declared in the spec are exactly the conjugate momenta.
    momenta = dict(zip((q.name for q in system.q), system.generalized_momenta()))
    by_name = {c.name: c for c in SYMMETRIC_TOP.conserved}
    assert sp.simplify(by_name["p_phi"].expression_for(system) - momenta["phi"]) == 0
    assert sp.simplify(by_name["p_psi"].expression_for(system) - momenta["psi"]) == 0


def test_effective_potential_matches_reduced_energy_balance() -> None:
    system = build_system()
    theta = next(q for q in system.q if q.name == "theta")
    p_phi, p_psi = sp.symbols("p_phi p_psi")
    i1, m, g, ell = sp.symbols("I1 M g ell", positive=True)
    expected = (
        (p_phi - p_psi * sp.cos(theta)) ** 2 / (2 * i1 * sp.sin(theta) ** 2)
        + m * g * ell * sp.cos(theta)
    )
    assert sp.simplify(effective_potential(system) - expected) == 0


def test_generated_top_precesses_and_nutates_with_measured_invariants() -> None:
    trajectory = generate_symmetric_top_trajectory(t_span=(0.0, 8.0))

    assert trajectory.series is not None
    assert set(trajectory.series) == {"H", "p_phi", "p_psi"}

    assert trajectory.metadata is not None
    residuals = trajectory.metadata["invariantResiduals"]
    assert {record["rigor"] for record in residuals} == {"measured"}
    assert {record["name"] for record in residuals} == {"H", "p_phi", "p_psi"}
    assert max(record["maxRelative"] for record in residuals) < 1e-8

    theta = trajectory.states[:, 0]
    phi = trajectory.states[:, 1]
    # Nutation: the tilt angle visibly oscillates rather than staying fixed.
    assert (theta.max() - theta.min()) > 0.1
    # Precession: the azimuth advances steadily and monotonically.
    assert phi[-1] - phi[0] > 1.0
    assert np.all(np.diff(phi) >= -1e-9)


def test_generated_top_exports_effective_potential_plot() -> None:
    trajectory = generate_symmetric_top_trajectory(t_span=(0.0, 4.0))
    assert trajectory.metadata is not None
    plots = trajectory.metadata["potentialPlots"]
    assert len(plots) == 1
    plot = plots[0]
    assert plot["coordinate"] == "theta"
    coordinate = np.asarray(plot["coordinateValues"], dtype=float)
    potential = np.asarray(plot["potentialValues"], dtype=float)
    assert coordinate.shape == potential.shape
    # The centrifugal barrier diverges as theta approaches the poles.
    assert potential[0] > potential[len(potential) // 2]


def test_generated_top_exports_orientation_matching_its_axis_embedding() -> None:
    trajectory = generate_symmetric_top_trajectory(t_span=(0.0, 4.0))
    orientation = trajectory.orientation
    assert orientation is not None
    assert orientation["convention"] == "quaternion-wxyz"
    quaternions = np.asarray(orientation["quaternion"], dtype=float)
    assert quaternions.shape == (trajectory.states.shape[0], 4)
    assert np.allclose(np.linalg.norm(quaternions, axis=1), 1.0)

    # The exported body 3-axis matches the symmetry-axis embedding (radius ell).
    e3 = np.asarray(orientation["bodyAxes"]["e3"], dtype=float)
    embedding = trajectory.states[:, 6:9] / 0.5
    assert np.allclose(e3, embedding, atol=1e-9)
    assert "orientation" in trajectory.to_dict()


def test_symmetric_top_manifest_declares_orientation_channel() -> None:
    entry = system_entry(SYMMETRIC_TOP)
    assert entry["orientation"]["rendererHint"] == "rigid-body"
    assert entry["orientation"]["convention"] == "quaternion-wxyz"
    assert entry["orientation"]["source"] == "trajectory.orientation"


def test_manifest_entry_exposes_conserved_momenta_and_effective_potential() -> None:
    entry = system_entry(SYMMETRIC_TOP)
    conserved_names = {item["name"] for item in entry["conserved"]}
    assert {"H", "p_phi", "p_psi"} <= conserved_names

    potentials = entry["effectivePotentials"]
    assert [potential["coordinate"] for potential in potentials] == ["theta"]
    assert r"p_{\psi}" in potentials[0]["expression_latex"]
