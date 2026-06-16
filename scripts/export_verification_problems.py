"""Export verification-problem inspection artifacts (backend-only).

Builds representative verification problems and runs the stub inspection
adapter on them. The artifacts are for external inspection; nothing here crosses
the manifest/viewer boundary or claims proof discharge.
"""

from __future__ import annotations

import argparse
import json
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, replace
from pathlib import Path

import numpy as np
import sympy as sp

from engine.dynamics import (
    BarrierCandidate,
    Box,
    ControlledDiscreteSystem,
    DiscreteSystem,
    LyapunovCandidate,
    ProofObligation,
    SafetySpecification,
    SublevelSet,
)
from engine.export import PackageManifest, write_package, write_package_index
from engine.numerics import integrate_fixed_step
from engine.verification import (
    AssumptionSpec,
    CandidateSpec,
    InspectionAdapterReport,
    VerificationProblem,
    certificate_series_for_trajectory,
    expression_spec,
    scalar_field_region_geometries,
    sampled_region_proof_statuses,
    verification_problem_from_barrier,
    verification_problem_from_controlled_discrete_lyapunov,
    verification_problem_from_obligations,
    write_inspection_artifacts,
)
from systems.controlled_pendulum import build_system
from systems.controlled_spring import build_system as build_spring_system
from systems.drone_point_mass import (
    DEFAULT_OBSTACLE,
    DRONE_CONTROLS,
    DRONE_STATE,
    DroneParams,
    ObstacleSpec,
    horizontal_axis_closed_loop,
    horizontal_axis_rollout,
    horizontal_axis_system,
    horizontal_plane_rollout,
    vertical_axis_closed_loop,
    vertical_axis_rollout,
    vertical_axis_system,
)

DEFAULT_OUTPUT_DIR = "data/generated/verification"
INSPECTION_ARTIFACT_INDEX_FILENAME = "inspection-artifacts.index.json"
INSPECTION_ARTIFACT_INDEX_SCHEMA_VERSION = "verification-inspection-artifacts/v1"

# The verification world is self-contained: its phase plane is the problem's own
# (theta, omega) state, mapped to itself, with no dependency on any gallery
# manifest system.
_PHASE_AXES = {"theta": "theta", "omega": "omega"}
_SPRING_PHASE_AXES = {"x": "x", "v": "v"}
# The flagship drone's geofence problems are the decoupled single-axis sub-
# dynamics: the (q1, v1) horizontal axis and the (q3, v3) vertical altitude axis.
_DRONE_PHASE_AXES = {"q1": "q1", "v1": "v1"}
_DRONE_VERTICAL_PHASE_AXES = {"q3": "q3", "v3": "v3"}
# The Tier-2 obstacle problem couples the two horizontal position axes; it
# renders on the (q1, q2) position plane (spec P4).
_DRONE_PLANE_PHASE_AXES = {"q1": "q1", "q2": "q2"}


@dataclass(frozen=True)
class ViewerVerificationExample:
    """A self-contained verification problem plus the trajectory it animates."""

    problem_factory: Callable[[], VerificationProblem]
    trajectory_factory: Callable[[], tuple[np.ndarray, np.ndarray]]
    variable_to_state_axis: Mapping[str, str]


def upright_pendulum_closed_loop():
    """The PD-stabilized upright pendulum closed-loop system and its state.

    This is the single source of truth for both the verification problem and the
    controlled trajectory the viewer animates, so the obligations and the path
    describe the same system.
    """

    pendulum = build_system(mass=1.0, length=1.0, gravity=9.81, damping=0.1)
    theta, omega = pendulum.state
    (u,) = pendulum.controls
    closed = pendulum.closed_loop({u: -20 * (theta - sp.pi) - 5 * omega})
    return closed, theta, omega


def upright_pendulum_problem() -> VerificationProblem:
    """PD-stabilized upright pendulum with an energy-style barrier candidate."""

    closed, theta, omega = upright_pendulum_closed_loop()

    d = theta - sp.pi
    energy = omega**2 / 2 + 10 * d**2 + sp.Rational(981, 100) * (sp.cos(d) - 1)
    specification = SafetySpecification(
        state=(theta, omega),
        safe_set=SublevelSet(
            state=(theta, omega), expression=d**2, level=0.25, name="corridor"
        ),
        unsafe_sets=(
            SublevelSet(
                state=(theta, omega), expression=theta, level=0.2, name="near-bottom"
            ),
        ),
        initial_set=SublevelSet(
            state=(theta, omega),
            expression=d**2 + omega**2,
            level=0.09,
            name="start-ball",
        ),
    )
    barrier = BarrierCandidate(
        state=(theta, omega),
        function=energy - sp.Rational(12, 10),
        name="energy-barrier",
    )

    # The candidate construction is only valid under stated assumptions: the pole
    # stays in the upright corridor, and the PD command stays within the assumed
    # actuator bound (so the closed loop matches the model). The dynamical
    # non-increase claim depends on both; the static value claims only on the
    # operating domain.
    corridor = AssumptionSpec(
        id="operating-corridor-near-upright",
        name="state stays in the upright corridor",
        role="domain",
        expression=expression_spec(d**2),
        comparison="<=",
        rhs=0.25,
        variables=("theta", "omega"),
        description=(
            "Analysis is valid only while the pole stays within the safe corridor "
            "about the upright equilibrium theta = pi."
        ),
    )
    actuator_bound = AssumptionSpec(
        id="pd-command-within-actuator-bound",
        name="PD command stays within the actuator bound",
        role="model",
        expression=expression_spec((-20 * d - 5 * omega) ** 2),
        comparison="<=",
        rhs=625.0,
        variables=("theta", "omega"),
        description=(
            "The PD law's commanded torque stays within the assumed actuator limit, "
            "so the closed-loop field matches the modeled dynamics."
        ),
    )
    obligation_assumptions = {
        "energy-barrier:non-increase": (corridor.id, actuator_bound.id),
        "energy-barrier:initial-containment": (corridor.id,),
        "energy-barrier:excludes:near-bottom": (corridor.id,),
    }

    problem = verification_problem_from_barrier(
        "upright pendulum safety",
        closed,
        barrier,
        specification=specification,
        assumptions=(corridor, actuator_bound),
        obligation_assumptions=obligation_assumptions,
        metadata={"verificationModel": "controlled-pendulum-closed-loop"},
    )
    geometry = scalar_field_region_geometries(
        problem.regions,
        projection="phase",
        plane_variables=("theta", "omega"),
        variable_to_state_axis=_PHASE_AXES,
        x_range=(-0.5, 4.0),
        y_range=(-3.0, 3.0),
        samples=(91, 91),
    )
    problem = replace(problem, region_geometry=geometry)
    return replace(problem, proof_statuses=sampled_region_proof_statuses(problem))


