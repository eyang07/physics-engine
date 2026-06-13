from __future__ import annotations

import json

import pytest
import sympy as sp

from engine.dynamics import (
    BarrierCandidate,
    Box,
    ControlledDiscreteSystem,
    DiscreteSystem,
    FirstOrderSystem,
    LyapunovCandidate,
    ProofObligation,
    SafetySpecification,
    SublevelSet,
)
from engine.verification import (
    AssumptionSpec,
    AdapterCapabilities,
    CandidateSpec,
    DynamicsSpec,
    InputSpec,
    MALFORMED_OBLIGATION_TARGETS,
    OBLIGATION_TARGETS,
    ObligationSpec,
    ParameterSpec,
    SCHEMA_VERSION,
    RegionGeometrySpec,
    RegionSpec,
    SOS_POLYNOMIAL_ADAPTER,
    VariableSpec,
    VerificationProblem,
    dynamics_spec_from_controlled,
    dynamics_spec_from_controlled_discrete,
    dynamics_spec_from_discrete,
    expression_spec,
    obligation_classifications,
    sos_polynomial_requirement_diagnostics,
    verification_problem_from_barrier,
    verification_problem_from_controlled_discrete_barrier,
    verification_problem_from_controlled_discrete_lyapunov,
    verification_problem_from_discrete_barrier,
    verification_problem_from_discrete_lyapunov,
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
    assert payload["system"] == "damped-oscillator"
    assert payload["id"] == "damped-oscillator-lyapunov"
    assert [variable["name"] for variable in payload["variables"]] == ["x", "v"]
    assert [parameter["name"] for parameter in payload["parameters"]] == ["c", "k"]
    assert payload["parameters"][0]["value"] == 0.5
    assert payload["parameters"][1]["value"] == 4.0
    assert [assumption["id"] for assumption in payload["assumptions"]] == [
        "parameter-c-positive",
        "parameter-k-positive",
    ]
    assert payload["assumptions"][0]["role"] == "parameter-domain"
    assert payload["assumptions"][0]["comparison"] == ">"
    assert payload["assumptions"][0]["variables"] == ["c"]
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
    assert {tuple(obligation["assumptionIds"]) for obligation in obligations} == {
        ("parameter-c-positive", "parameter-k-positive")
    }
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


def test_ir_spec_validation() -> None:
    x = sp.Symbol("x", real=True)
    expr = expression_spec(x)

    with pytest.raises(ValueError, match="continuous.*discrete"):
        DynamicsSpec(kind="hybrid", time_variable="t", state=("x",), rhs=(expr,))
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
    with pytest.raises(ValueError, match="assumption comparison"):
        AssumptionSpec(
            id="a",
            name="a",
            expression=expr,
            comparison="approximately",
        )
    with pytest.raises(ValueError, match="assumption role"):
        AssumptionSpec(
            id="a",
            name="a",
            expression=expr,
            comparison=">",
            role="evidence",
        )
    with pytest.raises(ValueError, match="rigor"):
        RegionGeometrySpec(
            region_id="r",
            role="safe",
            projection="phase",
            plane_variables=("x", "v"),
            state_axes=("x", "x_dot"),
            variable_to_state_axis={"x": "x", "v": "x_dot"},
            x_values=(0.0, 1.0),
            y_values=(0.0, 1.0),
            values=((0.0, 1.0), (1.0, 2.0)),
            level=0.0,
            convention="expression <= level",
            rigor="external-required",
        )
    with pytest.raises(ValueError, match="variable-to-state-axis"):
        RegionGeometrySpec(
            region_id="r",
            role="safe",
            projection="phase",
            plane_variables=("x", "v"),
            state_axes=("x", "x_dot"),
            variable_to_state_axis={"x": "x"},
            x_values=(0.0, 1.0),
            y_values=(0.0, 1.0),
            values=((0.0, 1.0), (1.0, 2.0)),
            level=0.0,
            convention="expression <= level",
        )
    with pytest.raises(ValueError, match="at least two points"):
        RegionGeometrySpec(
            region_id="r",
            role="safe",
            projection="phase",
            plane_variables=("x", "v"),
            state_axes=("x", "x_dot"),
            variable_to_state_axis={"x": "x", "v": "x_dot"},
            x_values=(0.0, 1.0),
            y_values=(0.0, 1.0),
            values=((0.0, 1.0), (1.0, 2.0)),
            level=0.0,
            convention="expression <= level",
            boundary_polylines=(((0.0, 0.0),),),
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
    with pytest.raises(ValueError, match="open-loop dynamics state"):
        VerificationProblem(
            id="p",
            name="p",
            source="test",
            variables=variables,
            parameters=(),
            regions=(),
            obligations=(obligation,),
            open_loop_dynamics=mismatched,
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

    assumption = AssumptionSpec(
        id="a",
        name="x nonnegative",
        expression=expr,
        comparison=">=",
        variables=("x",),
    )
    linked = ObligationSpec(
        id="linked",
        name="linked",
        expression=expr,
        comparison="<=",
        assumption_ids=("missing",),
    )
    with pytest.raises(ValueError, match="unknown obligation assumption"):
        VerificationProblem(
            id="p",
            name="p",
            source="test",
            variables=variables,
            parameters=(),
            regions=(),
            assumptions=(assumption,),
            obligations=(linked,),
        )

    with pytest.raises(ValueError, match="assumption ids"):
        VerificationProblem(
            id="p",
            name="p",
            source="test",
            variables=variables,
            parameters=(),
            regions=(),
            assumptions=(assumption, assumption),
            obligations=(obligation,),
        )

    bad_variable = AssumptionSpec(
        id="bad-var",
        name="bad variable",
        expression=expr,
        comparison=">=",
        variables=("z",),
    )
    with pytest.raises(ValueError, match="unknown assumption variables"):
        VerificationProblem(
            id="p",
            name="p",
            source="test",
            variables=variables,
            parameters=(),
            regions=(),
            assumptions=(bad_variable,),
            obligations=(obligation,),
        )


def test_problem_validates_names_and_region_variables() -> None:
    x = sp.Symbol("x", real=True)
    variables, obligation = _minimal_problem_parts()
    expr = obligation.expression

    with pytest.raises(ValueError, match="variable names"):
        VerificationProblem(
            id="p",
            name="p",
            source="test",
            variables=(variables[0], variables[0]),
            parameters=(),
            regions=(),
            obligations=(obligation,),
        )

    with pytest.raises(ValueError, match="parameter names"):
        VerificationProblem(
            id="p",
            name="p",
            source="test",
            variables=variables,
            parameters=(
                ParameterSpec(name="k", latex="k"),
                ParameterSpec(name="k", latex="k"),
            ),
            regions=(),
            obligations=(obligation,),
        )

    with pytest.raises(ValueError, match="shadow variables"):
        VerificationProblem(
            id="p",
            name="p",
            source="test",
            variables=variables,
            parameters=(ParameterSpec(name="x", latex="x"),),
            regions=(),
            obligations=(obligation,),
        )

    region = RegionSpec(
        id="bad-region",
        name="bad region",
        kind="sublevel",
        role="domain",
        variables=("z",),
        expression=expr,
        level=1.0,
    )
    with pytest.raises(ValueError, match="unknown region variables"):
        VerificationProblem(
            id="p",
            name="p",
            source="test",
            variables=variables,
            parameters=(),
            regions=(region,),
            obligations=(obligation,),
        )

    valid_region = RegionSpec(
        id="domain",
        name="domain",
        kind="sublevel",
        role="domain",
        variables=("x",),
        expression=expression_spec(x),
        level=1.0,
    )
    problem = VerificationProblem(
        id="p",
        name="p",
        source="test",
        variables=variables,
        parameters=(),
        regions=(valid_region,),
        obligations=(obligation,),
    )
    assert problem.regions == (valid_region,)

    v = sp.Symbol("v", real=True)
    variables_2d = (
        VariableSpec(name="x", latex="x"),
        VariableSpec(name="v", latex="v"),
    )
    obligation_2d = ObligationSpec(
        id="claim",
        name="claim",
        expression=expression_spec(x),
        comparison="<=",
    )
    region_2d = RegionSpec(
        id="domain",
        name="domain",
        kind="sublevel",
        role="domain",
        variables=("x", "v"),
        expression=expression_spec(x + v**2),
        level=1.0,
    )
    valid_geometry = RegionGeometrySpec(
        region_id="domain",
        role="domain",
        projection="phase",
        plane_variables=("x", "v"),
        state_axes=("x", "x_dot"),
        variable_to_state_axis={"x": "x", "v": "x_dot"},
        x_values=(0.0, 1.0),
        y_values=(0.0, 1.0),
        values=((0.0, 1.0), (1.0, 2.0)),
        level=1.0,
        convention="expression <= level",
    )
    with pytest.raises(ValueError, match="role"):
        VerificationProblem(
            id="p",
            name="p",
            source="test",
            variables=variables_2d,
            parameters=(),
            regions=(region_2d,),
            obligations=(obligation_2d,),
            region_geometry=(
                RegionGeometrySpec(
                    region_id="domain",
                    role="unsafe",
                    projection="phase",
                    plane_variables=("x", "v"),
                    state_axes=("x", "x_dot"),
                    variable_to_state_axis={"x": "x", "v": "x_dot"},
                    x_values=(0.0, 1.0),
                    y_values=(0.0, 1.0),
                    values=((0.0, 1.0), (1.0, 2.0)),
                    level=1.0,
                    convention="expression <= level",
                ),
            ),
        )
    assert (
        VerificationProblem(
            id="p",
            name="p",
            source="test",
            variables=variables_2d,
            parameters=(),
            regions=(region_2d,),
            obligations=(obligation_2d,),
            region_geometry=(valid_geometry,),
        ).region_geometry
        == (valid_geometry,)
    )


def test_obligation_classification_tracks_backend_targets() -> None:
    system, x, v, _k, _c = _damped_oscillator()
    candidate = LyapunovCandidate(
        state=(x, v),
        function=(x**2 + v**2) / 2,
        equilibrium=(0.0, 0.0),
    )
    continuous = verification_problem_from_lyapunov(
        "continuous target",
        system,
        candidate,
    )

    targets = {
        classification.target
        for classification in obligation_classifications(continuous)
    }
    assert targets == {"continuous-lyapunov"}

    xd = sp.Symbol("x", real=True)
    discrete = DiscreteSystem(state=(xd,), update=(xd / 2,))
    discrete_candidate = LyapunovCandidate(
        state=(xd,),
        function=xd**2,
        equilibrium=(0.0,),
    )
    discrete_problem = verification_problem_from_discrete_lyapunov(
        "discrete target",
        discrete,
        discrete_candidate,
    )

    (classification,) = {
        classification
        for classification in obligation_classifications(discrete_problem)
        if classification.obligation_id.endswith("decrease")
    }
    assert classification.target == "discrete-lyapunov"
    assert classification.required_capability == "discharge:discrete-lyapunov"

    variables, obligation = _minimal_problem_parts()
    generic = VerificationProblem(
        id="generic",
        name="generic",
        source="test",
        variables=variables,
        parameters=(),
        regions=(),
        obligations=(obligation,),
    )
    (generic_classification,) = obligation_classifications(generic)
    assert generic_classification.target == "obligation-only"
    assert generic_classification.candidate_kind is None

    candidate_without_dynamics = VerificationProblem(
        id="candidate-without-dynamics",
        name="candidate without dynamics",
        source="test",
        variables=variables,
        parameters=(),
        regions=(),
        obligations=(obligation,),
        candidates=(
            CandidateSpec(
                id="lyapunov-candidate",
                name="lyapunov candidate",
                kind="lyapunov",
                expression=obligation.expression,
                obligation_ids=(obligation.id,),
                equilibrium=(0.0,),
            ),
        ),
    )
    (candidate_classification,) = obligation_classifications(candidate_without_dynamics)
    assert candidate_classification.target == "candidate-without-dynamics"
    assert candidate_classification.candidate_kind == "lyapunov"
    assert candidate_classification.malformed_reason is not None

    mixed_candidate = VerificationProblem(
        id="mixed-candidate",
        name="mixed candidate",
        source="test",
        variables=variables,
        parameters=(),
        regions=(),
        obligations=(obligation,),
        candidates=(
            CandidateSpec(
                id="lyapunov-candidate",
                name="lyapunov candidate",
                kind="lyapunov",
                expression=obligation.expression,
                obligation_ids=(obligation.id,),
                equilibrium=(0.0,),
            ),
            CandidateSpec(
                id="barrier-candidate",
                name="barrier candidate",
                kind="barrier",
                expression=obligation.expression,
                obligation_ids=(obligation.id,),
            ),
        ),
    )
    (mixed_classification,) = obligation_classifications(mixed_candidate)
    assert mixed_classification.target == "mixed-candidate"
    assert mixed_classification.candidate_kind == "mixed"
    assert mixed_classification.malformed_reason is not None

    capability = AdapterCapabilities(
        adapter="test-certificate-adapter",
        supported_targets=("continuous-lyapunov",),
        supports_discharge=True,
    )
    assert capability.supports(obligation_classifications(continuous)[0])
    assert not capability.supports(generic_classification)
    assert "continuous-lyapunov" in OBLIGATION_TARGETS

    with pytest.raises(ValueError, match="non-discharging"):
        AdapterCapabilities(
            adapter="bad",
            supported_targets=("continuous-lyapunov",),
        )
    with pytest.raises(ValueError, match="malformed targets"):
        AdapterCapabilities(
            adapter="bad",
            supported_targets=("mixed-candidate",),
            supports_discharge=True,
        )
    assert set(MALFORMED_OBLIGATION_TARGETS) <= set(OBLIGATION_TARGETS)


def test_sos_polynomial_requirements_accept_polynomial_certificate_targets() -> None:
    system, x, v, _k, _c = _damped_oscillator()
    candidate = LyapunovCandidate(
        state=(x, v),
        function=(x**2 + v**2) / 2,
        equilibrium=(0.0, 0.0),
        domain=SublevelSet(
            state=(x, v),
            expression=x**2 + v**2,
            level=4.0,
            name="ball",
        ),
    )

    problem = verification_problem_from_lyapunov(
        "polynomial lyapunov",
        system,
        candidate,
    )

    assert SOS_POLYNOMIAL_ADAPTER.supports(obligation_classifications(problem)[0])
    assert sos_polynomial_requirement_diagnostics(problem) == ()


def test_sos_polynomial_requirements_reject_non_polynomial_targets() -> None:
    closed, theta, omega = _pendulum_closed_loop()
    d = theta - sp.pi
    specification = SafetySpecification(
        state=(theta, omega),
        safe_set=SublevelSet(
            state=(theta, omega),
            expression=d**2,
            level=0.25,
            name="corridor",
        ),
    )
    barrier = BarrierCandidate(
        state=(theta, omega),
        function=omega**2 + sp.cos(d),
        name="trig-barrier",
    )

    problem = verification_problem_from_barrier(
        "non polynomial barrier",
        closed,
        barrier,
        specification=specification,
    )
    diagnostics = sos_polynomial_requirement_diagnostics(problem)

    assert diagnostics
    assert {diagnostic.code for diagnostic in diagnostics} == {
        "sos.polynomial_requirement"
    }
    assert {diagnostic.status for diagnostic in diagnostics} == {"unsupported"}
    assert any(
        "dynamics.rhs.1" in diagnostic.details["requirement"]["nonPolynomialFields"]
        for diagnostic in diagnostics
        if diagnostic.details is not None
    )
    assert any(
        "candidates.trig-barrier.expression"
        in diagnostic.details["requirement"]["nonPolynomialFields"]
        for diagnostic in diagnostics
        if diagnostic.details is not None
    )


def test_sos_polynomial_requirements_reject_generic_claims() -> None:
    variables, obligation = _minimal_problem_parts()
    problem = VerificationProblem(
        id="generic",
        name="generic",
        source="test",
        variables=variables,
        parameters=(),
        regions=(),
        obligations=(obligation,),
    )

    (diagnostic,) = sos_polynomial_requirement_diagnostics(problem)

    assert diagnostic.code == "sos.target_unsupported"
    assert diagnostic.status == "unsupported"
    assert diagnostic.obligation_id == "claim"


def test_explicit_assumptions_are_serialized_and_linked_to_obligations() -> None:
    x = sp.Symbol("x", real=True)
    h = sp.Symbol("h", real=True)
    system = FirstOrderSystem(state=(x,), rhs=(-h * x,), parameters=(h,))
    assumption = AssumptionSpec(
        id="time-step-positive",
        name="time step is positive",
        role="model",
        expression=expression_spec(h),
        comparison=">",
        rhs=0.0,
        variables=("h",),
        description="External verifier may assume the model time step is positive.",
    )
    obligation = ProofObligation(
        name="decay",
        state=(x,),
        expression=-h * x**2,
        comparison="<=",
    )

    problem = verification_problem_from_obligations(
        "explicit assumptions",
        (obligation,),
        system=system,
        assumptions=(assumption,),
    )
    payload = problem.to_dict()

    assert payload["assumptions"] == [assumption.to_dict()]
    assert payload["obligations"][0]["assumptionIds"] == ["time-step-positive"]


def test_dynamics_spec_from_controlled_encodes_bounds() -> None:
    pendulum = build_system(mass=1.0, length=1.0, gravity=9.81, damping=0.1, torque_bound=2.0)
    spec = dynamics_spec_from_controlled(pendulum)

    assert spec.kind == "continuous"
    assert spec.state == ("theta", "omega")
    assert len(spec.rhs) == 2
    assert [input_spec.to_dict() for input_spec in spec.inputs] == [
        {"name": "u", "latex": "u", "role": "control", "lower": -2.0, "upper": 2.0}
    ]


def test_dynamics_spec_from_discrete_encodes_update_map() -> None:
    x = sp.Symbol("x", real=True)
    r = sp.Symbol("r", positive=True)
    system = DiscreteSystem(state=(x,), update=(r * x * (1 - x),), parameters=(r,))

    spec = dynamics_spec_from_discrete(system)
    payload = spec.to_dict()

    assert payload["kind"] == "discrete"
    assert payload["stepVariable"] == "k"
    assert payload["state"] == ["x"]
    assert "timeVariable" not in payload
    assert "rhs" not in payload
    assert payload["update"][0]["display"] == "r*x*(1 - x)"
    assert payload["inputs"] == []


def test_dynamics_spec_from_controlled_discrete_encodes_inputs() -> None:
    x, v = sp.symbols("x v", real=True)
    u, d = sp.symbols("u d", real=True)
    h = sp.Symbol("h", positive=True)
    step = sp.Symbol("n", integer=True, nonnegative=True)
    system = ControlledDiscreteSystem(
        state=(x, v),
        controls=(u,),
        update=(x + h * v, v + h * (u + d)),
        disturbances=(d,),
        parameters=(h,),
        step=step,
        control_bounds=Box(lower=(-1.0,), upper=(1.0,)),
        disturbance_bounds=Box(lower=(-0.1,), upper=(0.1,)),
    )

    spec = dynamics_spec_from_controlled_discrete(system)
    payload = spec.to_dict()

    assert payload["kind"] == "discrete"
    assert payload["stepVariable"] == "n"
    assert payload["state"] == ["x", "v"]
    assert [entry["display"] for entry in payload["update"]] == [
        "h*v + x",
        "h*(d + u) + v",
    ]
    assert payload["inputs"] == [
        {"name": "u", "latex": "u", "role": "control", "lower": -1.0, "upper": 1.0},
        {
            "name": "d",
            "latex": "d",
            "role": "disturbance",
            "lower": -0.1,
            "upper": 0.1,
        },
    ]


def test_discrete_lyapunov_candidate_exports_verification_problem() -> None:
    x = sp.Symbol("x", real=True)
    a = sp.Symbol("a", positive=True)
    system = DiscreteSystem(state=(x,), update=(a * x,), parameters=(a,))
    candidate = LyapunovCandidate(
        state=(x,),
        function=x**2,
        equilibrium=(0.0,),
        domain=SublevelSet(state=(x,), expression=x**2, level=4.0, name="interval"),
        name="contractive-map-lyapunov",
    )

    problem = verification_problem_from_discrete_lyapunov(
        "contractive map lyapunov",
        system,
        candidate,
        substitutions={a: 0.5},
    )
    payload = problem.to_dict()

    assert payload["dynamics"]["kind"] == "discrete"
    assert payload["dynamics"]["stepVariable"] == "k"
    assert payload["dynamics"]["update"][0]["display"] == "a*x"
    assert [assumption["id"] for assumption in payload["assumptions"]] == [
        "parameter-a-positive"
    ]
    assert [obligation["id"] for obligation in payload["obligations"]] == [
        "contractive-map-lyapunov-equilibrium-value",
        "contractive-map-lyapunov-positivity",
        "contractive-map-lyapunov-decrease",
    ]
    assert payload["obligations"][2]["regionId"] == "domain-interval"
    assert payload["obligations"][2]["assumptionIds"] == ["parameter-a-positive"]
    (candidate_payload,) = payload["candidates"]
    assert candidate_payload["kind"] == "lyapunov"
    assert candidate_payload["obligationIds"] == [
        obligation["id"] for obligation in payload["obligations"]
    ]


def test_discrete_barrier_candidate_exports_verification_problem() -> None:
    x = sp.Symbol("x", real=True)
    system = DiscreteSystem(state=(x,), update=(sp.Rational(1, 2) * x,))
    barrier = BarrierCandidate(state=(x,), function=x**2 - 1, name="unit-interval")
    specification = SafetySpecification(
        state=(x,),
        safe_set=SublevelSet(state=(x,), expression=x**2, level=1.0, name="safe"),
        initial_set=SublevelSet(state=(x,), expression=x**2, level=0.25, name="initial"),
        unsafe_sets=(
            SublevelSet(state=(x,), expression=-(x - 2), level=0.0, name="right-wall"),
        ),
    )

    problem = verification_problem_from_discrete_barrier(
        "unit interval discrete safety",
        system,
        barrier,
        specification=specification,
    )
    payload = problem.to_dict()

    assert payload["dynamics"]["kind"] == "discrete"
    assert [region["role"] for region in payload["regions"]] == [
        "safe",
        "initial",
        "unsafe",
        "domain",
    ]
    assert [obligation["name"] for obligation in payload["obligations"]] == [
        "unit-interval:non-increase",
        "unit-interval:initial-containment",
        "unit-interval:excludes:right-wall",
    ]
    assert payload["obligations"][0]["regionId"] == "domain-unit-interval-region"
    (candidate_payload,) = payload["candidates"]
    assert candidate_payload["kind"] == "barrier"
    assert candidate_payload["regionId"] == "domain-unit-interval-region"


def test_controlled_discrete_lyapunov_export_records_open_and_closed_loop() -> None:
    x = sp.Symbol("x", real=True)
    u = sp.Symbol("u", real=True)
    system = ControlledDiscreteSystem(
        state=(x,),
        controls=(u,),
        update=(x + u,),
        control_bounds=Box(lower=(-1.0,), upper=(1.0,)),
    )
    candidate = LyapunovCandidate(
        state=(x,),
        function=x**2,
        equilibrium=(0.0,),
        name="feedback-lyapunov",
    )

    problem = verification_problem_from_controlled_discrete_lyapunov(
        "feedback lyapunov",
        system,
        {u: -x / 2},
        candidate,
    )
    payload = problem.to_dict()

    assert payload["dynamics"]["kind"] == "discrete"
    assert payload["dynamics"]["update"][0]["display"] == "x/2"
    assert payload["dynamics"]["inputs"] == []
    assert payload["openLoopDynamics"]["kind"] == "discrete"
    assert payload["openLoopDynamics"]["update"][0]["display"] == "u + x"
    assert payload["openLoopDynamics"]["inputs"] == [
        {"name": "u", "latex": "u", "role": "control", "lower": -1.0, "upper": 1.0}
    ]
    assert payload["metadata"]["feedbackLaw"]["control"]["u"]["display"] == "-x/2"
    assert [obligation["name"] for obligation in payload["obligations"]] == [
        "feedback-lyapunov:equilibrium-value",
        "feedback-lyapunov:positivity",
        "feedback-lyapunov:decrease",
    ]
    assert payload["candidates"][0]["obligationIds"] == [
        obligation["id"] for obligation in payload["obligations"]
    ]


def test_controlled_discrete_barrier_export_records_disturbance_law() -> None:
    x = sp.Symbol("x", real=True)
    u, d = sp.symbols("u d", real=True)
    system = ControlledDiscreteSystem(
        state=(x,),
        controls=(u,),
        update=(x + u + d,),
        disturbances=(d,),
        control_bounds=Box(lower=(-1.0,), upper=(1.0,)),
        disturbance_bounds=Box(lower=(-0.25,), upper=(0.25,)),
    )
    barrier = BarrierCandidate(state=(x,), function=x**2 - 1, name="unit-interval")
    specification = SafetySpecification(
        state=(x,),
        safe_set=SublevelSet(state=(x,), expression=x**2, level=1.0, name="safe"),
    )

    problem = verification_problem_from_controlled_discrete_barrier(
        "feedback barrier",
        system,
        {u: -x / 2},
        barrier,
        disturbance_law={d: 0},
        specification=specification,
    )
    payload = problem.to_dict()

    assert payload["dynamics"]["update"][0]["display"] == "x/2"
    assert payload["openLoopDynamics"]["inputs"] == [
        {"name": "u", "latex": "u", "role": "control", "lower": -1.0, "upper": 1.0},
        {
            "name": "d",
            "latex": "d",
            "role": "disturbance",
            "lower": -0.25,
            "upper": 0.25,
        },
    ]
    assert payload["metadata"]["feedbackLaw"]["control"]["u"]["display"] == "-x/2"
    assert payload["metadata"]["feedbackLaw"]["disturbance"]["d"]["display"] == "0"
    assert payload["obligations"][0]["regionId"] == "domain-unit-interval-region"
