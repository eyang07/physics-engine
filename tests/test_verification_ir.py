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
    CandidateSpec,
    DynamicsSpec,
    InputSpec,
    ObligationSpec,
    SCHEMA_VERSION,
    VariableSpec,
    VerificationProblem,
    dynamics_spec_from_controlled,
    expression_spec,
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

    dynamics = payload["dynamics"]
    assert dynamics["kind"] == "continuous"
    assert dynamics["timeVariable"] == "t"
    assert dynamics["state"] == ["x", "v"]
    assert dynamics["rhs"][0]["display"] == "v"
    assert "k*x" in dynamics["rhs"][1]["display"]
    assert dynamics["inputs"] == []

    (candidate_payload,) = payload["candidates"]
    assert candidate_payload["kind"] == "lyapunov"
    assert candidate_payload["status"] == "candidate"
    assert candidate_payload["equilibrium"] == [0.0, 0.0]
    assert candidate_payload["regionId"] == "domain-ball"
    assert candidate_payload["obligationIds"] == [
        obligation["id"] for obligation in obligations
    ]


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

    assert payload["dynamics"]["state"] == ["theta", "omega"]
    (candidate_payload,) = payload["candidates"]
    assert candidate_payload["kind"] == "barrier"
    assert candidate_payload["regionId"] == "domain-energy-barrier-region"
    assert "equilibrium" not in candidate_payload


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


def _minimal_problem_parts() -> tuple[tuple[VariableSpec, ...], ObligationSpec]:
    x = sp.Symbol("x", real=True)
    variables = (VariableSpec(name="x", latex="x"),)
    obligation = ObligationSpec(
        id="claim", name="claim", expression=expression_spec(x), comparison="<="
    )
    return variables, obligation


def test_v1_spec_validation() -> None:
    x = sp.Symbol("x", real=True)
    expr = expression_spec(x)

    with pytest.raises(ValueError, match="continuous"):
        DynamicsSpec(kind="discrete", time_variable="t", state=("x",), rhs=(expr,))
    with pytest.raises(ValueError, match="same length"):
        DynamicsSpec(kind="continuous", time_variable="t", state=("x", "v"), rhs=(expr,))
    with pytest.raises(ValueError, match="disjoint"):
        DynamicsSpec(
            kind="continuous",
            time_variable="t",
            state=("x",),
            rhs=(expr,),
            inputs=(InputSpec(name="x", latex="x", role="control"),),
        )
    with pytest.raises(ValueError, match="role"):
        InputSpec(name="u", latex="u", role="actuator")
    with pytest.raises(ValueError, match="lower bound"):
        InputSpec(name="u", latex="u", role="control", lower=1.0, upper=-1.0)
    with pytest.raises(ValueError, match="candidate"):
        CandidateSpec(
            id="c",
            name="c",
            kind="barrier",
            expression=expr,
            obligation_ids=("claim",),
            status="accepted",
        )


def test_problem_validates_dynamics_and_candidate_links() -> None:
    variables, obligation = _minimal_problem_parts()
    expr = obligation.expression

    mismatched = DynamicsSpec(
        kind="continuous", time_variable="t", state=("y",), rhs=(expr,)
    )
    with pytest.raises(ValueError, match="dynamics state"):
        VerificationProblem(
            id="p",
            name="p",
            source="test",
            variables=variables,
            parameters=(),
            regions=(),
            obligations=(obligation,),
            dynamics=mismatched,
        )

    dangling = CandidateSpec(
        id="c",
        name="c",
        kind="barrier",
        expression=expr,
        obligation_ids=("missing",),
    )
    with pytest.raises(ValueError, match="candidate obligation"):
        VerificationProblem(
            id="p",
            name="p",
            source="test",
            variables=variables,
            parameters=(),
            regions=(),
            obligations=(obligation,),
            candidates=(dangling,),
        )


def test_dynamics_spec_from_controlled_encodes_bounds() -> None:
    pendulum = build_system(mass=1.0, length=1.0, gravity=9.81, damping=0.1, torque_bound=2.0)
    spec = dynamics_spec_from_controlled(pendulum)

    assert spec.kind == "continuous"
    assert spec.state == ("theta", "omega")
    assert len(spec.rhs) == 2
    assert [input_spec.to_dict() for input_spec in spec.inputs] == [
        {"name": "u", "latex": "u", "role": "control", "lower": -2.0, "upper": 2.0}
    ]