def upright_pendulum_trajectory(
    *,
    theta0: float = float(sp.pi) - 0.25,
    omega0: float = 0.0,
    t_span: tuple[float, float] = (0.0, 8.0),
    dt: float = 0.01,
) -> tuple[np.ndarray, np.ndarray]:
    """Integrate the closed loop from a point inside the initial set.

    Starting near upright, the PD controller holds the pole there, so the path
    stays in the safe corridor — the coherent motion the obligations are about.
    Returns ``(time, states)`` with state columns ``(theta, omega)``.
    """

    closed, _, _ = upright_pendulum_closed_loop()
    time, states = integrate_fixed_step(
        closed.numerical_rhs(),
        initial_state=[float(theta0), float(omega0)],
        t_span=t_span,
        dt=dt,
    )
    return time, states


def spring_mass_closed_loop():
    """The controlled spring-mass regulator closed-loop system and its state."""

    spring = build_spring_system(
        mass=sp.Integer(1),
        stiffness=sp.Integer(1),
        damping=sp.Rational(2, 5),
    )
    x, v = spring.state
    (u,) = spring.controls
    closed = spring.closed_loop({u: -x - sp.Rational(13, 5) * v})
    return closed, x, v


def controlled_spring_problem() -> VerificationProblem:
    """Controlled spring-mass regulator with a quadratic barrier candidate."""

    closed, x, v = spring_mass_closed_loop()

    regulated_energy = x**2 + x * v + v**2
    specification = SafetySpecification(
        state=(x, v),
        safe_set=SublevelSet(
            state=(x, v),
            expression=regulated_energy,
            level=1.0,
            name="regulated-energy",
        ),
        unsafe_sets=(
            SublevelSet(
                state=(x, v),
                expression=-regulated_energy,
                level=-1.5,
                name="outside-energy-envelope",
            ),
        ),
        initial_set=SublevelSet(
            state=(x, v),
            expression=regulated_energy,
            level=0.16,
            name="start-ellipse",
        ),
    )
    barrier = BarrierCandidate(
        state=(x, v),
        function=regulated_energy - 1,
        name="regulated-energy-barrier",
    )

    # Stated assumptions the candidate relies on: the state stays within the
    # regulated-energy envelope, and the regulator command stays within the
    # assumed actuator bound. Only the dynamical non-increase claim depends on
    # the actuator bound; the value claims depend on the operating envelope.
    envelope = AssumptionSpec(
        id="operating-within-energy-envelope",
        name="state stays within the energy envelope",
        role="domain",
        expression=expression_spec(regulated_energy),
        comparison="<=",
        rhs=1.0,
        variables=("x", "v"),
        description=(
            "Analysis is valid only while the state stays within the regulated-energy "
            "envelope where the quadratic barrier governs the motion."
        ),
    )
    actuator_bound = AssumptionSpec(
        id="regulator-command-within-actuator-bound",
        name="regulator command stays within the actuator bound",
        role="model",
        expression=expression_spec((-x - sp.Rational(13, 5) * v) ** 2),
        comparison="<=",
        rhs=9.0,
        variables=("x", "v"),
        description=(
            "The regulator's commanded force stays within the assumed actuator limit, "
            "so the closed-loop field matches the modeled dynamics."
        ),
    )
    obligation_assumptions = {
        "regulated-energy-barrier:non-increase": (envelope.id, actuator_bound.id),
        "regulated-energy-barrier:initial-containment": (envelope.id,),
        "regulated-energy-barrier:excludes:outside-energy-envelope": (envelope.id,),
    }

    problem = verification_problem_from_barrier(
        "controlled spring regulator safety",
        closed,
        barrier,
        specification=specification,
        assumptions=(envelope, actuator_bound),
        obligation_assumptions=obligation_assumptions,
        metadata={"verificationModel": "controlled-spring-regulator"},
    )
    geometry = scalar_field_region_geometries(
        problem.regions,
        projection="phase",
        plane_variables=("x", "v"),
        variable_to_state_axis=_SPRING_PHASE_AXES,
        x_range=(-1.8, 1.8),
        y_range=(-1.8, 1.8),
        samples=(81, 81),
    )
    problem = replace(problem, region_geometry=geometry)
    return replace(problem, proof_statuses=sampled_region_proof_statuses(problem))


