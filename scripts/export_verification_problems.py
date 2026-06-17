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
from engine.export import (
    PackageManifest,
    write_package,
    write_package_index,
    write_package_summary,
)
from engine.numerics import Interval, integrate_fixed_step
from engine.verification import (
    AssumptionSpec,
    CandidateSpec,
    EnclosureStatusSpec,
    InspectionAdapterReport,
    VerificationProblem,
    certificate_series_for_trajectory,
    certified_enclosure_status,
    expression_spec,
    scalar_field_region_geometries,
    sampled_region_proof_statuses,
    trajectory_obligation_proof_status,
    verification_problem_from_barrier,
    verification_problem_from_controlled_discrete_lyapunov,
    verification_problem_from_obligations,
    write_inspection_artifacts,
)
from systems.controlled_pendulum import build_system
from systems.controlled_spring import build_system as build_spring_system
from systems.drone_point_mass import (
    DEFAULT_DISTURBANCE,
    DEFAULT_OBSTACLE,
    DRONE_CONTROLS,
    DRONE_STATE,
    DisturbanceSpec,
    DroneParams,
    ObstacleSpec,
    horizontal_axis_closed_loop,
    horizontal_axis_rollout,
    horizontal_axis_system,
    horizontal_disturbed_axis_closed_loop,
    horizontal_plane_disturbed_coasting,
    horizontal_plane_rollout,
    vertical_axis_closed_loop,
    vertical_axis_rollout,
    vertical_axis_system,
    vertical_disturbed_axis_closed_loop,
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
    problem = replace(
        problem,
        proof_statuses=sampled_region_proof_statuses(
            problem, restrict_to_assumption_regions=True
        ),
    )
    return replace(problem, enclosure_statuses=_geofence_certified_statuses(problem, spec))


def _geofence_certified_statuses(
    problem: VerificationProblem, spec: _AxisGeofenceSpec
) -> tuple[EnclosureStatusSpec, ...]:
    """Level-2 certified-numeric statuses for a Tier-1 geofence package.

    The exact-rational interval enclosure closes the geofence barrier's
    initial-containment obligation over the inner-start set ``S_in``: the barrier
    ``B = max(qMin - q, q - qMax)`` is polynomial and Piecewise-free, so the
    enclosure holds with no rounding and certifies ``B <= 0`` on ``S_in``.

    BE-069 adds conservative branch-free boxes for the Tier-1 P2 velocity bound
    and the inner-set one-step obligation. These boxes sit inside the guard-band
    interior, so the recorded box itself fixes the closed-loop map to the coast
    branch. The certified expressions are exact-rational polynomials/Abs/Max on
    that stated box; the guard-band portions of the larger assumption regions
    remain measured-only until the branch-partitioned enclosure handles them.
    """

    r = _drone_rational
    q_min, q_max = spec.pos_bounds
    dt = r(spec.timestep)
    q = spec.position
    v = spec.velocity
    velocity_bound = r(spec.velocity_bound)
    inner_low = r(q_min) + r(spec.lower_band)
    inner_high = r(q_max) - r(spec.upper_band)
    drift_margin = dt * velocity_bound
    obligation_by_name = {ob.name: ob for ob in problem.obligations}

    statuses: list[EnclosureStatusSpec] = []
    containment = obligation_by_name["geofence-barrier:initial-containment"]
    inner_box = {
        q.name: Interval(inner_low, inner_high),
        v.name: Interval(-velocity_bound, velocity_bound),
    }
    status = certified_enclosure_status(
        id="enclosure:geofence-barrier:initial-containment",
        obligation=containment,
        box=inner_box,
        soundness_assumptions=(
            "Exact zero-order-hold sampled-data map with rational DroneParams; "
            "the enclosure is exact-rational with no rounding.",
            "Box is the inner-start set S_in: "
            f"{spec.position.name} in [qMin + dLow, qMax - dHigh], "
            f"|{spec.velocity.name}| <= Bh.",
        ),
    )
    if status is not None:
        statuses.append(status)

    coast_box = {
        q.name: Interval(inner_low + drift_margin, inner_high - drift_margin),
        v.name: Interval(-velocity_bound, velocity_bound),
    }
    velocity_obligation = replace(
        obligation_by_name["velocity-bound:one-step-invariance"],
        expression=expression_spec(sp.Abs(v) - velocity_bound),
    )
    status = certified_enclosure_status(
        id="enclosure:velocity-bound:one-step-invariance:coast-core",
        obligation=velocity_obligation,
        box=coast_box,
        soundness_assumptions=(
            "Exact zero-order-hold sampled-data map with rational DroneParams; "
            "the enclosure is exact-rational with no rounding.",
            "Box lies in the guard-band interior, so the closed-loop guard law "
            "selects the coast branch throughout the stated box.",
            f"Box records the certified P2 core: {q.name} in "
            "[qMin + guard + dt*B, qMax - guard - dt*B], "
            f"|{v.name}| <= B.",
        ),
        note=(
            "Certified-numeric only on the recorded coast-core box; guard-band "
            "branches remain measured/external-required until partitioned."
        ),
    )
    if status is not None:
        statuses.append(status)

    drift = q + dt * v
    inner_obligation = replace(
        obligation_by_name["inner-set:one-step-invariance"],
        expression=expression_spec(
            sp.Max(inner_low - drift, drift - inner_high, sp.Abs(v) - velocity_bound)
        ),
    )
    status = certified_enclosure_status(
        id="enclosure:inner-set:one-step-invariance:coast-core",
        obligation=inner_obligation,
        box=coast_box,
        soundness_assumptions=(
            "Exact zero-order-hold sampled-data map with rational DroneParams; "
            "the enclosure is exact-rational with no rounding.",
            "Box lies in the guard-band interior, so the closed-loop guard law "
            "selects the coast branch throughout the stated box.",
            "Box is tightened by dt*B on each side, so q + dt*v remains inside "
            "the inner interval for every point in the box.",
        ),
        note=(
            "Certified-numeric only on the recorded drift-valid coast-core box; "
            "the larger S_in region remains measured/external-required."
        ),
    )
    if status is not None:
        statuses.append(status)
    return tuple(statuses)


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


# A boundary-approaching axis-1 start (spec L.2 margin scenario): the drone begins
# deep in the upper guard band, coasting outward at the velocity bound, so one
# braking step nearly reaches the geofence wall before stopping -- the tight,
# load-bearing forward-invariance margin.
DRONE_GEOFENCE_MARGIN_INITIAL_STATE: tuple[float, ...] = (0.95, 0.25)


def drone_geofence_margin_trajectory(
    params: DroneParams = DroneParams(),
) -> tuple[np.ndarray, np.ndarray]:
    """The spec L.2 boundary-approaching MARGIN rollout; columns ``(q1, v1)``.

    The drone starts deep in the upper guard band (``q1 = 0.95``) moving outward at
    the velocity bound (``v1 = Bh``); the guard band fires ``-uh`` and one braking
    step nearly reaches the wall ``q1 = q1Max`` before stopping -- staying strictly
    inside the geofence with a small, load-bearing margin, unlike the comfortable
    centered rollout. Discrete-time axis: step ``k`` maps to ``k * dt``.
    """

    result = horizontal_axis_rollout(
        params, initial_state=DRONE_GEOFENCE_MARGIN_INITIAL_STATE
    )
    time = result.steps.astype(float) * params.timestep
    return time, result.states


def drone_geofence_margin_problem(
    params: DroneParams = DroneParams(),
) -> VerificationProblem:
    """Tier-1 geofence boundary-approaching MARGIN reference scenario (spec L.2).

    The same decoupled ``(q1, v1)`` geofence problem as
    :func:`drone_geofence_problem`, but carrying the measured *tight margin* the
    spec's boundary-approaching scenario produces. A drone that begins deep in the
    upper guard band moving outward at the velocity bound brakes to a near-wall
    stop, so the forward-invariance barrier's measured slack is small but
    nonnegative -- the closest the rollout's successor comes to the geofence wall.

    The base region-grid statuses are unchanged (each one-step claim still
    measured-holds within its assumption region); an added trajectory-sampled
    status reports the tight forward-invariance margin along this rollout, with its
    closest-approach point. Measured evidence only -- a tight hold witnesses how
    close *this* rollout came to the boundary; it is never a discharge. Renders on
    the ``(q1, v1)`` phase plane.
    """

    problem = drone_geofence_problem(params)
    time, states = drone_geofence_margin_trajectory(params)
    margin_status = trajectory_obligation_proof_status(
        problem,
        "geofence-barrier-forward-invariance",
        time,
        states,
        state_names=("q1", "v1"),
        variable_to_state_axis=_DRONE_PHASE_AXES,
        source="trajectory:boundary-approaching-margin",
    )
    return replace(
        problem,
        id="drone-geofence-margin",
        name="drone geofence margin",
        proof_statuses=problem.proof_statuses + (margin_status,),
        metadata={"verificationModel": "drone-geofence-margin"},
    )


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
    # Circular analogue of the Tier-2 obstacle braking band `b`: one per-axis
    # velocity-cap drift step. This is separate from the larger standoff radius
    # used as the measured operating annulus.
    obstacle_band = dt * r(params.horizontal_velocity_bound)

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
    inner_clearance = min(
        float(r(cx) - (r(q1_min) + band)),
        float((r(q1_max) - band) - r(cx)),
        float(r(cy) - (r(q2_min) + band)),
        float((r(q2_max) - band) - r(cy)),
    )
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
    obstacle_valid_dilation = AssumptionSpec(
        id="obstacle-valid-dilated-obstacle-inside-inner-set",
        name="Obstacle.Valid: dilated obstacle lies inside the inner set",
        role="parameter-domain",
        expression=expression_spec(rho + obstacle_band),
        comparison="<=",
        rhs=inner_clearance,
        variables=(),
        description=(
            "rho + b <= dist(c, boundary(S_in)): the circular obstacle dilated by "
            "the obstacle braking band b lies inside the horizontal geofence inner "
            "set, so obstacle avoidance does not interfere with the geofence guard "
            "bands (Obstacle.Valid clause 1)."
        ),
    )
    obstacle_valid_separation = AssumptionSpec(
        id="obstacle-valid-band-separates-opposite-faces",
        name="Obstacle.Valid: obstacle band separates opposite faces",
        role="parameter-domain",
        expression=expression_spec(2 * obstacle_band),
        comparison="<",
        rhs=float(2 * rho),
        variables=(),
        description=(
            "2*b < 2*rho: the circular analogue of the strict obstacle-band "
            "separation condition, keeping the avoidance controller single-valued "
            "(Obstacle.Valid clause 2)."
        ),
    )
    obstacle_valid_braking = AssumptionSpec(
        id="obstacle-valid-braking-band-dominates-one-step-drift",
        name="Obstacle.Valid: obstacle band dominates one-step drift",
        role="parameter-domain",
        expression=expression_spec(dt * r(params.horizontal_velocity_bound)),
        comparison="<=",
        rhs=float(obstacle_band),
        variables=(),
        description=(
            "dt*Bh <= b: the obstacle braking band dominates one per-axis drift step "
            "at the velocity cap, the braking-margin precondition used by P4 "
            "(Obstacle.Valid clause 3)."
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
        assumptions=(
            speed_bound,
            maintains_standoff,
            interior,
            obstacle_valid_dilation,
            obstacle_valid_separation,
            obstacle_valid_braking,
            standoff_margin,
        ),
        obligation_assumptions={
            "obstacle-keepout:one-step-avoidance": (
                "planar-speed-within-velocity-bound",
                "drone-maintains-obstacle-standoff",
                "operating-region-within-guard-band-interior",
                "obstacle-valid-dilated-obstacle-inside-inner-set",
                "obstacle-valid-band-separates-opposite-faces",
                "obstacle-valid-braking-band-dominates-one-step-drift",
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


def drone_obstacle_keepout_violation_trajectory(
    params: DroneParams = DroneParams(),
    obstacle: ObstacleSpec = DEFAULT_OBSTACLE,
) -> tuple[np.ndarray, np.ndarray]:
    """The spec L.2 diagonal-corner VIOLATION rollout; columns ``(q1, q2)``.

    The drone starts at the corner ``q = (9/16, 9/16)`` with inward velocity
    ``v = (-Bh, -Bh)`` (spec scaled ``(-8, -8)``) and coasts straight at the
    centered obstacle under the keep-out problem's own interior dynamics
    ``q+ = q + dt v`` -- it never maintains the standoff, so it enters the keep-out
    region. ``N = 8``, ``dt`` from ``params``. Discrete-time axis: step ``k`` maps
    to ``k * dt``.
    """

    dt = params.timestep
    vel = params.horizontal_velocity_bound
    q0 = np.array([9.0 / 16.0, 9.0 / 16.0])
    velocity = np.array([-vel, -vel])
    steps = np.arange(9)
    states = q0[None, :] + steps[:, None] * dt * velocity[None, :]
    time = steps.astype(float) * dt
    return time, states


def drone_obstacle_keepout_violation_problem(
    params: DroneParams = DroneParams(),
    obstacle: ObstacleSpec = DEFAULT_OBSTACLE,
) -> VerificationProblem:
    """Tier-2 keep-out VIOLATION reference scenario (spec L.2 diagonal corner).

    The same coupled ``(q1, q2)`` keep-out problem as
    :func:`drone_obstacle_keepout_problem`, but carrying the measured *violation*
    the spec's load-bearing diagonal-corner scenario produces. A drone that does
    not maintain the standoff -- starting at ``q = (9/16, 9/16)`` with inward
    velocity ``v = (-Bh, -Bh)`` -- coasts straight into the centered obstacle.

    The avoidance obligation's region-grid status still measured-holds within the
    standoff annulus (the candidate's claim is conditional on the standoff
    assumption), and an added trajectory-sampled status reports the measured
    violation along this rollout, with the obstacle entry time located by the event
    root-finder (sharp, not snapped to the ``dt`` grid). This is the rigor-ladder
    lesson of spec L.2: the standoff/dilation margin is load-bearing, not vacuous.
    Measured evidence only -- a located violation witnesses that *this* rollout
    left the set; it does not disprove the candidate. Renders on the ``(q1, q2)``
    plane.
    """

    problem = drone_obstacle_keepout_problem(params, obstacle)
    time, states = drone_obstacle_keepout_violation_trajectory(params, obstacle)

    # Locate the obstacle entry by event root-finding on the interior coasting
    # segment (constant velocity between samples), so the entry time is sharp to
    # integration tolerance rather than snapped to the dt grid.
    q1, q2 = DRONE_STATE[0], DRONE_STATE[1]
    r = _drone_rational
    cx, cy = obstacle.center
    dist = sp.sqrt((q1 - r(cx)) ** 2 + (q2 - r(cy)) ** 2)
    obstacle_interior = SublevelSet(
        state=(q1, q2),
        expression=dist - r(obstacle.radius),
        level=0.0,
        name="obstacle-interior",
    )
    keepout_safe = SublevelSet(
        state=(q1, q2),
        expression=r(obstacle.radius) - dist,
        level=0.0,
        name="obstacle-exterior",
    )
    spec = SafetySpecification(
        state=(q1, q2), safe_set=keepout_safe, unsafe_sets=(obstacle_interior,)
    )
    vel = float(params.horizontal_velocity_bound)
    velocity = np.array([-vel, -vel])

    def coasting_rhs(_t: float, _y: Sequence[float]) -> np.ndarray:
        return velocity

    entry = spec.event_entry_report(
        coasting_rhs,
        [float(states[0, 0]), float(states[0, 1])],
        (float(time[0]), float(time[-1])),
    ).unsafe_sets[0]

    violation_status = trajectory_obligation_proof_status(
        problem,
        "obstacle-keepout-one-step-avoidance",
        time,
        states,
        state_names=("q1", "q2"),
        variable_to_state_axis=_DRONE_PLANE_PHASE_AXES,
        source="trajectory:diagonal-corner-violation",
        entry_time=entry.first_entry_time,
    )
    return replace(
        problem,
        id="drone-obstacle-keepout-violation",
        name="drone obstacle keepout violation",
        proof_statuses=problem.proof_statuses + (violation_status,),
        metadata={"verificationModel": "drone-obstacle-keepout-violation"},
    )


def drone_geofence_obstacle_problem(
    params: DroneParams = DroneParams(),
    obstacle: ObstacleSpec = DEFAULT_OBSTACLE,
) -> VerificationProblem:
    """Coupled geofence + obstacle keep-out problem on the ``(q1, q2)`` plane.

    The first problem whose safe set is an *intersection* of two candidate
    regions: the drone must stay both **inside** the geofence box and **outside**
    the obstacle under the same guard-band law. It reuses the BE-048 coasting
    kinematics (in the geofence interior the guard band commands zero thrust, so
    one closed-loop step is the drift ``q+ = q + dt v`` with the planar velocity
    ``(v1, v2)`` a bounded parameter) and assumptions, carrying two barrier
    candidates together:

    - the geofence box barrier ``B_geo = max(q1Min-q1, q1-q1Max, q2Min-q2,
      q2-q2Max)`` with a worst-case one-step forward-invariance obligation
      ``B_geo + dt*Vmax <= 0`` (one coasting step keeps the drone in the box),
    - the keep-out barrier ``B_obs = rho - |q - c|`` with the BE-048 worst-case
      one-step avoidance obligation.

    The safe set is the intersection ``{max(B_geo, B_obs) <= 0}``. Each barrier
    holds within its assumption region: the geofence claim within the inner
    interval, the keep-out claim within the standoff annulus, both in the
    guard-band interior. Every obligation is ``external-required`` and both
    barriers are candidates only. Renders on the ``(q1, q2)`` plane.
    """

    q1, q2 = DRONE_STATE[0], DRONE_STATE[1]
    v1, v2 = DRONE_STATE[3], DRONE_STATE[4]
    r = _drone_rational
    dt = r(params.timestep)
    cx, cy = obstacle.center
    rho = r(obstacle.radius)
    standoff = r(obstacle.standoff_radius)
    q1_min, q1_max = params.q1_bounds
    q2_min, q2_max = params.q2_bounds
    band = r(params.horizontal_band)
    # Worst-case planar speed for per-axis |vi| <= Bh, and the displacement one
    # coasting step of that speed can produce (shared by both barriers, since the
    # per-axis drift |dt*vi| <= dt*|v| <= dt*Vmax).
    speed_max = sp.sqrt(2) * r(params.horizontal_velocity_bound)
    drift = dt * speed_max

    geofence_expression = sp.Max(
        r(q1_min) - q1, q1 - r(q1_max), r(q2_min) - q2, q2 - r(q2_max)
    )
    dist = sp.sqrt((q1 - r(cx)) ** 2 + (q2 - r(cy)) ** 2)
    keepout_expression = rho - dist
    standoff_expression = standoff - dist
    inner_interval_expression = sp.Max(
        r(q1_min) + band - q1,
        q1 - (r(q1_max) - band),
        r(q2_min) + band - q2,
        q2 - (r(q2_max) - band),
    )

    geofence_set = SublevelSet(
        state=(q1, q2), expression=geofence_expression, level=0.0, name="geofence-box"
    )
    keepout_set = SublevelSet(
        state=(q1, q2), expression=keepout_expression, level=0.0, name="keep-out"
    )
    # The combined safe set is the intersection of the two candidate regions:
    # inside the geofence box AND outside the obstacle.
    combined_safe_expression = sp.Max(geofence_expression, keepout_expression)
    combined_safe_set = SublevelSet(
        state=(q1, q2),
        expression=combined_safe_expression,
        level=0.0,
        name="geofence-and-keepout",
    )
    # The initial set lies in the geofence inner interval AND outside the standoff
    # annulus, so both barriers start nonpositive.
    initial_expression = sp.Max(inner_interval_expression, standoff_expression)
    initial_set = SublevelSet(
        state=(q1, q2),
        expression=initial_expression,
        level=0.0,
        name="inner-and-standoff",
    )
    specification = SafetySpecification(
        state=(q1, q2), safe_set=combined_safe_set, initial_set=initial_set
    )

    geofence_invariance = ProofObligation(
        name="geofence-box:one-step-forward-invariance",
        state=(q1, q2),
        expression=geofence_expression + drift,
        comparison="<=",
        region=geofence_set,
        description=(
            "B_geo + dt*Vmax <= 0 on {B_geo <= 0}: the worst-case one-step coasting "
            "drift keeps the drone inside the geofence box (Tier-1 P1 on the plane)."
        ),
    )
    geofence_containment = ProofObligation(
        name="geofence-box:initial-containment",
        state=(q1, q2),
        expression=geofence_expression,
        comparison="<=",
        region=initial_set,
        description=(
            "B_geo <= 0 on the initial set: the operating region lies inside the "
            "geofence box."
        ),
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
    keepout_containment = ProofObligation(
        name="obstacle-keepout:initial-containment",
        state=(q1, q2),
        expression=keepout_expression,
        comparison="<=",
        region=initial_set,
        description=(
            "B_obs <= 0 on the initial set: the operating region lies outside the "
            "obstacle."
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
    interior = AssumptionSpec(
        id="operating-region-within-guard-band-interior",
        name="operating region lies in the guard-band interior",
        role="domain",
        expression=expression_spec(inner_interval_expression),
        comparison="<=",
        rhs=0.0,
        variables=("q1", "q2"),
        description=(
            "q in [qMin+dh, qMax-dh]^2: the operating region lies in the geofence "
            "inner interval, where the guard band commands zero thrust so the "
            "closed-loop step is the pure coasting drift and one step stays inside "
            "the geofence box."
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
    geofence_margin = AssumptionSpec(
        id="guard-band-exceeds-worst-case-drift",
        name="guard band leaves room for one worst-case drift step",
        role="parameter-domain",
        expression=expression_spec(drift),
        comparison="<=",
        rhs=float(band),
        variables=(),
        description=(
            "dt*Vmax <= dh: the inner-interval guard band exceeds one worst-case "
            "coasting step (precondition of one-step geofence forward invariance)."
        ),
    )

    problem = verification_problem_from_obligations(
        "drone geofence obstacle",
        (geofence_invariance, geofence_containment, avoidance, keepout_containment),
        system=dynamics,
        specification=specification,
        assumptions=(
            speed_bound,
            maintains_standoff,
            interior,
            standoff_margin,
            geofence_margin,
        ),
        obligation_assumptions={
            "geofence-box:one-step-forward-invariance": (
                "planar-speed-within-velocity-bound",
                "operating-region-within-guard-band-interior",
                "guard-band-exceeds-worst-case-drift",
            ),
            "geofence-box:initial-containment": (),
            "obstacle-keepout:one-step-avoidance": (
                "planar-speed-within-velocity-bound",
                "drone-maintains-obstacle-standoff",
                "operating-region-within-guard-band-interior",
                "standoff-exceeds-worst-case-drift",
            ),
            "obstacle-keepout:initial-containment": (),
        },
        metadata={"verificationModel": "drone-geofence-obstacle"},
    )

    region_id_by_name = {region.name: region.id for region in problem.regions}
    obligation_id_by_name = {
        obligation.name: obligation.id for obligation in problem.obligations
    }
    candidates = (
        CandidateSpec(
            id="geofence-box-barrier",
            name="geofence-box-barrier",
            kind="barrier",
            expression=expression_spec(geofence_expression),
            obligation_ids=(
                obligation_id_by_name["geofence-box:one-step-forward-invariance"],
                obligation_id_by_name["geofence-box:initial-containment"],
            ),
            region_id=region_id_by_name["geofence-box"],
        ),
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
    # Each one-step claim holds only within its assumption region (the geofence
    # claim in the inner interval, the keep-out claim in the standoff annulus);
    # sample within that region (the velocity bound is external-required).
    return replace(
        problem,
        proof_statuses=sampled_region_proof_statuses(
            problem, restrict_to_assumption_regions=True
        ),
    )


def drone_geofence_obstacle_trajectory(
    params: DroneParams = DroneParams(),
) -> tuple[np.ndarray, np.ndarray]:
    """Integrate the coupled plane guard-band loop; columns ``(q1, q2)``.

    The drone coasts in +q1 above the centered obstacle, staying both inside the
    geofence box and outside the keep-out region throughout (the same BE-048
    rollout). Discrete-time axis: step ``k`` maps to ``k * dt``.
    """

    result = horizontal_plane_rollout(params)
    time = result.steps.astype(float) * params.timestep
    return time, result.states[:, :2]


def drone_disturbed_geofence_problem(
    params: DroneParams = DroneParams(),
    disturbance: DisturbanceSpec = DEFAULT_DISTURBANCE,
) -> VerificationProblem:
    """Tier-3 disturbance-robust geofence problem on the ``(q1, v1)`` axis.

    The first worst-case problem (spec App. ``app:tier3``): the horizontal
    zero-order-hold step gains a bounded additive disturbance ``w1 in W = [-w,
    w]`` matched to the control, making the closed loop set-valued (one successor
    per admissible ``w1``). The robust forward-invariance obligation must hold for
    *every* admissible ``w1``, not just the nominal path.

    The worst case over ``W`` is exact and baked into the obligation analytically:
    one disturbed step displaces the position by at most ``dt^2/2 * w`` toward
    either wall, so ``max_w B(F(x, g(x), w)) = B(F_nom(x)) + dt^2/2 * w``. The
    obligation samples that worst-case barrier value within the geofence inner
    interval (the spec-G ``driftBound`` region, where the guard band commands zero
    thrust so one disturbed coasting step stays inside the geofence) and the
    robust speed bound ``|v1| <= (uh - w) * dt / 2`` (tightened from the nominal
    ``speedBound`` to leave room for the worst-case gust). The disturbance bound
    ``|w1| <= w`` is a non-plane assumption left for external discharge — the
    measured signed margin already reports the worst case across the whole
    disturbance set.

    Every obligation is ``external-required`` and the geofence barrier is a
    candidate only. Renders on the ``(q1, v1)`` plane.
    """

    disturbance.assert_authority(params)
    q, v = DRONE_STATE[0], DRONE_STATE[3]
    w = horizontal_disturbed_axis_closed_loop(params, disturbance).parameters[0]
    closed = horizontal_axis_closed_loop(params)
    r = _drone_rational
    dt = r(params.timestep)
    q_min, q_max = params.q1_bounds
    band = r(params.horizontal_band)
    uh = r(params.horizontal_thrust)
    w_max = r(disturbance.bound)
    # Worst-case one-step position displacement under the disturbance set.
    robust_drift = dt**2 / 2 * w_max
    # Robust speed bound: the nominal half-guard-reach minus the disturbance,
    # so one disturbed corrective step still arrests outward motion at the wall.
    robust_speed_cap = (uh - w_max) * dt / 2

    barrier_expression = sp.Max(r(q_min) - q, q - r(q_max))
    barrier = BarrierCandidate(
        state=(q, v), function=barrier_expression, name="geofence-barrier"
    )
    safe_set = SublevelSet(
        state=(q, v), expression=barrier_expression, level=0.0, name="geofence"
    )
    inner_start_expression = sp.Max(
        r(q_min) + band - q,
        q - (r(q_max) - band),
        sp.Abs(v) - robust_speed_cap,
    )
    inner_start_set = SublevelSet(
        state=(q, v), expression=inner_start_expression, level=0.0, name="inner-start"
    )
    specification = SafetySpecification(
        state=(q, v), safe_set=safe_set, initial_set=inner_start_set
    )

    nominal_next = {q: closed.update[0], v: closed.update[1]}
    robust_forward_invariance = ProofObligation(
        name="geofence-barrier:robust-forward-invariance",
        state=(q, v),
        expression=barrier_expression.subs(nominal_next, simultaneous=True) + robust_drift,
        comparison="<=",
        region=safe_set,
        description=(
            "max_w B(F(x, g(x), w)) = B(F_nom(x)) + dt^2/2*w <= 0 on {B <= 0}: one "
            "guard-band step keeps the drone inside the geofence for every admissible "
            "disturbance w in W = [-w, w] (Tier-3 robust P1)."
        ),
    )
    initial_containment = ProofObligation(
        name="geofence-barrier:initial-containment",
        state=(q, v),
        expression=barrier_expression,
        comparison="<=",
        region=inner_start_set,
        description="B <= 0 on the inner start set: the initial set lies inside the geofence.",
    )

    # Robust self-reproducing velocity bound (Tier-3 P2). One disturbed step adds
    # at most dt*w to the velocity, so the per-axis bound enlarges from the nominal
    # Bh = uh*dt to the robust Bh(3) = (uh + w)*dt. The obligation asserts that the
    # worst-case disturbed successor of the *nominal*-velocity-bounded set lands
    # within Bh(3): max_w |v1+| = |v1_nom+| + dt*w <= (uh + w)*dt, equivalently
    # |v1_nom+| <= uh*dt. The bound is not self-reproducing from Bh(3) itself -- a
    # coasting interior step under persistent wind grows the speed by dt*w each
    # step -- so the robust claim is asserted from the nominal bound, exactly as the
    # spec's P2 precondition leans on authority. The +dt*w enlargement is exactly
    # consumed by the worst-case gust, so the margin is tight (zero) at |v1| = uh*dt.
    nominal_velocity_bound = uh * dt
    robust_velocity_bound = (uh + w_max) * dt
    robust_velocity_drift = dt * w_max
    robust_velocity_barrier = sp.Abs(v) - robust_velocity_bound
    robust_velocity_bound_set = SublevelSet(
        state=(q, v),
        expression=robust_velocity_barrier,
        level=0.0,
        name="robust-velocity-bound",
    )
    robust_velocity_invariance = ProofObligation(
        name="robust-velocity-bound:one-step-invariance",
        state=(q, v),
        expression=robust_velocity_barrier.subs(nominal_next, simultaneous=True)
        + robust_velocity_drift,
        comparison="<=",
        region=robust_velocity_bound_set,
        description=(
            "max_w |v1+| = |v1_nom+| + dt*w <= (uh + w)*dt on {|v1| <= uh*dt}: the "
            "per-axis velocity bound enlarges to the robust Bh(3) = (uh + w)*dt, and "
            "the worst-case disturbed successor of the nominal velocity-bounded set "
            "stays within it for every admissible w in W = [-w, w] (Tier-3 robust "
            "P2). The +dt*w gust is exactly absorbed by the enlargement."
        ),
    )

    disturbance_bound = AssumptionSpec(
        id="disturbance-within-wind-bound",
        name="additive disturbance within the wind bound",
        role="domain",
        expression=expression_spec(sp.Abs(w)),
        comparison="<=",
        rhs=float(w_max),
        variables=(w.name,),
        description=(
            "|w1| <= w: the additive acceleration disturbance stays within the "
            "per-axis wind box W = [-w, w]; the robust forward-invariance claim is "
            "quantified over every admissible w1 in W (spec Tier-3 disturbance set). "
            "Not plane-expressible in (q1, v1); left for external discharge."
        ),
    )
    robust_speed_bound = AssumptionSpec(
        id="robust-speed-within-tightened-guard-reach",
        name="per-step speed within the disturbance-tightened guard reach",
        role="domain",
        expression=expression_spec(sp.Abs(v)),
        comparison="<=",
        rhs=float(robust_speed_cap),
        variables=(v.name,),
        description=(
            "Speed stays within (uh - w)*dt/2, the nominal half-guard-reach tightened "
            "by the disturbance so one disturbed corrective step arrests outward motion "
            "before the wall (robust analogue of spec G speedBound)."
        ),
    )
    drift_inner_interval = AssumptionSpec(
        id="operating-within-geofence-inner-interval",
        name="operating region stays in the geofence inner interval",
        role="domain",
        expression=expression_spec(
            sp.Max(r(q_min) + band - q, q - (r(q_max) - band))
        ),
        comparison="<=",
        rhs=0.0,
        variables=(q.name,),
        description=(
            "q1Min+dh <= q1 <= q1Max-dh: the robust claim is asserted within the "
            "geofence inner interval (spec G driftBound region), where the guard band "
            "commands zero thrust so one disturbed coasting step stays inside the "
            "geofence."
        ),
    )
    robust_braking = AssumptionSpec(
        id="robust-braking-displacement-fits-guard-band",
        name="one disturbed step's braking displacement fits the guard band",
        role="parameter-domain",
        expression=expression_spec((uh + w_max) * dt**2 / 2),
        comparison="<=",
        rhs=float(band),
        variables=(),
        description=(
            "(uh + w)*dt^2/2 <= dh: one step's worst corrective displacement under the "
            "disturbance fits inside the guard band (robust analogue of spec G dtSmall)."
        ),
    )
    nominal_velocity_bound_assumption = AssumptionSpec(
        id="velocity-within-nominal-self-reproducing-bound",
        name="speed within the nominal self-reproducing velocity bound",
        role="domain",
        expression=expression_spec(sp.Abs(v)),
        comparison="<=",
        rhs=float(nominal_velocity_bound),
        variables=(v.name,),
        description=(
            "|v1| <= Bh = uh*dt: the robust P2 obligation is asserted from the nominal "
            "self-reproducing velocity bound (spec G velBound), the largest set one "
            "disturbed step keeps within the enlarged Bh(3) = (uh + w)*dt. A coasting "
            "interior step under persistent wind grows the speed by dt*w, so the "
            "enlarged bound is not self-reproducing from itself; the nominal bound is "
            "the honest precondition (plane-expressible in (q1, v1))."
        ),
    )

    dynamics = horizontal_disturbed_axis_closed_loop(params, disturbance)
    problem = verification_problem_from_obligations(
        "drone disturbed geofence axis",
        (robust_forward_invariance, initial_containment, robust_velocity_invariance),
        system=dynamics,
        specification=specification,
        assumptions=(
            disturbance_bound,
            robust_speed_bound,
            drift_inner_interval,
            robust_braking,
            nominal_velocity_bound_assumption,
        ),
        obligation_assumptions={
            "geofence-barrier:robust-forward-invariance": (
                "disturbance-within-wind-bound",
                "robust-speed-within-tightened-guard-reach",
                "operating-within-geofence-inner-interval",
                "robust-braking-displacement-fits-guard-band",
            ),
            "geofence-barrier:initial-containment": (),
            "robust-velocity-bound:one-step-invariance": (
                "disturbance-within-wind-bound",
                "velocity-within-nominal-self-reproducing-bound",
            ),
        },
        metadata={"verificationModel": "drone-disturbed-geofence-axis"},
    )

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
                obligation_id_by_name["geofence-barrier:robust-forward-invariance"],
                obligation_id_by_name["geofence-barrier:initial-containment"],
            ),
            region_id=region_id_by_name["geofence"],
        ),
        CandidateSpec(
            id="robust-velocity-bound-barrier",
            name="robust-velocity-bound-barrier",
            kind="barrier",
            expression=expression_spec(robust_velocity_barrier),
            obligation_ids=(
                obligation_id_by_name["robust-velocity-bound:one-step-invariance"],
            ),
            region_id=region_id_by_name["robust-velocity-bound"],
        ),
    )
    problem = replace(problem, candidates=candidates)

    geometry = scalar_field_region_geometries(
        problem.regions,
        projection="phase",
        plane_variables=("q1", "v1"),
        variable_to_state_axis=_DRONE_PHASE_AXES,
        x_range=(-1.1, 1.1),
        y_range=(-0.35, 0.35),
        samples=(81, 81),
    )
    problem = replace(problem, region_geometry=geometry)
    # The robust forward-invariance claim is asserted only within the inner
    # interval and the tightened speed bound; sample within that region (the
    # disturbance bound is non-plane and external-required).
    return replace(
        problem,
        proof_statuses=sampled_region_proof_statuses(
            problem, restrict_to_assumption_regions=True
        ),
    )


def drone_disturbed_geofence_trajectory(
    params: DroneParams = DroneParams(),
) -> tuple[np.ndarray, np.ndarray]:
    """Integrate the nominal (``w1 = 0``) axis-1 guard-band loop; columns ``(q1, v1)``.

    The disturbance-robust obligation quantifies over the whole disturbance set;
    the animated path is one admissible realization — the nominal undisturbed
    rollout — so the viewer shows a representative trajectory the robust claim
    must hold around. Discrete-time axis: step ``k`` maps to ``k * dt``.
    """

    result = horizontal_axis_rollout(params)
    time = result.steps.astype(float) * params.timestep
    return time, result.states


def drone_vertical_disturbed_geofence_problem(
    params: DroneParams = DroneParams(),
    disturbance: DisturbanceSpec = DEFAULT_DISTURBANCE,
) -> VerificationProblem:
    """Tier-3 disturbance-robust altitude problem on the ``(q3, v3)`` axis.

    The vertical analogue of the horizontal BE-049 problem: the asymmetric
    altitude zero-order-hold step (carrying the gravity offset) gains a bounded
    additive disturbance ``w3 in W = [-w, w]`` matched to the control, making the
    closed loop set-valued. The robust floor/ceiling forward-invariance obligation
    must hold for *every* admissible ``w3``.

    The worst case over ``W`` is exact and baked in analytically: one disturbed
    step displaces the altitude by at most ``dt^2/2 * w`` toward either bound, so
    ``max_w B(F(x, g(x), w)) = B(F_nom(x)) + dt^2/2 * w``. The obligation samples
    that worst-case barrier value within the altitude inner interval (the spec-G
    ``driftBound`` region, where the guard band commands hover thrust so one
    disturbed coasting step stays between floor and ceiling) and the robust speed
    bound ``|v3| <= (a - w) * dt / 2``, where ``a = min(u3Max - g, g - u3Min)`` is
    the binding *asymmetric* vertical authority margin (unlike the symmetric
    horizontal reach). The disturbance bound ``|w3| <= w`` is a non-plane
    assumption left for external discharge.

    Every obligation is ``external-required`` and the geofence barrier is a
    candidate only. Renders on the ``(q3, v3)`` plane.
    """

    disturbance.assert_vertical_authority(params)
    q, v = DRONE_STATE[2], DRONE_STATE[5]
    dynamics = vertical_disturbed_axis_closed_loop(params, disturbance)
    w = dynamics.parameters[0]
    closed = vertical_axis_closed_loop(params)
    r = _drone_rational
    dt = r(params.timestep)
    q_min, q_max = params.q3_bounds
    floor = r(params.floor_band)
    ceiling = r(params.ceiling_band)
    reach = r(params.vertical_reach)
    authority = r(DisturbanceSpec.vertical_authority_margin(params))
    w_max = r(disturbance.bound)
    # Worst-case one-step altitude displacement under the disturbance set.
    robust_drift = dt**2 / 2 * w_max
    # Robust speed bound: the binding asymmetric authority margin tightened by the
    # disturbance, so one disturbed corrective step still arrests outward motion.
    robust_speed_cap = (authority - w_max) * dt / 2

    barrier_expression = sp.Max(r(q_min) - q, q - r(q_max))
    barrier = BarrierCandidate(
        state=(q, v), function=barrier_expression, name="geofence-barrier"
    )
    safe_set = SublevelSet(
        state=(q, v), expression=barrier_expression, level=0.0, name="geofence"
    )
    inner_start_expression = sp.Max(
        r(q_min) + floor - q,
        q - (r(q_max) - ceiling),
        sp.Abs(v) - robust_speed_cap,
    )
    inner_start_set = SublevelSet(
        state=(q, v), expression=inner_start_expression, level=0.0, name="inner-start"
    )
    specification = SafetySpecification(
        state=(q, v), safe_set=safe_set, initial_set=inner_start_set
    )

    nominal_next = {q: closed.update[0], v: closed.update[1]}
    robust_forward_invariance = ProofObligation(
        name="geofence-barrier:robust-forward-invariance",
        state=(q, v),
        expression=barrier_expression.subs(nominal_next, simultaneous=True) + robust_drift,
        comparison="<=",
        region=safe_set,
        description=(
            "max_w B(F(x, g(x), w)) = B(F_nom(x)) + dt^2/2*w <= 0 on {B <= 0}: one "
            "guard-band step keeps the drone between the floor and ceiling for every "
            "admissible disturbance w in W = [-w, w] (Tier-3 robust P1)."
        ),
    )
    initial_containment = ProofObligation(
        name="geofence-barrier:initial-containment",
        state=(q, v),
        expression=barrier_expression,
        comparison="<=",
        region=inner_start_set,
        description=(
            "B <= 0 on the inner start set: the initial set lies between the floor "
            "and ceiling."
        ),
    )

    # Robust self-reproducing vertical velocity bound (Tier-3 P2), the vertical
    # mirror of the horizontal BE-053. The nominal bound is B3 = reach*dt with
    # reach = max(u3Max-g, g-u3Min) -- the *larger* asymmetric authority margin --
    # because the interior binds: the hover branch cancels gravity, so a coasting
    # interior step is velocity-preserving, and one disturbed step adds at most
    # dt*w. The bound therefore enlarges to (reach + w)*dt, and the worst-case
    # disturbed successor of the nominal-velocity-bounded set lands within it:
    # max_w |v3+| = |v3_nom+| + dt*w <= (reach + w)*dt, i.e. |v3_nom+| <= reach*dt.
    # (The *binding* margin a = min(u3Max-g, g-u3Min) governs the robust speed
    # precondition above, not this bound; the brakes never overshoot reach*dt.)
    nominal_velocity_bound = reach * dt
    robust_velocity_bound = (reach + w_max) * dt
    robust_velocity_drift = dt * w_max
    robust_velocity_barrier = sp.Abs(v) - robust_velocity_bound
    robust_velocity_bound_set = SublevelSet(
        state=(q, v),
        expression=robust_velocity_barrier,
        level=0.0,
        name="robust-velocity-bound",
    )
    robust_velocity_invariance = ProofObligation(
        name="robust-velocity-bound:one-step-invariance",
        state=(q, v),
        expression=robust_velocity_barrier.subs(nominal_next, simultaneous=True)
        + robust_velocity_drift,
        comparison="<=",
        region=robust_velocity_bound_set,
        description=(
            "max_w |v3+| = |v3_nom+| + dt*w <= (reach + w)*dt on {|v3| <= reach*dt}: "
            "the vertical velocity bound B3 = reach*dt, reach = max(u3Max-g, g-u3Min), "
            "enlarges to the robust (reach + w)*dt, and the worst-case disturbed "
            "successor of the nominal velocity-bounded set stays within it for every "
            "admissible w in W = [-w, w] (Tier-3 robust P2). The +dt*w gust is exactly "
            "absorbed by the enlargement."
        ),
    )

    disturbance_bound = AssumptionSpec(
        id="disturbance-within-wind-bound",
        name="additive disturbance within the wind bound",
        role="domain",
        expression=expression_spec(sp.Abs(w)),
        comparison="<=",
        rhs=float(w_max),
        variables=(w.name,),
        description=(
            "|w3| <= w: the additive acceleration disturbance stays within the "
            "per-axis wind box W = [-w, w]; the robust forward-invariance claim is "
            "quantified over every admissible w3 in W (spec Tier-3 disturbance set). "
            "Not plane-expressible in (q3, v3); left for external discharge."
        ),
    )
    robust_speed_bound = AssumptionSpec(
        id="robust-speed-within-tightened-guard-reach",
        name="per-step vertical speed within the disturbance-tightened authority",
        role="domain",
        expression=expression_spec(sp.Abs(v)),
        comparison="<=",
        rhs=float(robust_speed_cap),
        variables=(v.name,),
        description=(
            "Vertical speed stays within (a - w)*dt/2, where a = min(u3Max-g, "
            "g-u3Min) is the binding asymmetric authority margin tightened by the "
            "disturbance, so one disturbed corrective step arrests outward motion "
            "before the bound (robust analogue of spec G speedBound)."
        ),
    )
    drift_inner_interval = AssumptionSpec(
        id="operating-within-geofence-inner-interval",
        name="operating region stays in the altitude inner interval",
        role="domain",
        expression=expression_spec(
            sp.Max(r(q_min) + floor - q, q - (r(q_max) - ceiling))
        ),
        comparison="<=",
        rhs=0.0,
        variables=(q.name,),
        description=(
            "q3Min+floor <= q3 <= q3Max-ceiling: the robust claim is asserted within "
            "the altitude inner interval (spec G driftBound region), where the guard "
            "band commands hover thrust so one disturbed coasting step stays between "
            "the floor and ceiling."
        ),
    )
    robust_braking = AssumptionSpec(
        id="robust-braking-displacement-fits-guard-band",
        name="one disturbed step's braking displacement fits the guard band",
        role="parameter-domain",
        expression=expression_spec((reach + w_max) * dt**2 / 2),
        comparison="<=",
        rhs=float(min(params.floor_band, params.ceiling_band)),
        variables=(),
        description=(
            "(max(u3Max-g, g-u3Min) + w)*dt^2/2 <= min(floor, ceiling band): one "
            "step's worst corrective displacement under the disturbance fits inside "
            "the guard band (robust analogue of spec G dtSmall)."
        ),
    )
    nominal_velocity_bound_assumption = AssumptionSpec(
        id="velocity-within-nominal-self-reproducing-bound",
        name="vertical speed within the nominal self-reproducing velocity bound",
        role="domain",
        expression=expression_spec(sp.Abs(v)),
        comparison="<=",
        rhs=float(nominal_velocity_bound),
        variables=(v.name,),
        description=(
            "|v3| <= B3 = reach*dt, reach = max(u3Max-g, g-u3Min): the robust P2 "
            "obligation is asserted from the nominal self-reproducing vertical velocity "
            "bound (spec G velBound, asymmetric reach), the largest set one disturbed "
            "step keeps within the enlarged (reach + w)*dt. A coasting interior step "
            "(hover cancels gravity) under persistent wind grows the speed by dt*w, so "
            "the enlarged bound is not self-reproducing from itself; the nominal bound "
            "is the honest precondition (plane-expressible in (q3, v3))."
        ),
    )

    problem = verification_problem_from_obligations(
        "drone disturbed vertical geofence axis",
        (robust_forward_invariance, initial_containment, robust_velocity_invariance),
        system=dynamics,
        specification=specification,
        assumptions=(
            disturbance_bound,
            robust_speed_bound,
            drift_inner_interval,
            robust_braking,
            nominal_velocity_bound_assumption,
        ),
        obligation_assumptions={
            "geofence-barrier:robust-forward-invariance": (
                "disturbance-within-wind-bound",
                "robust-speed-within-tightened-guard-reach",
                "operating-within-geofence-inner-interval",
                "robust-braking-displacement-fits-guard-band",
            ),
            "geofence-barrier:initial-containment": (),
            "robust-velocity-bound:one-step-invariance": (
                "disturbance-within-wind-bound",
                "velocity-within-nominal-self-reproducing-bound",
            ),
        },
        metadata={"verificationModel": "drone-disturbed-vertical-geofence-axis"},
    )

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
                obligation_id_by_name["geofence-barrier:robust-forward-invariance"],
                obligation_id_by_name["geofence-barrier:initial-containment"],
            ),
            region_id=region_id_by_name["geofence"],
        ),
        CandidateSpec(
            id="robust-velocity-bound-barrier",
            name="robust-velocity-bound-barrier",
            kind="barrier",
            expression=expression_spec(robust_velocity_barrier),
            obligation_ids=(
                obligation_id_by_name["robust-velocity-bound:one-step-invariance"],
            ),
            region_id=region_id_by_name["robust-velocity-bound"],
        ),
    )
    problem = replace(problem, candidates=candidates)

    geometry = scalar_field_region_geometries(
        problem.regions,
        projection="phase",
        plane_variables=("q3", "v3"),
        variable_to_state_axis=_DRONE_VERTICAL_PHASE_AXES,
        x_range=(-0.1, 2.1),
        y_range=(-0.35, 0.35),
        samples=(81, 81),
    )
    problem = replace(problem, region_geometry=geometry)
    # The robust forward-invariance claim is asserted only within the inner
    # interval and the tightened speed bound; sample within that region (the
    # disturbance bound is non-plane and external-required).
    return replace(
        problem,
        proof_statuses=sampled_region_proof_statuses(
            problem, restrict_to_assumption_regions=True
        ),
    )


def drone_vertical_disturbed_geofence_trajectory(
    params: DroneParams = DroneParams(),
) -> tuple[np.ndarray, np.ndarray]:
    """Integrate the nominal (``w3 = 0``) axis-3 guard-band loop; columns ``(q3, v3)``.

    The animated path is one admissible realization — the nominal undisturbed
    rollout — that the robust altitude claim must hold around. Discrete-time
    axis: step ``k`` maps to ``k * dt``.
    """

    result = vertical_axis_rollout(params)
    time = result.steps.astype(float) * params.timestep
    return time, result.states


def drone_disturbed_obstacle_keepout_problem(
    params: DroneParams = DroneParams(),
    obstacle: ObstacleSpec = DEFAULT_OBSTACLE,
    disturbance: DisturbanceSpec = DEFAULT_DISTURBANCE,
) -> VerificationProblem:
    """Tier-3 disturbance-robust obstacle keep-out on the ``(q1, q2)`` plane.

    Combines the BE-048 obstacle keep-out with the BE-049 disturbance regime: in
    the geofence interior the guard band commands zero thrust, so one coupled step
    is the disturbed coasting drift ``q+ = q + dt v + dt^2/2 w`` with the planar
    velocity ``(v1, v2)`` and disturbance ``(w1, w2)`` bounded parameters of the
    set-valued map. The keep-out avoidance obligation is *robust*: it must hold for
    every admissible velocity (``|v| <= Vmax = sqrt(2)*Bh``) and disturbance
    (``|w| <= sqrt(2)*w``).

    The worst-case displacement of one step is ``dt*Vmax + dt^2/2*sqrt(2)*w``, so
    ``max_{v,w} B_obs(q+) = rho - |q - c| + dt*Vmax + dt^2/2*sqrt(2)*w`` — both
    worst cases baked in analytically, leaving the obligation expression in
    ``(q1, q2)`` alone. It samples that within the standoff annulus and the
    geofence interior; the velocity and disturbance bounds are non-plane
    assumptions left for external discharge. Every obligation is
    ``external-required`` and the keep-out barrier is a candidate only. Renders on
    the ``(q1, q2)`` plane.
    """

    disturbance.assert_authority(params)
    q1, q2 = DRONE_STATE[0], DRONE_STATE[1]
    dynamics = horizontal_plane_disturbed_coasting(params, disturbance)
    v1, v2, w1, w2 = dynamics.parameters
    r = _drone_rational
    dt = r(params.timestep)
    cx, cy = obstacle.center
    rho = r(obstacle.radius)
    standoff = r(obstacle.standoff_radius)
    # Worst-case planar speed and disturbance, and the total displacement one
    # disturbed coasting step of those can produce.
    speed_max = sp.sqrt(2) * r(params.horizontal_velocity_bound)
    disturbance_max = sp.sqrt(2) * r(disturbance.bound)
    drift = dt * speed_max + dt**2 / 2 * disturbance_max

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
        name="obstacle-keepout:robust-one-step-avoidance",
        state=(q1, q2),
        expression=keepout_expression + drift,
        comparison="<=",
        region=keepout_set,
        description=(
            "rho - |q - c| + dt*Vmax + dt^2/2*sqrt(2)*w <= 0 on {B_obs <= 0}: the "
            "worst-case one-step disturbed coasting drift keeps the drone outside the "
            "obstacle for every admissible velocity and disturbance (Tier-3 robust P4)."
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
    disturbance_bound = AssumptionSpec(
        id="planar-disturbance-within-wind-bound",
        name="planar disturbance within the wind bound",
        role="domain",
        expression=expression_spec(sp.sqrt(w1**2 + w2**2)),
        comparison="<=",
        rhs=float(disturbance_max),
        variables=("w1", "w2"),
        description=(
            "|w| <= sqrt(2)*w: the matched additive disturbance stays within the "
            "planar wind box W = [-w, w]^2; the robust avoidance claim is quantified "
            "over every admissible (w1, w2) in W (spec Tier-3 disturbance set). Not "
            "plane-expressible in (q1, q2); left for external discharge."
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
            "closed-loop step is the pure disturbed coasting drift."
        ),
    )
    standoff_margin = AssumptionSpec(
        id="standoff-exceeds-worst-case-drift",
        name="standoff radius leaves room for one worst-case disturbed drift step",
        role="parameter-domain",
        expression=expression_spec(rho + drift),
        comparison="<=",
        rhs=float(standoff),
        variables=(),
        description=(
            "rho + dt*Vmax + dt^2/2*sqrt(2)*w <= R: the standoff radius exceeds the "
            "obstacle radius by more than one worst-case disturbed coasting step "
            "(precondition of robust one-step avoidance)."
        ),
    )

    problem = verification_problem_from_obligations(
        "drone disturbed obstacle keepout",
        (avoidance, initial_containment),
        system=dynamics,
        specification=specification,
        assumptions=(
            speed_bound,
            disturbance_bound,
            maintains_standoff,
            interior,
            standoff_margin,
        ),
        obligation_assumptions={
            "obstacle-keepout:robust-one-step-avoidance": (
                "planar-speed-within-velocity-bound",
                "planar-disturbance-within-wind-bound",
                "drone-maintains-obstacle-standoff",
                "operating-region-within-guard-band-interior",
                "standoff-exceeds-worst-case-drift",
            ),
            "obstacle-keepout:initial-containment": (),
        },
        metadata={"verificationModel": "drone-disturbed-obstacle-keepout"},
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
                obligation_id_by_name["obstacle-keepout:robust-one-step-avoidance"],
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
    # The robust avoidance claim holds only where the standoff and interior
    # assumptions hold; sample within that region (the velocity and disturbance
    # bounds are external-required).
    return replace(
        problem,
        proof_statuses=sampled_region_proof_statuses(
            problem, restrict_to_assumption_regions=True
        ),
    )


def drone_disturbed_obstacle_keepout_trajectory(
    params: DroneParams = DroneParams(),
) -> tuple[np.ndarray, np.ndarray]:
    """Integrate the nominal coupled-plane guard-band loop; columns ``(q1, q2)``.

    The animated path is one admissible realization — the nominal undisturbed
    rollout (the BE-048 pass above the obstacle) — that the robust keep-out claim
    must hold around. Discrete-time axis: step ``k`` maps to ``k * dt``.
    """

    result = horizontal_plane_rollout(params)
    time = result.steps.astype(float) * params.timestep
    return time, result.states[:, :2]


def drone_disturbed_geofence_obstacle_problem(
    params: DroneParams = DroneParams(),
    obstacle: ObstacleSpec = DEFAULT_OBSTACLE,
    disturbance: DisturbanceSpec = DEFAULT_DISTURBANCE,
) -> VerificationProblem:
    """Tier-3 disturbance-robust geofence + obstacle keep-out on the ``(q1, q2)`` plane.

    The capstone of the nominal/robust x single/intersection matrix: it combines
    the BE-050 geofence-and-obstacle intersection with the BE-049/052 disturbance
    regime. In the geofence interior the guard band commands zero thrust, so one
    coupled step is the disturbed coasting drift ``q+ = q + dt v + dt^2/2 w`` with
    the planar velocity ``(v1, v2)`` and disturbance ``(w1, w2)`` bounded
    parameters of the set-valued map. The drone must stay both **inside** the
    geofence box and **outside** the obstacle for *every* admissible velocity
    (``|v| <= Vmax = sqrt(2)*Bh``) and disturbance (``|w| <= sqrt(2)*w``).

    The worst-case displacement of one step is ``dt*Vmax + dt^2/2*sqrt(2)*w``, baked
    analytically into both robust obligations so each expression stays in
    ``(q1, q2)`` alone:

    - geofence box barrier ``B_geo = max(q1Min-q1, q1-q1Max, q2Min-q2, q2-q2Max)``
      with the robust forward-invariance obligation ``B_geo + dt*Vmax +
      dt^2/2*sqrt(2)*w <= 0`` (one disturbed coasting step keeps the drone in the box),
    - keep-out barrier ``B_obs = rho - |q - c|`` with the robust avoidance obligation
      ``B_obs + dt*Vmax + dt^2/2*sqrt(2)*w <= 0`` (BE-052 worst-case one-step keep-out).

    The safe set is the intersection ``{max(B_geo, B_obs) <= 0}``. Each barrier
    holds within its assumption region (the geofence claim within the inner
    interval, the keep-out claim within the standoff annulus, both in the
    guard-band interior); the velocity and disturbance bounds are non-plane
    assumptions left for external discharge. Every obligation is
    ``external-required`` and both barriers are candidates only. Renders on the
    ``(q1, q2)`` plane.
    """

    disturbance.assert_authority(params)
    q1, q2 = DRONE_STATE[0], DRONE_STATE[1]
    dynamics = horizontal_plane_disturbed_coasting(params, disturbance)
    v1, v2, w1, w2 = dynamics.parameters
    r = _drone_rational
    dt = r(params.timestep)
    cx, cy = obstacle.center
    rho = r(obstacle.radius)
    standoff = r(obstacle.standoff_radius)
    q1_min, q1_max = params.q1_bounds
    q2_min, q2_max = params.q2_bounds
    band = r(params.horizontal_band)
    # Worst-case planar speed and disturbance, and the total displacement one
    # disturbed coasting step of those can produce (shared by both barriers, since
    # the per-axis drift |dt*vi + dt^2/2*wi| <= dt*Vmax + dt^2/2*sqrt(2)*w).
    speed_max = sp.sqrt(2) * r(params.horizontal_velocity_bound)
    disturbance_max = sp.sqrt(2) * r(disturbance.bound)
    drift = dt * speed_max + dt**2 / 2 * disturbance_max

    geofence_expression = sp.Max(
        r(q1_min) - q1, q1 - r(q1_max), r(q2_min) - q2, q2 - r(q2_max)
    )
    dist = sp.sqrt((q1 - r(cx)) ** 2 + (q2 - r(cy)) ** 2)
    keepout_expression = rho - dist
    standoff_expression = standoff - dist
    inner_interval_expression = sp.Max(
        r(q1_min) + band - q1,
        q1 - (r(q1_max) - band),
        r(q2_min) + band - q2,
        q2 - (r(q2_max) - band),
    )

    geofence_set = SublevelSet(
        state=(q1, q2), expression=geofence_expression, level=0.0, name="geofence-box"
    )
    keepout_set = SublevelSet(
        state=(q1, q2), expression=keepout_expression, level=0.0, name="keep-out"
    )
    combined_safe_expression = sp.Max(geofence_expression, keepout_expression)
    combined_safe_set = SublevelSet(
        state=(q1, q2),
        expression=combined_safe_expression,
        level=0.0,
        name="geofence-and-keepout",
    )
    initial_expression = sp.Max(inner_interval_expression, standoff_expression)
    initial_set = SublevelSet(
        state=(q1, q2),
        expression=initial_expression,
        level=0.0,
        name="inner-and-standoff",
    )
    specification = SafetySpecification(
        state=(q1, q2), safe_set=combined_safe_set, initial_set=initial_set
    )

    geofence_invariance = ProofObligation(
        name="geofence-box:robust-one-step-forward-invariance",
        state=(q1, q2),
        expression=geofence_expression + drift,
        comparison="<=",
        region=geofence_set,
        description=(
            "B_geo + dt*Vmax + dt^2/2*sqrt(2)*w <= 0 on {B_geo <= 0}: the worst-case "
            "one-step disturbed coasting drift keeps the drone inside the geofence box "
            "for every admissible velocity and disturbance (Tier-3 robust P1)."
        ),
    )
    geofence_containment = ProofObligation(
        name="geofence-box:initial-containment",
        state=(q1, q2),
        expression=geofence_expression,
        comparison="<=",
        region=initial_set,
        description=(
            "B_geo <= 0 on the initial set: the operating region lies inside the "
            "geofence box."
        ),
    )
    avoidance = ProofObligation(
        name="obstacle-keepout:robust-one-step-avoidance",
        state=(q1, q2),
        expression=keepout_expression + drift,
        comparison="<=",
        region=keepout_set,
        description=(
            "rho - |q - c| + dt*Vmax + dt^2/2*sqrt(2)*w <= 0 on {B_obs <= 0}: the "
            "worst-case one-step disturbed coasting drift keeps the drone outside the "
            "obstacle for every admissible velocity and disturbance (Tier-3 robust P4)."
        ),
    )
    keepout_containment = ProofObligation(
        name="obstacle-keepout:initial-containment",
        state=(q1, q2),
        expression=keepout_expression,
        comparison="<=",
        region=initial_set,
        description=(
            "B_obs <= 0 on the initial set: the operating region lies outside the "
            "obstacle."
        ),
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
    disturbance_bound = AssumptionSpec(
        id="planar-disturbance-within-wind-bound",
        name="planar disturbance within the wind bound",
        role="domain",
        expression=expression_spec(sp.sqrt(w1**2 + w2**2)),
        comparison="<=",
        rhs=float(disturbance_max),
        variables=("w1", "w2"),
        description=(
            "|w| <= sqrt(2)*w: the matched additive disturbance stays within the "
            "planar wind box W = [-w, w]^2; the robust forward-invariance and "
            "avoidance claims are quantified over every admissible (w1, w2) in W "
            "(spec Tier-3 disturbance set). Not plane-expressible in (q1, q2); left "
            "for external discharge."
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
    interior = AssumptionSpec(
        id="operating-region-within-guard-band-interior",
        name="operating region lies in the guard-band interior",
        role="domain",
        expression=expression_spec(inner_interval_expression),
        comparison="<=",
        rhs=0.0,
        variables=("q1", "q2"),
        description=(
            "q in [qMin+dh, qMax-dh]^2: the operating region lies in the geofence "
            "inner interval, where the guard band commands zero thrust so the "
            "closed-loop step is the pure disturbed coasting drift and one step stays "
            "inside the geofence box."
        ),
    )
    standoff_margin = AssumptionSpec(
        id="standoff-exceeds-worst-case-drift",
        name="standoff radius leaves room for one worst-case disturbed drift step",
        role="parameter-domain",
        expression=expression_spec(rho + drift),
        comparison="<=",
        rhs=float(standoff),
        variables=(),
        description=(
            "rho + dt*Vmax + dt^2/2*sqrt(2)*w <= R: the standoff radius exceeds the "
            "obstacle radius by more than one worst-case disturbed coasting step "
            "(precondition of robust one-step avoidance)."
        ),
    )
    geofence_margin = AssumptionSpec(
        id="guard-band-exceeds-worst-case-drift",
        name="guard band leaves room for one worst-case disturbed drift step",
        role="parameter-domain",
        expression=expression_spec(drift),
        comparison="<=",
        rhs=float(band),
        variables=(),
        description=(
            "dt*Vmax + dt^2/2*sqrt(2)*w <= dh: the inner-interval guard band exceeds "
            "one worst-case disturbed coasting step (precondition of robust one-step "
            "geofence forward invariance)."
        ),
    )

    problem = verification_problem_from_obligations(
        "drone disturbed geofence obstacle",
        (geofence_invariance, geofence_containment, avoidance, keepout_containment),
        system=dynamics,
        specification=specification,
        assumptions=(
            speed_bound,
            disturbance_bound,
            maintains_standoff,
            interior,
            standoff_margin,
            geofence_margin,
        ),
        obligation_assumptions={
            "geofence-box:robust-one-step-forward-invariance": (
                "planar-speed-within-velocity-bound",
                "planar-disturbance-within-wind-bound",
                "operating-region-within-guard-band-interior",
                "guard-band-exceeds-worst-case-drift",
            ),
            "geofence-box:initial-containment": (),
            "obstacle-keepout:robust-one-step-avoidance": (
                "planar-speed-within-velocity-bound",
                "planar-disturbance-within-wind-bound",
                "drone-maintains-obstacle-standoff",
                "operating-region-within-guard-band-interior",
                "standoff-exceeds-worst-case-drift",
            ),
            "obstacle-keepout:initial-containment": (),
        },
        metadata={"verificationModel": "drone-disturbed-geofence-obstacle"},
    )

    region_id_by_name = {region.name: region.id for region in problem.regions}
    obligation_id_by_name = {
        obligation.name: obligation.id for obligation in problem.obligations
    }
    candidates = (
        CandidateSpec(
            id="geofence-box-barrier",
            name="geofence-box-barrier",
            kind="barrier",
            expression=expression_spec(geofence_expression),
            obligation_ids=(
                obligation_id_by_name["geofence-box:robust-one-step-forward-invariance"],
                obligation_id_by_name["geofence-box:initial-containment"],
            ),
            region_id=region_id_by_name["geofence-box"],
        ),
        CandidateSpec(
            id="obstacle-keepout-barrier",
            name="obstacle-keepout-barrier",
            kind="barrier",
            expression=expression_spec(keepout_expression),
            obligation_ids=(
                obligation_id_by_name["obstacle-keepout:robust-one-step-avoidance"],
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
    # Each robust one-step claim holds only within its assumption region (the
    # geofence claim in the inner interval, the keep-out claim in the standoff
    # annulus); sample within that region (the velocity and disturbance bounds are
    # non-plane and external-required).
    return replace(
        problem,
        proof_statuses=sampled_region_proof_statuses(
            problem, restrict_to_assumption_regions=True
        ),
    )


def drone_disturbed_geofence_obstacle_trajectory(
    params: DroneParams = DroneParams(),
) -> tuple[np.ndarray, np.ndarray]:
    """Integrate the nominal coupled-plane guard-band loop; columns ``(q1, q2)``.

    The animated path is one admissible realization — the nominal undisturbed
    rollout (the BE-048 pass both inside the geofence box and above the obstacle) —
    that the robust intersection claim must hold around. Discrete-time axis: step
    ``k`` maps to ``k * dt``.
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
            problem_factory=drone_geofence_margin_problem,
            trajectory_factory=drone_geofence_margin_trajectory,
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
        ViewerVerificationExample(
            problem_factory=drone_obstacle_keepout_violation_problem,
            trajectory_factory=drone_obstacle_keepout_violation_trajectory,
            variable_to_state_axis=_DRONE_PLANE_PHASE_AXES,
        ),
        ViewerVerificationExample(
            problem_factory=drone_disturbed_geofence_problem,
            trajectory_factory=drone_disturbed_geofence_trajectory,
            variable_to_state_axis=_DRONE_PHASE_AXES,
        ),
        ViewerVerificationExample(
            problem_factory=drone_geofence_obstacle_problem,
            trajectory_factory=drone_geofence_obstacle_trajectory,
            variable_to_state_axis=_DRONE_PLANE_PHASE_AXES,
        ),
        ViewerVerificationExample(
            problem_factory=drone_vertical_disturbed_geofence_problem,
            trajectory_factory=drone_vertical_disturbed_geofence_trajectory,
            variable_to_state_axis=_DRONE_VERTICAL_PHASE_AXES,
        ),
        ViewerVerificationExample(
            problem_factory=drone_disturbed_obstacle_keepout_problem,
            trajectory_factory=drone_disturbed_obstacle_keepout_trajectory,
            variable_to_state_axis=_DRONE_PLANE_PHASE_AXES,
        ),
        ViewerVerificationExample(
            problem_factory=drone_disturbed_geofence_obstacle_problem,
            trajectory_factory=drone_disturbed_geofence_obstacle_trajectory,
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
    (``packages.index.json``) plus a human-readable cross-package summary
    (``packages.summary.md``) are written beside them so external tools and the
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
    write_package_summary(output_dir)
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
