from __future__ import annotations

import json

import pytest
import sympy as sp

from engine.dynamics import (
    BarrierCandidate,
    FirstOrderSystem,
    LyapunovCandidate,
    ProofObligation,
    SafetySpecification,
    SublevelSet,
)
from engine.verification import (
    SCHEMA_VERSION,
    verification_problem_from_barrier,
    verification_problem_from_lyapunov,
    verification_problem_from_obligations,
)
from systems.controlled_pendulum import build_system


def _damped_oscillator() -> tuple[FirstOrderSystem, sp.Symbol, sp.Symbol, sp.Symbol, sp.Symbol]:
    x, v = sp.symbols("x v", real=True)
    k, c = sp.symbols("k c", positive=True)
    system = FirstOrderSystem(state=(x, v), rhs=(v, -k * x - c * v), parameters=(k, c))
    return system, x, v, k, c


def _pendulum_closed_loop():
    pendulum = build_system(mass=1.0, length=1.0, gravity=9.81, damping=0.1)
    theta, omega = pendulum.state
    (u,) = pendulum.controls
    closed = pendulum.closed_loop({u: -20 * (theta - sp.pi) - 5 * omega})
    return closed, theta, omega


def test_lyapunov_candidate_exports_verification_problem() -> None:
    system, x, v, k, c = _damped_oscillator()
    candidate = LyapunovCandidate(
        state=(x, v),
        function=(k * x**2 + v**2) / 2,
        equilibrium=(0.0, 0.0),
        domain=SublevelSet(state=(x, v), expression=x**2 + v**2, level=4.0, name="ball"),
    )

    problem = verification_problem_from_lyapunov(
        "damped oscillator lyapunov",
        system,
        candidate,
        substitutions={k: 4.0, c: 0.5},
        metadata={"system": "damped-oscillator"},
    )
    payload = problem.to_dict()

    assert payload["schemaVersion"] == SCHEMA_VERSION
    assert payload["id"] == "damped-oscillator-lyapunov"
    assert [variable["name"] for variable in payload["variables"]] == ["x", "v"]
    assert [parameter["name"] for parameter in payload["parameters"]] == ["c", "k"]
    assert payload["parameters"][0]["value"] == 0.5
    assert payload["parameters"][1]["value"] == 4.0
    assert payload["metadata"]["status"] == "candidate"
    assert "external sound discharge" in payload["metadata"]["note"]

    assert len(payload["regions"]) == 1
    assert payload["regions"][0]["id"] == "domain-ball"
    assert payload["regions"][0]["kind"] == "sublevel"
    assert payload["regions"][0]["convention"] == "expression <= level"

    obligations = payload["obligations"]
    assert [obligation["id"] for obligation in obligations] == [
        "lyapunov-candidate-equilibrium-value",
        "lyapunov-candidate-positivity",
        "lyapunov-candidate-decrease",
    ]
    assert obligations[1]["regionId"] == "domain-ball"
    assert obligations[1]["excludedPoints"] == [[0.0, 0.0]]
    assert {obligation["rigor"] for obligation in obligations} == {"external-required"}
    assert obligations[2]["expression"]["format"] == "sympy-srepr"

    encoded = json.dumps(payload)
    assert "certified" not in encoded


def test_barrier_candidate_exports_specification_regions() -> None:
    closed, theta, omega = _pendulum_closed_loop()
    d = theta - sp.pi
    lyapunov = omega**2 / 2 + 10 * d**2 + sp.Rational(981, 100) * (sp.cos(d) - 1)
    specification = SafetySpecification(
        state=(theta, omega),
        safe_set=SublevelSet(state=(theta, omega), expression=d**2, level=0.25, name="corridor"),
        unsafe_sets=(
            SublevelSet(state=(theta, omega), expression=theta, level=0.2, name="near-bottom"),
        ),
        initial_set=SublevelSet(
            state=(theta, omega), expression=d**2 + omega**2, level=0.09, name="start-ball"
        ),
    )
    barrier = BarrierCandidate(
        state=(theta, omega),
        function=lyapunov - sp.Rational(12, 10),
        name="energy-barrier",
    )

    problem = verification_problem_from_barrier(
        "upright pendulum safety",
        closed,
        barrier,
        specification=specification,
    )
    payload = problem.to_dict()

    assert [region["role"] for region in payload["regions"]] == [
        "safe",
        "initial",
        "unsafe",
        "domain",
    ]
    assert [region["id"] for region in payload["regions"]] == [
        "safe-corridor",
        "initial-start-ball",
        "unsafe-near-bottom",
        "domain-energy-barrier-region",
    ]
    assert [obligation["name"] for obligation in payload["obligations"]] == [
        "energy-barrier:non-increase",
        "energy-barrier:initial-containment",
        "energy-barrier:excludes:near-bottom",
    ]
    assert payload["obligations"][0]["regionId"] == "domain-energy-barrier-region"
    assert payload["obligations"][1]["regionId"] == "initial-start-ball"
    assert payload["obligations"][2]["regionId"] == "unsafe-near-bottom"


def test_verification_problem_write_json_and_validation(tmp_path) -> None:
    system, x, v, _k, _c = _damped_oscillator()
    candidate = LyapunovCandidate(
        state=(x, v),
        function=(x**2 + v**2) / 2,
        equilibrium=(0.0, 0.0),
    )
    problem = verification_problem_from_lyapunov("simple lyapunov", system, candidate)

    output_path = tmp_path / "problem.json"
    problem.write_json(output_path)
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["name"] == "simple lyapunov"
    assert len(payload["obligations"]) == 3

    y = sp.Symbol("y", real=True)
    with pytest.raises(ValueError, match="same state"):
        verification_problem_from_obligations(
            "bad",
            (
                ProofObligation(name="first", state=(x, v), expression=x, comparison="<="),
                ProofObligation(name="second", state=(x, y), expression=x, comparison="<="),
            ),
        )