def controlled_spring_trajectory(
    *,
    x0: float = 0.35,
    v0: float = -0.1,
    t_span: tuple[float, float] = (0.0, 8.0),
    dt: float = 0.01,
) -> tuple[np.ndarray, np.ndarray]:
    """Integrate the regulated spring-mass closed loop inside the initial set."""

    closed, _, _ = spring_mass_closed_loop()
    time, states = integrate_fixed_step(
        closed.numerical_rhs(),
        initial_state=[float(x0), float(v0)],
        t_span=t_span,
        dt=dt,
    )
    return time, states


def _drone_rational(value: float) -> sp.Expr:
    return sp.nsimplify(value, rational=True)


@dataclass(frozen=True)
class _AxisGeofenceSpec:
    """The per-axis data the shared Tier-1 geofence builder needs.

    Captures the decoupled single-axis sub-dynamics, its geofence/guard-band
    geometry, and the axis-specific obligation/assumption prose so the horizontal
    and vertical altitude problems share one assembly path.
    """

    problem_name: str
    model: str
    position: sp.Symbol
    velocity: sp.Symbol
    open_loop: ControlledDiscreteSystem
    closed: DiscreteSystem
    pos_bounds: tuple[float, float]
    lower_band: float
    upper_band: float
    velocity_bound: float
    reach: float
    timestep: float
    plane_variables: tuple[str, str]
    variable_to_state_axis: Mapping[str, str]
    x_range: tuple[float, float]
    y_range: tuple[float, float]
    forward_invariance_description: str
    velocity_invariance_description: str
    inner_set_description: str
    speed_bound_name: str
    speed_bound_description: str
    velocity_bound_name: str
    velocity_bound_description: str
    timestep_small_name: str
    timestep_small_description: str
    drift_bound_name: str
    drift_bound_description: str


