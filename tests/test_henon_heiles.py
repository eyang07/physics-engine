from __future__ import annotations

import numpy as np
import sympy as sp

from scripts.generate_henon_heiles import generate_henon_heiles_trajectory
from systems.henon_heiles import build_system


def test_henon_heiles_equations_and_energy() -> None:
    m, k, lam = sp.symbols("m k lambda")
    system = build_system(mass=m, stiffness=k, coupling=lam)
    x, y = system.q
    x_dot, y_dot = system.qdot
    x_ddot, y_ddot = system.qddot

    x_equation, y_equation = system.euler_lagrange_expressions()

    assert sp.simplify(x_equation - (m * x_ddot + k * x + 2 * lam * x * y)) == 0
    assert sp.simplify(y_equation - (m * y_ddot + k * y + lam * (x**2 - y**2))) == 0
    expected_energy = (
        m * (x_dot**2 + y_dot**2) / 2
        + k * (x**2 + y**2) / 2
        + lam * (x**2 * y - y**3 / 3)
    )
    assert sp.simplify(system.energy() - expected_energy) == 0


def test_henon_heiles_generated_energy_and_potential_surface() -> None:
    trajectory = generate_henon_heiles_trajectory(t_span=(0.0, 12.0), dt=0.01)

    assert trajectory.state_names == ("x", "y", "x_dot", "y_dot")
    assert trajectory.series is not None
    energy = np.asarray(trajectory.series["H"], dtype=float)
    assert np.max(np.abs(energy - energy[0])) < 1e-8

    surface = trajectory.metadata["potentialSurface"]
    assert len(surface["xValues"]) == 120
    assert len(surface["yValues"]) == 120
    assert np.asarray(surface["values"], dtype=float).shape == (120, 120)
    assert abs(surface["energy"] - float(energy.mean())) < 1e-12
    hints = trajectory.metadata["rendererHints"]
    assert hints["referenceGeometry"][0]["kind"] == "potentialSurface"
    assert hints["flow"]["kind"] == "potentialGradient"
    assert set(hints["bounds"]) == {"x", "y", "z"}
