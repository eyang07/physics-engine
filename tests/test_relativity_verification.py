from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest
import sympy as sp

from engine.numerics import integrate_fixed_step
from engine.verification import (
    ObligationSpec,
    VerificationProblem,
    four_momentum_conservation_obligations,
    mass_shell_conservation_obligation,
    worldline_conservation_verification_problem,
)
from scripts.generate_relativistic_free_particle import (
    generate_relativistic_free_particle_verification,
    write_relativistic_free_particle_verification,
)
from systems.relativistic_free_particle import (
    build_system,
    initial_state_from_velocity,
    interval_rate_expression,
)


def test_mass_shell_conservation_obligation_bounds_the_absolute_residual() -> None:
    x = sp.Symbol("x", real=True)
    obligation = mass_shell_conservation_obligation(x - 1, tolerance=1e-6)

    assert isinstance(obligation, ObligationSpec)
    assert obligation.rigor == "external-required"
    assert obligation.comparison == "<="
    assert obligation.rhs == 1e-6
    assert sp.sympify(obligation.expression.source) == sp.Abs(x - 1)


def test_mass_shell_conservation_obligation_rejects_nonpositive_tolerance() -> None:
    x = sp.Symbol("x", real=True)
    with pytest.raises(ValueError):
        mass_shell_conservation_obligation(x, tolerance=0.0)


def test_four_momentum_conservation_obligations_bound_each_component() -> None:
    p0, p1 = sp.symbols("p0 p1", real=True)
    obligations = four_momentum_conservation_obligations(
        (p0, p1), (2.0, -3.0), tolerance=1e-4
    )

    assert [obligation.id for obligation in obligations] == [
        "four-momentum-p0-conservation",
        "four-momentum-p1-conservation",
    ]
    assert sp.sympify(obligations[0].expression.source) == sp.Abs(p0 - 2.0)
    assert sp.sympify(obligations[1].expression.source) == sp.Abs(p1 + 3.0)
    for obligation in obligations:
        assert obligation.rigor == "external-required"
        assert obligation.comparison == "<="
        assert obligation.rhs == 1e-4


def test_four_momentum_conservation_obligations_rejects_mismatched_lengths() -> None:
    p0 = sp.Symbol("p0", real=True)
    with pytest.raises(ValueError):
        four_momentum_conservation_obligations((p0,), (1.0, 2.0), tolerance=1e-4)


def test_free_particle_conservation_problem_measures_holds_along_the_rollout() -> None:
    problem = generate_relativistic_free_particle_verification()

    assert isinstance(problem, VerificationProblem)
    assert problem.system == "relativistic_free_particle"
    assert len(problem.obligations) == 4
    assert {obligation.rigor for obligation in problem.obligations} == {"external-required"}
    assert len(problem.proof_statuses) == len(problem.obligations)

    for status in problem.proof_statuses:
        assert status.status == "measured-holds"
        assert status.rigor == "measured"
        assert status.external_status == "external-required"
        assert status.sample_count > 0


def test_free_particle_conservation_problem_flags_a_violation_below_tolerance() -> None:
    system = build_system()
    mass_shell_expression = interval_rate_expression(system) + 1
    momentum_symbols = system.state[len(system.state) // 2 :]

    time, states = integrate_fixed_step(
        system.numerical_rhs(),
        initial_state_from_velocity(),
        (0.0, 6.0),
        0.02,
    )
    tampered = np.asarray(states, dtype=float).copy()
    tampered[-1, 3] += 10.0  # perturb the last sample's u^0 far outside tolerance

    problem = worldline_conservation_verification_problem(
        id="tampered-free-particle",
        name="tampered free particle",
        system_id="relativistic_free_particle",
        system=system,
        mass_shell_expression=mass_shell_expression,
        momentum_symbols=momentum_symbols,
        time=time,
        states=tampered,
        tolerance=1e-6,
    )

    momentum_status = next(
        status
        for status in problem.proof_statuses
        if status.obligation_id == "four-momentum-x0_dot-conservation"
    )
    assert momentum_status.status == "measured-violated"
    assert momentum_status.worst_margin is not None and momentum_status.worst_margin < 0


def test_free_particle_conservation_problem_round_trips_through_json(tmp_path: Path) -> None:
    output = tmp_path / "relativistic_free_particle_verification.json"
    viewer_output = tmp_path / "viewer" / "relativistic_free_particle_verification.json"

    problem = write_relativistic_free_particle_verification(output, viewer_output=viewer_output)

    for path in (output, viewer_output):
        payload = json.loads(path.read_text(encoding="utf-8"))
        assert VerificationProblem.from_dict(payload) == problem
        assert all(
            obligation["rigor"] == "external-required" for obligation in payload["obligations"]
        )
        assert all(
            status["status"] in ("measured-holds", "measured-violated")
            for status in payload["proofStatuses"]
        )