def _drone_axis_geofence_problem(spec: _AxisGeofenceSpec) -> VerificationProblem:
    """Assemble one decoupled-axis Tier-1 geofence verification problem.

    Builds the geofence/velocity/inner-set barrier candidates, their one-step
    invariance obligations, the spec-G domain assumptions, the `(q, v)` region
    geometry, and the measured proof statuses (sampled within each obligation's
    assumption region). Every obligation is `external-required`; the candidates
    are proposals only. Shared by the horizontal and vertical altitude axes.
    """

    q = spec.position
    v = spec.velocity
    open_loop = spec.open_loop
    closed = spec.closed
    q_min, q_max = spec.pos_bounds
    lower_band = spec.lower_band
    upper_band = spec.upper_band
    velocity_bound = spec.velocity_bound
    half_reach = spec.reach * spec.timestep / 2
    r = _drone_rational
    dt = r(spec.timestep)
    pos_name, vel_name = q.name, v.name

    barrier_expression = sp.Max(r(q_min) - q, q - r(q_max))
    barrier = BarrierCandidate(
        state=(q, v), function=barrier_expression, name="geofence-barrier"
    )
    safe_set = SublevelSet(
        state=(q, v), expression=barrier_expression, level=0.0, name="geofence"
    )
    inner_start_expression = sp.Max(
        r(q_min) + r(lower_band) - q,
        q - (r(q_max) - r(upper_band)),
        sp.Abs(v) - r(velocity_bound),
    )
    inner_start_set = SublevelSet(
        state=(q, v), expression=inner_start_expression, level=0.0, name="inner-start"
    )
    velocity_barrier_expression = sp.Abs(v) - r(velocity_bound)
    velocity_bound_set = SublevelSet(
        state=(q, v),
        expression=velocity_barrier_expression,
        level=0.0,
        name="velocity-bound",
    )
    specification = SafetySpecification(
        state=(q, v), safe_set=safe_set, initial_set=inner_start_set
    )

    next_state = {q: closed.update[0], v: closed.update[1]}
    forward_invariance = ProofObligation(
        name="geofence-barrier:forward-invariance",
        state=(q, v),
        expression=barrier_expression.subs(next_state, simultaneous=True),
        comparison="<=",
        region=barrier.candidate_region(),
        description=spec.forward_invariance_description,
    )
    initial_containment = ProofObligation(
        name="geofence-barrier:initial-containment",
        state=(q, v),
        expression=barrier_expression,
        comparison="<=",
        region=inner_start_set,
        description="B <= 0 on the inner start set: the initial set lies inside the geofence.",
    )
    velocity_invariance = ProofObligation(
        name="velocity-bound:one-step-invariance",
        state=(q, v),
        expression=velocity_barrier_expression.subs(next_state, simultaneous=True),
        comparison="<=",
        region=velocity_bound_set,
        description=spec.velocity_invariance_description,
    )
    inner_set_invariance = ProofObligation(
        name="inner-set:one-step-invariance",
        state=(q, v),
        expression=inner_start_expression.subs(next_state, simultaneous=True),
        comparison="<=",
        region=inner_start_set,
        description=spec.inner_set_description,
    )

    drift = q + dt * v
    speed_bound = AssumptionSpec(
        id="speed-within-half-guard-reach",
        name=spec.speed_bound_name,
        role="domain",
        expression=expression_spec(sp.Abs(v)),
        comparison="<=",
        rhs=float(half_reach),
        variables=(vel_name,),
        description=spec.speed_bound_description,
    )
    velocity_bound_assumption = AssumptionSpec(
        id="velocity-within-self-reproducing-bound",
        name=spec.velocity_bound_name,
        role="domain",
        expression=expression_spec(sp.Abs(v)),
        comparison="<=",
        rhs=float(velocity_bound),
        variables=(vel_name,),
        description=spec.velocity_bound_description,
    )
    timestep_small = AssumptionSpec(
        id="timestep-small-vs-guard-band",
        name=spec.timestep_small_name,
        role="parameter-domain",
        expression=expression_spec(r(spec.reach) * dt**2 / 2),
        comparison="<=",
        rhs=float(min(lower_band, upper_band)),
        variables=(),
        description=spec.timestep_small_description,
    )
    drift_bound = AssumptionSpec(
        id="linear-drift-within-inner-interval",
        name=spec.drift_bound_name,
        role="domain",
        expression=expression_spec(
            sp.Max(r(q_min) + r(lower_band) - drift, drift - (r(q_max) - r(upper_band)))
        ),
        comparison="<=",
        rhs=0.0,
        variables=(pos_name, vel_name),
        description=spec.drift_bound_description,
    )

    problem = verification_problem_from_obligations(
        spec.problem_name,
        (
            forward_invariance,
            initial_containment,
            velocity_invariance,
            inner_set_invariance,
        ),
        system=closed,
        open_loop_system=open_loop,
        specification=specification,
        assumptions=(
            speed_bound,
            velocity_bound_assumption,
            timestep_small,
            drift_bound,
        ),
        obligation_assumptions={
            "geofence-barrier:forward-invariance": (
                "speed-within-half-guard-reach",
                "timestep-small-vs-guard-band",
            ),
            "geofence-barrier:initial-containment": (),
            "velocity-bound:one-step-invariance": (
                "velocity-within-self-reproducing-bound",
            ),
            "inner-set:one-step-invariance": ("linear-drift-within-inner-interval",),
        },
        metadata={"verificationModel": spec.model},
    )

    # Attach the three Tier-1 barrier candidates, each linked only to its own
    # obligation(s) (the single-candidate adapter would link one barrier to all
    # obligations, which would mislabel the velocity and inner-set certificates).
    region_id_by_name = {region.name: region.id for region in problem.regions}
    obligation_id_by_name = {
        obligation.name: obligation.id for obligation in problem.obligations
    }
    candidates = (
        CandidateSpec(
            id="geofence-barrier",
            name="geofence-barrier",
            kind="barrier",
            expression=expression_spec(barrier_expression),
            obligation_ids=(
                obligation_id_by_name["geofence-barrier:forward-invariance"],
                obligation_id_by_name["geofence-barrier:initial-containment"],
            ),
            region_id=region_id_by_name["geofence-barrier:region"],
        ),
        CandidateSpec(
            id="velocity-bound-barrier",
            name="velocity-bound-barrier",
            kind="barrier",
            expression=expression_spec(velocity_barrier_expression),
            obligation_ids=(
                obligation_id_by_name["velocity-bound:one-step-invariance"],
            ),
            region_id=region_id_by_name["velocity-bound"],
        ),
        CandidateSpec(
            id="inner-set-barrier",
            name="inner-set-barrier",
            kind="barrier",
            expression=expression_spec(inner_start_expression),
            obligation_ids=(
                obligation_id_by_name["inner-set:one-step-invariance"],
            ),
            region_id=region_id_by_name["inner-start"],
        ),
    )
    problem = replace(problem, candidates=candidates)

    geometry = scalar_field_region_geometries(
        problem.regions,
        projection="phase",
        plane_variables=spec.plane_variables,
        variable_to_state_axis=spec.variable_to_state_axis,
        x_range=spec.x_range,
        y_range=spec.y_range,
        samples=(81, 81),
    )
    problem = replace(problem, region_geometry=geometry)
    # Each one-step invariance claim is asserted only under its stated assumption
    # (speedBound, velBound, driftBound); sample within that region rather than
    # over all velocities, where a single guard-band step can overshoot.
    return replace(
        problem,
        proof_statuses=sampled_region_proof_statuses(
            problem, restrict_to_assumption_regions=True
        ),
    )


def drone_geofence_problem(params: DroneParams = DroneParams()) -> VerificationProblem:
    """Flagship Tier-1 verification problem for the drone's horizontal axis.

    The decoupled `(q1, v1)` guard-band closed loop, carrying the full set of
    spec-G assumptions and the three Tier-1 barrier candidates with their
    one-step invariance obligations (spec K, L):

    - geofence barrier `B = max(q1Min - q1, q1 - q1Max)` with P1 forward
      invariance under `speedBound` + `dtSmall`, plus initial containment;
    - velocity barrier `B_vel = |v1| - Bh` with P2 self-reproducing velocity
      invariance under `velBound`;
    - inner-set barrier `B_in` with S_in one-step invariance under `driftBound`.

    Every obligation is `external-required`; the candidates are proposals only.
    Renders on the `(q1, v1)` phase plane (spec M).
    """

    spec = _AxisGeofenceSpec(
        problem_name="drone geofence axis",
        model="drone-geofence-axis",
        position=DRONE_STATE[0],
        velocity=DRONE_STATE[3],
        open_loop=horizontal_axis_system(params),
        closed=horizontal_axis_closed_loop(params),
        pos_bounds=params.q1_bounds,
        lower_band=params.horizontal_band,
        upper_band=params.horizontal_band,
        velocity_bound=params.horizontal_velocity_bound,
        reach=params.horizontal_thrust,
        timestep=params.timestep,
        plane_variables=("q1", "v1"),
        variable_to_state_axis=_DRONE_PHASE_AXES,
        x_range=(-1.1, 1.1),
        y_range=(-0.35, 0.35),
        forward_invariance_description=(
            "B(F(x)) <= 0 on {B <= 0}: one guard-band step keeps the drone inside "
            "the geofence (Tier-1 P1)."
        ),
        velocity_invariance_description=(
            "B_vel(F(x)) <= 0 on {|v1| <= Bh}: the per-axis velocity bound Bh = uh*dt "
            "is self-reproducing under one closed-loop step (Tier-1 P2)."
        ),
        inner_set_description=(
            "B_in(F(x)) <= 0 on {B_in <= 0}: one step keeps the drone in the inner "
            "set S_in, the supporting invariant for recovery (Tier-1 P3 support)."
        ),
        speed_bound_name="per-step speed within half the guard reach",
        speed_bound_description=(
            "Speed stays within uh*dt/2 so corrective thrust arrests outward motion "
            "before the wall (spec G speedBound; precondition of P1)."
        ),
        velocity_bound_name="speed within the self-reproducing velocity bound",
        velocity_bound_description=(
            "Speed stays within Bh = uh*dt, the per-axis bound the closed loop "
            "preserves (spec G velBound; invariant established by P2)."
        ),
        timestep_small_name="one step's braking displacement fits the guard band",
        timestep_small_description=(
            "uh*dt^2/2 <= dh: one step's worst corrective displacement fits inside "
            "the guard band (spec G dtSmall; precondition of P1)."
        ),
        drift_bound_name="linear drift stays in the inner interval",
        drift_bound_description=(
            "q1Min+dh <= q1 + dt*v1 <= q1Max-dh: the linear drift stays in the inner "
            "interval (spec G driftBound; precondition of S_in invariance)."
        ),
    )
    return _drone_axis_geofence_problem(spec)


def drone_vertical_geofence_problem(
    params: DroneParams = DroneParams(),
) -> VerificationProblem:
    """Flagship Tier-1 verification problem for the drone's vertical altitude axis.

    The decoupled `(q3, v3)` guard-band closed loop — the asymmetric vertical
    regime (gravity, hover thrust, floor/ceiling guard bands, thrust box
    `[u3Min, u3Max]`). It mirrors the horizontal BE-043 structure with the same
    three Tier-1 barrier candidates and obligations, here the floor/ceiling P1
    forward invariance and the vertical P2 velocity bound `B3 = max(u3Max-g,
    g-u3Min)*dt` (spec E `B3`), each under the corresponding spec-G assumptions.

    Every obligation is `external-required`; the candidates are proposals only.
    Renders on the `(q3, v3)` phase plane (spec M).
    """

    spec = _AxisGeofenceSpec(
        problem_name="drone vertical axis",
        model="drone-vertical-axis",
        position=DRONE_STATE[2],
        velocity=DRONE_STATE[5],
        open_loop=vertical_axis_system(params),
        closed=vertical_axis_closed_loop(params),
        pos_bounds=params.q3_bounds,
        lower_band=params.floor_band,
        upper_band=params.ceiling_band,
        velocity_bound=params.vertical_velocity_bound,
        reach=params.vertical_reach,
        timestep=params.timestep,
        plane_variables=("q3", "v3"),
        variable_to_state_axis=_DRONE_VERTICAL_PHASE_AXES,
        x_range=(-0.1, 2.1),
        y_range=(-0.35, 0.35),
        forward_invariance_description=(
            "B3(F(x)) <= 0 on {B3 <= 0}: one guard-band step keeps the drone between "
            "the floor and ceiling (Tier-1 P1)."
        ),
        velocity_invariance_description=(
            "B_vel(F(x)) <= 0 on {|v3| <= B3}: the vertical velocity bound "
            "B3 = max(u3Max-g, g-u3Min)*dt is self-reproducing under one closed-loop "
            "step (Tier-1 P2, spec E B3)."
        ),
        inner_set_description=(
            "B_in(F(x)) <= 0 on {B_in <= 0}: one step keeps the drone in the inner "
            "altitude set S_in, the supporting invariant for recovery (Tier-1 P3 "
            "support)."
        ),
        speed_bound_name="per-step vertical speed within half the guard reach",
        speed_bound_description=(
            "Vertical speed stays within max(u3Max-g, g-u3Min)*dt/2 so floor/ceiling "
            "thrust arrests outward motion before the bound (spec G speedBound; "
            "precondition of P1)."
        ),
        velocity_bound_name="vertical speed within the self-reproducing velocity bound",
        velocity_bound_description=(
            "Vertical speed stays within B3 = max(u3Max-g, g-u3Min)*dt, the bound the "
            "closed loop preserves (spec G velBound; invariant established by P2)."
        ),
        timestep_small_name="one step's vertical braking displacement fits the guard band",
        timestep_small_description=(
            "max(u3Max-g, g-u3Min)*dt^2/2 <= min(floor, ceiling band): one step's "
            "worst corrective displacement fits inside the guard band (spec G dtSmall; "
            "precondition of P1)."
        ),
        drift_bound_name="linear altitude drift stays in the inner interval",
        drift_bound_description=(
            "q3Min+floor <= q3 + dt*v3 <= q3Max-ceiling: the linear altitude drift "
            "stays in the inner interval (spec G driftBound; precondition of S_in "
            "invariance)."
        ),
    )
    return _drone_axis_geofence_problem(spec)


def drone_geofence_trajectory(
    params: DroneParams = DroneParams(),
) -> tuple[np.ndarray, np.ndarray]:
    """Integrate the axis-1 guard-band closed loop; columns ``(q1, v1)``.

    The drone coasts outward at the velocity bound, reaches the guard band, and
    brakes — staying strictly inside the geofence. Discrete-time axis: step `k`
    maps to time `k * dt`.
    """

    result = horizontal_axis_rollout(params)
    time = result.steps.astype(float) * params.timestep
    return time, result.states


def drone_vertical_geofence_trajectory(
    params: DroneParams = DroneParams(),
) -> tuple[np.ndarray, np.ndarray]:
    """Integrate the axis-3 guard-band closed loop; columns ``(q3, v3)``.

    The drone coasts upward at the vertical velocity bound, reaches the ceiling
    guard band, and brakes — staying strictly between floor and ceiling.
    Discrete-time axis: step `k` maps to time `k * dt`.
    """

    result = vertical_axis_rollout(params)
    time = result.steps.astype(float) * params.timestep
    return time, result.states


def drone_obstacle_keepout_problem(
    params: DroneParams = DroneParams(),
    obstacle: ObstacleSpec = DEFAULT_OBSTACLE,
) -> VerificationProblem:
    """Tier-2 obstacle keep-out problem on the coupled ``(q1, q2)`` plane (spec P4).

    A circular obstacle of radius ``rho`` centered in the geofence is the keep-out
    region ``{B_obs <= 0}`` with the signed-distance barrier ``B_obs = rho - |q - c|``
    (negative outside the obstacle, coupling q1 and q2). In the geofence interior
    the guard band commands zero thrust, so one closed-loop step is the coasting
    drift ``q+ = q + dt v`` with the planar velocity ``(v1, v2)`` a bounded
    parameter. For any admissible velocity (``|v| <= Vmax = sqrt(2)*Bh``) one step
    moves the drone at most ``dt*Vmax``, so the worst-case one-step keep-out claim
    is ``rho - |q+| <= rho - (|q| - dt*Vmax) <= 0`` whenever the drone keeps a
    standoff ``|q - c| >= R`` with ``R = rho + dt*Vmax``.

    The avoidance obligation samples that worst-case condition on the keep-out set,
    measured-holding within the standoff annulus and the geofence interior; the
    velocity bound is a non-plane assumption left for external discharge. Every
    obligation is ``external-required`` and the keep-out barrier is a candidate
    only. Renders on the ``(q1, q2)`` plane.
    """

    q1, q2 = DRONE_STATE[0], DRONE_STATE[1]
    v1, v2 = DRONE_STATE[3], DRONE_STATE[4]
    r = _drone_rational
    dt = r(params.timestep)
    cx, cy = obstacle.center
    rho = r(obstacle.radius)
    standoff = r(obstacle.standoff_radius)
    # Worst-case planar speed for per-axis |vi| <= Bh, and the displacement one
    # coasting step of that speed can produce.
    speed_max = sp.sqrt(2) * r(params.horizontal_velocity_bound)
    drift = dt * speed_max

    dist = sp.sqrt((q1 - r(cx)) ** 2 + (q2 - r(cy)) ** 2)
    keepout_expression = rho - dist
    standoff_expression = standoff - dist
    keepout_set = SublevelSet(
        state=(q1, q2), expression=keepout_expression, level=0.0, name="keep-out"
    )
    standoff_set = SublevelSet(
        state=(q1, q2), expression=standoff_expression, level=0.0, name="standoff"
    )
    specification = SafetySpecification(
        state=(q1, q2), safe_set=keepout_set, initial_set=standoff_set
    )

    avoidance = ProofObligation(
        name="obstacle-keepout:one-step-avoidance",
        state=(q1, q2),
        expression=keepout_expression + drift,
        comparison="<=",
        region=keepout_set,
        description=(
            "rho - |q - c| + dt*Vmax <= 0 on {B_obs <= 0}: the worst-case one-step "
            "coasting drift keeps the drone outside the obstacle (Tier-2 P4)."
        ),
    )
    initial_containment = ProofObligation(
        name="obstacle-keepout:initial-containment",
        state=(q1, q2),
        expression=keepout_expression,
        comparison="<=",
        region=standoff_set,
        description=(
            "B_obs <= 0 on the standoff annulus: the operating region lies outside "
            "the obstacle."
        ),
    )

    # Coasting kinematics in the geofence interior: q+ = q + dt v, with the planar
    # velocity (v1, v2) a bounded parameter the velocity bound constrains.
    dynamics = DiscreteSystem(
        state=(q1, q2),
        update=(q1 + dt * v1, q2 + dt * v2),
        parameters=(v1, v2),
    )

    speed_bound = AssumptionSpec(
        id="planar-speed-within-velocity-bound",
        name="planar speed within the closed-loop velocity bound",
        role="domain",
        expression=expression_spec(sp.sqrt(v1**2 + v2**2)),
        comparison="<=",
        rhs=float(speed_max),
        variables=("v1", "v2"),
        description=(
            "Planar speed stays within Vmax = sqrt(2)*Bh, the per-axis closed-loop "
            "velocity bound, so one coasting step drifts at most dt*Vmax (spec G "
            "velBound). Not plane-expressible in (q1, q2); left for external discharge."
        ),
    )
    maintains_standoff = AssumptionSpec(
        id="drone-maintains-obstacle-standoff",
        name="drone keeps the standoff distance from the obstacle",
        role="domain",
        expression=expression_spec(standoff_expression),
        comparison="<=",
        rhs=0.0,
        variables=("q1", "q2"),
        description=(
            "|q - c| >= R: the drone operates outside the standoff annulus, the "
            "region the one-step keep-out argument is asserted within (analogous to "
            "the geofence speed bound)."
        ),
    )
    q1_min, q1_max = params.q1_bounds
    q2_min, q2_max = params.q2_bounds
    band = r(params.horizontal_band)
    interior = AssumptionSpec(
        id="operating-region-within-guard-band-interior",
        name="operating region lies in the guard-band interior",
        role="domain",
        expression=expression_spec(
            sp.Max(
                r(q1_min) + band - q1,
                q1 - (r(q1_max) - band),
                r(q2_min) + band - q2,
                q2 - (r(q2_max) - band),
            )
        ),
        comparison="<=",
        rhs=0.0,
        variables=("q1", "q2"),
        description=(
            "q in [qMin+dh, qMax-dh]^2: the obstacle and its standoff lie in the "
            "geofence interior, where the guard band commands zero thrust so the "
            "closed-loop step is the pure coasting drift."
        ),
    )
    standoff_margin = AssumptionSpec(
        id="standoff-exceeds-worst-case-drift",
        name="standoff radius leaves room for one worst-case drift step",
        role="parameter-domain",
        expression=expression_spec(rho + drift),
        comparison="<=",
        rhs=float(standoff),
        variables=(),
        description=(
            "rho + dt*Vmax <= R: the standoff radius exceeds the obstacle radius by "
            "more than one worst-case coasting step (precondition of one-step "
            "avoidance)."
        ),
    )

    problem = verification_problem_from_obligations(
        "drone obstacle keepout",
        (avoidance, initial_containment),
        system=dynamics,
        specification=specification,
        assumptions=(speed_bound, maintains_standoff, interior, standoff_margin),
        obligation_assumptions={
            "obstacle-keepout:one-step-avoidance": (
                "planar-speed-within-velocity-bound",
                "drone-maintains-obstacle-standoff",
                "operating-region-within-guard-band-interior",
                "standoff-exceeds-worst-case-drift",
            ),
            "obstacle-keepout:initial-containment": (),
        },
        metadata={"verificationModel": "drone-obstacle-keepout"},
    )

    region_id_by_name = {region.name: region.id for region in problem.regions}
    obligation_id_by_name = {
        obligation.name: obligation.id for obligation in problem.obligations
    }
    candidates = (
        CandidateSpec(
            id="obstacle-keepout-barrier",
            name="obstacle-keepout-barrier",
            kind="barrier",
            expression=expression_spec(keepout_expression),
            obligation_ids=(
                obligation_id_by_name["obstacle-keepout:one-step-avoidance"],
                obligation_id_by_name["obstacle-keepout:initial-containment"],
            ),
            region_id=region_id_by_name["keep-out"],
        ),
    )
    problem = replace(problem, candidates=candidates)

    geometry = scalar_field_region_geometries(
        problem.regions,
        projection="phase",
        plane_variables=("q1", "q2"),
        variable_to_state_axis=_DRONE_PLANE_PHASE_AXES,
        x_range=(-1.1, 1.1),
        y_range=(-1.1, 1.1),
        samples=(81, 81),
    )
    problem = replace(problem, region_geometry=geometry)
    # The avoidance claim holds only where the standoff and interior assumptions
    # hold; sample within that region (the velocity bound is external-required).
    return replace(
        problem,
        proof_statuses=sampled_region_proof_statuses(
            problem, restrict_to_assumption_regions=True
        ),
    )


def drone_obstacle_keepout_trajectory(
    params: DroneParams = DroneParams(),
) -> tuple[np.ndarray, np.ndarray]:
    """Integrate the coupled plane guard-band loop; columns ``(q1, q2)``.

    The drone coasts in +q1 above the centered obstacle, staying clear of the
    keep-out region throughout. Discrete-time axis: step `k` maps to `k * dt`.
    Returns the `(q1, q2)` position projection of the 4-D rollout.
    """

    result = horizontal_plane_rollout(params)
    time = result.steps.astype(float) * params.timestep
    return time, result.states[:, :2]


def viewer_verification_examples() -> tuple[ViewerVerificationExample, ...]:
    """Every self-contained verification problem exported to the viewer."""

    return (
        ViewerVerificationExample(
            problem_factory=upright_pendulum_problem,
            trajectory_factory=upright_pendulum_trajectory,
            variable_to_state_axis=_PHASE_AXES,
        ),
        ViewerVerificationExample(
            problem_factory=controlled_spring_problem,
            trajectory_factory=controlled_spring_trajectory,
            variable_to_state_axis=_SPRING_PHASE_AXES,
        ),
        ViewerVerificationExample(
            problem_factory=drone_geofence_problem,
            trajectory_factory=drone_geofence_trajectory,
            variable_to_state_axis=_DRONE_PHASE_AXES,
        ),
        ViewerVerificationExample(
            problem_factory=drone_vertical_geofence_problem,
            trajectory_factory=drone_vertical_geofence_trajectory,
            variable_to_state_axis=_DRONE_VERTICAL_PHASE_AXES,
        ),
        ViewerVerificationExample(
            problem_factory=drone_obstacle_keepout_problem,
            trajectory_factory=drone_obstacle_keepout_trajectory,
            variable_to_state_axis=_DRONE_PLANE_PHASE_AXES,
        ),
    )


def controlled_trajectory_payload(
    problem: VerificationProblem,
    example: ViewerVerificationExample,
) -> dict:
    """The controlled path plus its candidate-certificate series.

    The viewer animates this self-contained trajectory in the Verification world;
    the certificate series are evaluated along the very system the obligations are
    derived for, so the path and the barrier describe one system.
    """

    time, states = example.trajectory_factory()
    state_names = [variable.name for variable in problem.variables]
    diagnostics = certificate_series_for_trajectory(
        problem,
        time=time,
        states=states,
        state_names=state_names,
        variable_to_state_axis=example.variable_to_state_axis,
    )
    return {
        "time": [float(value) for value in time],
        "stateNames": state_names,
        "states": np.asarray(states, dtype=float).tolist(),
        "series": {name: list(values) for name, values in diagnostics.series.items()},
        "certificateSeries": list(diagnostics.metadata),
    }


def verification_package_inputs() -> tuple[tuple[VerificationProblem, dict], ...]:
    """Each viewer example as a (problem, trajectory payload) package input."""

    inputs: list[tuple[VerificationProblem, dict]] = []
    for example in viewer_verification_examples():
        problem = example.problem_factory()
        inputs.append((problem, controlled_trajectory_payload(problem, example)))
    return tuple(inputs)


def write_verification_packages(directory: str | Path) -> list[PackageManifest]:
    """Write one self-contained verification package per viewer example.

    Each package lands under ``directory/<problem_id>/`` and a discovery index
    (``packages.index.json``) is written beside them so external tools and the
    viewer can enumerate every package without walking the tree. Output is
    deterministic and regenerable; keep it uncommitted like the other generated
    data.
    """

    output_dir = Path(directory)
    manifests: list[PackageManifest] = []
    for problem, trajectory in verification_package_inputs():
        manifests.append(
            write_package(
                problem,
                trajectory,
                output_dir / problem.id,
                include_adapter_stubs=True,
            )
        )
    write_package_index(output_dir, manifests)
    return manifests


def controlled_discrete_decay_problem() -> VerificationProblem:
    """Controlled discrete regulator fixture for inspection artifacts.

    This backend-only problem keeps controlled-discrete export coverage out of
    unit-only IR tests: the inspection artifact path sees the closed-loop map,
    preserved open-loop input channel, symbolic feedback law, and candidate
    obligation links.
    """

    x = sp.Symbol("x", real=True)
    u = sp.Symbol("u", real=True)
    controlled = ControlledDiscreteSystem(
        state=(x,),
        controls=(u,),
        update=(x + u,),
        control_bounds=Box(lower=(-1.0,), upper=(1.0,)),
    )
    candidate = LyapunovCandidate(
        state=(x,),
        function=x**2,
        equilibrium=(0.0,),
        domain=SublevelSet(state=(x,), expression=x**2, level=1.0, name="unit-domain"),
        name="discrete-decay-lyapunov",
    )
    return verification_problem_from_controlled_discrete_lyapunov(
        "controlled discrete decay lyapunov",
        controlled,
        {u: -x / 2},
        candidate,
        metadata={"verificationModel": "controlled-discrete-decay"},
    )


def inspection_artifact_problems() -> tuple[VerificationProblem, ...]:
    """Backend-only problems written by the inspection artifact script."""

    return (
        upright_pendulum_problem(),
        controlled_spring_problem(),
        controlled_discrete_decay_problem(),
    )


def inspection_artifact_index(
    records: Sequence[tuple[VerificationProblem, InspectionAdapterReport]],
) -> dict[str, object]:
    """Return a deterministic discovery index for inspection artifacts."""

    return {
        "schemaVersion": INSPECTION_ARTIFACT_INDEX_SCHEMA_VERSION,
        "problems": [
            {
                "id": problem.id,
                "name": problem.name,
                "schemaVersion": problem.schema_version,
                "artifacts": [artifact.to_dict() for artifact in report.artifacts],
            }
            for problem, report in records
        ],
    }


def write_inspection_artifact_index(
    records: Sequence[tuple[VerificationProblem, InspectionAdapterReport]],
    directory: str | Path,
) -> Path:
    """Write the backend-only discovery index for inspection artifacts."""

    output_dir = Path(directory)
    output_dir.mkdir(parents=True, exist_ok=True)
    index_path = output_dir / INSPECTION_ARTIFACT_INDEX_FILENAME
    index_path.write_text(
        json.dumps(inspection_artifact_index(records), indent=2),
        encoding="utf-8",
    )
    return index_path


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        default=DEFAULT_OUTPUT_DIR,
        help="directory for inspection artifacts",
    )
    return parser.parse_args(argv)


def export_inspection_artifacts(
    output_dir: str | Path,
) -> tuple[list[tuple[VerificationProblem, InspectionAdapterReport]], Path]:
    """Write every inspection problem artifact and the discovery index."""

    records: list[tuple[VerificationProblem, InspectionAdapterReport]] = []
    for problem in inspection_artifact_problems():
        report = write_inspection_artifacts(problem, output_dir)
        records.append((problem, report))
    index_path = write_inspection_artifact_index(records, output_dir)
    return records, index_path


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)

    records, index_path = export_inspection_artifacts(args.output_dir)
    for _problem, report in records:
        for artifact in report.artifacts:
            print(f"wrote {artifact.kind}: {artifact.path}")
        print(report.note)
    print(f"wrote inspection artifact index: {index_path}")


if __name__ == "__main__":
    main()
