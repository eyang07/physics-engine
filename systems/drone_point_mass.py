"""Guard-band feedback-controlled point-mass drone (backend-only flagship).

The canonical safety model from the DroneV study (`DRONE_MODEL_SPEC.md`): a
geofenced point mass in 3-D whose **exact zero-order-hold sampled-data** dynamics
are a discrete map, regulated by a per-axis **guard-band** feedback law that
fires corrective thrust only near the geofence walls. The control objective is
*set membership* (stay in the safe box), not convergence to a point — there is no
single equilibrium, so the certificate is a forward-invariance (barrier) one, not
a Lyapunov function.

State ``x = (q1, q2, q3, v1, v2, v3)`` (position then velocity; axis 3 is
altitude). Control ``u = (u1, u2, u3)`` is acceleration/thrust. With gravity ``g``
along ``-e3`` (``e3 = (0, 0, 1)``) the continuous origin is ``q'' = u - g e3``;
integrating it under a zero-order hold over one sample ``dt`` is *exact* (the
half-``dt^2`` term is the closed-form position integral, not an Euler
truncation), giving the discrete map this module builds.

This module stays thin: it defines the symbolic plant, the symbolic guard-band
feedback law, and the deterministic rollout. Safe/unsafe sets, candidate
certificates, and proof obligations are assembled downstream (the verification
export), mirroring how the pendulum/spring plants are kept separate from their
verification problems.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass

import sympy as sp

from engine.dynamics import (
    Box,
    ControlledDiscreteSystem,
    DiscreteRolloutResult,
    DiscreteSystem,
    discrete_rollout,
)

# Position then velocity; q3 / v3 are altitude (axis 3 in the paper, axis 2 in Lean).
DRONE_STATE: tuple[sp.Symbol, ...] = sp.symbols("q1 q2 q3 v1 v2 v3", real=True)
DRONE_CONTROLS: tuple[sp.Symbol, ...] = sp.symbols("u1 u2 u3", real=True)


def _rational(value: float) -> sp.Expr:
    """Exact SymPy number for a (dyadic) parameter value."""

    return sp.nsimplify(value, rational=True)


@dataclass(frozen=True)
class DroneParams:
    """Geometry, thrust authority, and timing for the geofenced drone.

    Defaults are the model-checking instantiation from the spec (normalized,
    ``g = 1``): geofence ``[-1, 1]^2 x [0, 2]``, guard bands ``1/4``, horizontal
    thrust ``1``, vertical thrust in ``[0, 2]``, sample period ``1/4``.
    """

    timestep: float = 0.25
    gravity: float = 1.0
    q1_bounds: tuple[float, float] = (-1.0, 1.0)
    q2_bounds: tuple[float, float] = (-1.0, 1.0)
    q3_bounds: tuple[float, float] = (0.0, 2.0)
    horizontal_band: float = 0.25
    floor_band: float = 0.25
    ceiling_band: float = 0.25
    horizontal_thrust: float = 1.0
    vertical_thrust_min: float = 0.0
    vertical_thrust_max: float = 2.0

    def __post_init__(self) -> None:
        # Params.Valid: the conditions the safety argument assumes (spec G).
        if self.timestep <= 0:
            raise ValueError("timestep must be positive")
        if min(self.horizontal_band, self.floor_band, self.ceiling_band) <= 0:
            raise ValueError("guard bands must be positive")
        if self.horizontal_thrust <= 0:
            raise ValueError("horizontal thrust authority must be positive")
        # Vertical authority both ways: net descent and net ascent are possible.
        if not (self.vertical_thrust_min < self.gravity < self.vertical_thrust_max):
            raise ValueError(
                "vertical thrust must straddle gravity: u3Min < g < u3Max"
            )
        if self.vertical_thrust_min < 0:
            raise ValueError("minimum vertical thrust must be nonnegative")
        # Inner set non-empty: opposite guard bands are disjoint.
        q1_min, q1_max = self.q1_bounds
        q2_min, q2_max = self.q2_bounds
        q3_min, q3_max = self.q3_bounds
        if 2 * self.horizontal_band >= q1_max - q1_min:
            raise ValueError("horizontal guard bands overlap on axis 1")
        if 2 * self.horizontal_band >= q2_max - q2_min:
            raise ValueError("horizontal guard bands overlap on axis 2")
        if self.floor_band + self.ceiling_band >= q3_max - q3_min:
            raise ValueError("vertical guard bands overlap")

    @property
    def hover_thrust(self) -> float:
        """Thrust that cancels gravity (the interior vertical command)."""

        return self.gravity

    @property
    def horizontal_velocity_bound(self) -> float:
        """Bh = uh * dt: the per-step horizontal velocity bound."""

        return self.horizontal_thrust * self.timestep

    @property
    def vertical_reach(self) -> float:
        """max(u3Max - g, g - u3Min): per-step vertical acceleration capacity.

        The net corrective acceleration the guard band can command toward the
        floor (``u3Max - g``, upward) or ceiling (``g - u3Min``, downward).
        """

        return max(
            self.vertical_thrust_max - self.gravity,
            self.gravity - self.vertical_thrust_min,
        )

    @property
    def vertical_velocity_bound(self) -> float:
        """B3 = max(u3Max - g, g - u3Min) * dt: the vertical velocity bound."""

        return self.vertical_reach * self.timestep

    @property
    def velocity_bound(self) -> float:
        """Vmax = max(Bh, B3): the self-reproducing per-axis velocity bound."""

        return max(self.horizontal_velocity_bound, self.vertical_velocity_bound)


def build_system(params: DroneParams = DroneParams()) -> ControlledDiscreteSystem:
    """The exact zero-order-hold sampled-data drone plant (open loop).

    ``q+ = q + dt v + (dt^2 / 2)(u - g e3)`` and ``v+ = v + dt (u - g e3)``. The
    admissible control box is ``[-uh, uh]^2 x [u3Min, u3Max]``.
    """

    q1, q2, q3, v1, v2, v3 = DRONE_STATE
    u1, u2, u3 = DRONE_CONTROLS
    dt = _rational(params.timestep)
    g = _rational(params.gravity)
    half_dt2 = dt**2 / 2

    update = (
        q1 + dt * v1 + half_dt2 * u1,
        q2 + dt * v2 + half_dt2 * u2,
        q3 + dt * v3 + half_dt2 * (u3 - g),
        v1 + dt * u1,
        v2 + dt * u2,
        v3 + dt * (u3 - g),
    )
    control_bounds = Box(
        lower=(
            -params.horizontal_thrust,
            -params.horizontal_thrust,
            params.vertical_thrust_min,
        ),
        upper=(
            params.horizontal_thrust,
            params.horizontal_thrust,
            params.vertical_thrust_max,
        ),
    )
    return ControlledDiscreteSystem(
        state=DRONE_STATE,
        controls=DRONE_CONTROLS,
        update=update,
        control_bounds=control_bounds,
    )


def _horizontal_law(
    position: sp.Symbol,
    velocity: sp.Symbol,
    lower: float,
    upper: float,
    params: DroneParams,
) -> sp.Expr:
    """Push inward only when near a wall and moving out; otherwise coast."""

    band = _rational(params.horizontal_band)
    thrust = _rational(params.horizontal_thrust)
    lo, hi = _rational(lower), _rational(upper)
    return sp.Piecewise(
        (thrust, sp.And(position <= lo + band, velocity < 0)),
        (-thrust, sp.And(position >= hi - band, velocity > 0)),
        (sp.Integer(0), True),
    )


def _vertical_law(
    position: sp.Symbol,
    velocity: sp.Symbol,
    params: DroneParams,
) -> sp.Expr:
    """Hover in the interior; brake toward the floor/ceiling near the bounds.

    Full upward thrust near the floor (descending) and minimum thrust near the
    ceiling (ascending); otherwise hover thrust cancels gravity. Asymmetric in
    both authority and band width, unlike the symmetric horizontal law.
    """

    q3_min, q3_max = params.q3_bounds
    return sp.Piecewise(
        (
            _rational(params.vertical_thrust_max),
            sp.And(position <= _rational(q3_min) + _rational(params.floor_band), velocity < 0),
        ),
        (
            _rational(params.vertical_thrust_min),
            sp.And(position >= _rational(q3_max) - _rational(params.ceiling_band), velocity > 0),
        ),
        (_rational(params.hover_thrust), True),
    )


def guard_band_control_law(
    params: DroneParams = DroneParams(),
) -> dict[sp.Symbol, sp.Expr]:
    """The symbolic per-axis guard-band feedback law ``u = g(x)``.

    Each branch is selected first-match (matching the controller's if/elif), so
    under :class:`DroneParams` validity (disjoint opposite bands) the law is
    single-valued. The horizontal axes coast in the interior; the vertical axis
    hovers in the interior and brakes toward the floor/ceiling near the bounds.
    """

    q1, q2, q3, v1, v2, v3 = DRONE_STATE
    u1, u2, u3 = DRONE_CONTROLS
    q1_min, q1_max = params.q1_bounds
    q2_min, q2_max = params.q2_bounds

    return {
        u1: _horizontal_law(q1, v1, q1_min, q1_max, params),
        u2: _horizontal_law(q2, v2, q2_min, q2_max, params),
        u3: _vertical_law(q3, v3, params),
    }


def closed_loop(params: DroneParams = DroneParams()) -> DiscreteSystem:
    """The autonomous closed-loop map ``x -> F(x, g(x))``."""

    return build_system(params).closed_loop(guard_band_control_law(params))


def guard_band_controller(
    params: DroneParams = DroneParams(),
) -> Callable[[int, Sequence[float]], tuple[float, ...]]:
    """A numeric ``(step, state) -> control`` law for deterministic rollouts.

    Derived by lambdifying the symbolic guard-band law, so the rollout and the
    closed-loop dynamics share one definition of the controller.
    """

    law = guard_band_control_law(params)
    compiled = sp.lambdify(DRONE_STATE, [law[symbol] for symbol in DRONE_CONTROLS], "numpy")

    def controller(step: int, state: Sequence[float]) -> tuple[float, ...]:
        return tuple(float(value) for value in compiled(*state))

    return controller


# A safe reference start inside the inner set (spec L-1): centered horizontally,
# hovering altitude, coasting in +x at the velocity bound.
DEFAULT_INITIAL_STATE: tuple[float, ...] = (0.0, 0.0, 1.0, 0.25, 0.0, 0.0)
DEFAULT_STEP_COUNT = 16


def safe_rollout(
    params: DroneParams = DroneParams(),
    *,
    initial_state: Sequence[float] = DEFAULT_INITIAL_STATE,
    step_count: int = DEFAULT_STEP_COUNT,
) -> DiscreteRolloutResult:
    """Deterministically iterate the guard-band closed loop.

    The drone coasts until it nears a geofence wall, where the guard band fires
    corrective thrust and holds it inside the safe box. Bound violations are
    measured and reported by :func:`discrete_rollout`, never clipped.
    """

    return discrete_rollout(
        build_system(params),
        guard_band_controller(params),
        initial_state=initial_state,
        step_count=step_count,
    )


# --- Decoupled horizontal-axis sub-dynamics --------------------------------
#
# Under the Tier-1 guard-band law each axis is independent: the (q1, v1)
# dynamics and the axis-1 controller depend only on (q1, v1). This exact 2-D
# sub-system is the natural geofence verification problem and renders directly on
# the (q1, v1) phase plane (spec M), with no projection of the 6-D state.

_AXIS1_POSITION = DRONE_STATE[0]
_AXIS1_VELOCITY = DRONE_STATE[3]
_AXIS1_CONTROL = DRONE_CONTROLS[0]


def horizontal_axis_system(
    params: DroneParams = DroneParams(),
) -> ControlledDiscreteSystem:
    """The decoupled ``(q1, v1)`` horizontal sub-dynamics (open loop)."""

    dt = _rational(params.timestep)
    update = (
        _AXIS1_POSITION + dt * _AXIS1_VELOCITY + dt**2 / 2 * _AXIS1_CONTROL,
        _AXIS1_VELOCITY + dt * _AXIS1_CONTROL,
    )
    return ControlledDiscreteSystem(
        state=(_AXIS1_POSITION, _AXIS1_VELOCITY),
        controls=(_AXIS1_CONTROL,),
        update=update,
        control_bounds=Box(
            lower=(-params.horizontal_thrust,),
            upper=(params.horizontal_thrust,),
        ),
    )


def horizontal_axis_control_law(
    params: DroneParams = DroneParams(),
) -> dict[sp.Symbol, sp.Expr]:
    """The axis-1 guard-band feedback law ``u1 = g1(q1, v1)``."""

    q1_min, q1_max = params.q1_bounds
    return {
        _AXIS1_CONTROL: _horizontal_law(
            _AXIS1_POSITION, _AXIS1_VELOCITY, q1_min, q1_max, params
        )
    }


def horizontal_axis_closed_loop(params: DroneParams = DroneParams()) -> DiscreteSystem:
    """The autonomous ``(q1, v1)`` closed loop under the guard-band law."""

    return horizontal_axis_system(params).closed_loop(horizontal_axis_control_law(params))


def horizontal_axis_controller(
    params: DroneParams = DroneParams(),
) -> Callable[[int, Sequence[float]], tuple[float, ...]]:
    """A numeric ``(step, (q1, v1)) -> (u1,)`` law for axis-1 rollouts."""

    law = horizontal_axis_control_law(params)[_AXIS1_CONTROL]
    compiled = sp.lambdify((_AXIS1_POSITION, _AXIS1_VELOCITY), law, "numpy")

    def controller(step: int, state: Sequence[float]) -> tuple[float, ...]:
        return (float(compiled(state[0], state[1])),)

    return controller


# A safe axis-1 start inside the inner interval, coasting outward at the
# velocity bound (the (q1, v1) slice of DEFAULT_INITIAL_STATE).
DEFAULT_AXIS_INITIAL_STATE: tuple[float, ...] = (0.0, 0.25)


def horizontal_axis_rollout(
    params: DroneParams = DroneParams(),
    *,
    initial_state: Sequence[float] = DEFAULT_AXIS_INITIAL_STATE,
    step_count: int = DEFAULT_STEP_COUNT,
) -> DiscreteRolloutResult:
    """Deterministically iterate the axis-1 guard-band closed loop."""

    return discrete_rollout(
        horizontal_axis_system(params),
        horizontal_axis_controller(params),
        initial_state=initial_state,
        step_count=step_count,
    )


# --- Decoupled vertical altitude-axis sub-dynamics -------------------------
#
# The altitude axis is the asymmetric vertical regime: the open-loop map carries
# the gravity term `u3 - g`, the interior command is hover thrust (`u3 = g`), and
# the guard band uses floor/ceiling thrust toward the bounds. Under the Tier-1
# law this `(q3, v3)` axis is independent of the others, giving an exact 2-D
# sub-system that renders directly on the `(q3, v3)` plane.

_AXIS3_POSITION = DRONE_STATE[2]
_AXIS3_VELOCITY = DRONE_STATE[5]
_AXIS3_CONTROL = DRONE_CONTROLS[2]


def vertical_axis_system(
    params: DroneParams = DroneParams(),
) -> ControlledDiscreteSystem:
    """The decoupled ``(q3, v3)`` vertical sub-dynamics (open loop).

    Carries the gravity offset: ``q3+ = q3 + dt v3 + dt^2/2 (u3 - g)`` and
    ``v3+ = v3 + dt (u3 - g)``, with thrust box ``[u3Min, u3Max]``.
    """

    dt = _rational(params.timestep)
    g = _rational(params.gravity)
    update = (
        _AXIS3_POSITION + dt * _AXIS3_VELOCITY + dt**2 / 2 * (_AXIS3_CONTROL - g),
        _AXIS3_VELOCITY + dt * (_AXIS3_CONTROL - g),
    )
    return ControlledDiscreteSystem(
        state=(_AXIS3_POSITION, _AXIS3_VELOCITY),
        controls=(_AXIS3_CONTROL,),
        update=update,
        control_bounds=Box(
            lower=(params.vertical_thrust_min,),
            upper=(params.vertical_thrust_max,),
        ),
    )


def vertical_axis_control_law(
    params: DroneParams = DroneParams(),
) -> dict[sp.Symbol, sp.Expr]:
    """The axis-3 guard-band feedback law ``u3 = g3(q3, v3)``."""

    return {_AXIS3_CONTROL: _vertical_law(_AXIS3_POSITION, _AXIS3_VELOCITY, params)}


def vertical_axis_closed_loop(params: DroneParams = DroneParams()) -> DiscreteSystem:
    """The autonomous ``(q3, v3)`` closed loop under the guard-band law."""

    return vertical_axis_system(params).closed_loop(vertical_axis_control_law(params))


def vertical_axis_controller(
    params: DroneParams = DroneParams(),
) -> Callable[[int, Sequence[float]], tuple[float, ...]]:
    """A numeric ``(step, (q3, v3)) -> (u3,)`` law for axis-3 rollouts."""

    law = vertical_axis_control_law(params)[_AXIS3_CONTROL]
    compiled = sp.lambdify((_AXIS3_POSITION, _AXIS3_VELOCITY), law, "numpy")

    def controller(step: int, state: Sequence[float]) -> tuple[float, ...]:
        return (float(compiled(state[0], state[1])),)

    return controller


# A safe axis-3 start inside the inner interval: hovering altitude, coasting
# upward at the vertical velocity bound so it reaches the ceiling guard band.
DEFAULT_VERTICAL_AXIS_INITIAL_STATE: tuple[float, ...] = (1.0, 0.25)


def vertical_axis_rollout(
    params: DroneParams = DroneParams(),
    *,
    initial_state: Sequence[float] = DEFAULT_VERTICAL_AXIS_INITIAL_STATE,
    step_count: int = DEFAULT_STEP_COUNT,
) -> DiscreteRolloutResult:
    """Deterministically iterate the axis-3 guard-band closed loop."""

    return discrete_rollout(
        vertical_axis_system(params),
        vertical_axis_controller(params),
        initial_state=initial_state,
        step_count=step_count,
    )


# --- Coupled horizontal-plane sub-dynamics (Tier-2) ------------------------
#
# The first non-decoupled regime: both horizontal axes together, (q1, q2, v1,
# v2), under the per-axis guard-band law. The axes stay dynamically decoupled
# (each control depends only on its own axis), but a planar keep-out constraint
# around an obstacle couples q1 and q2 geometrically. This 2-D position plane is
# the natural stage for the Tier-2 obstacle problem (spec P4): in the geofence
# interior the guard band commands zero thrust, so the closed-loop step is the
# exact coasting drift q+ = q + dt v.

_PLANE_STATE = (DRONE_STATE[0], DRONE_STATE[1], DRONE_STATE[3], DRONE_STATE[4])
_PLANE_CONTROLS = (DRONE_CONTROLS[0], DRONE_CONTROLS[1])


@dataclass(frozen=True)
class ObstacleSpec:
    """A circular keep-out obstacle in the ``(q1, q2)`` horizontal plane.

    ``standoff_radius`` is the operating-annulus radius the keep-out argument
    works within: from outside it, one bounded-speed coasting step cannot reach
    the obstacle. It must exceed the obstacle radius. Defaults place a small
    obstacle at the geofence center with a standoff that fits the interior.
    """

    center: tuple[float, float] = (0.0, 0.0)
    radius: float = 0.25
    standoff_radius: float = 0.5

    def __post_init__(self) -> None:
        if self.radius <= 0:
            raise ValueError("obstacle radius must be positive")
        if self.standoff_radius <= self.radius:
            raise ValueError("standoff radius must exceed the obstacle radius")


DEFAULT_OBSTACLE = ObstacleSpec()


def horizontal_plane_system(
    params: DroneParams = DroneParams(),
) -> ControlledDiscreteSystem:
    """The coupled ``(q1, q2, v1, v2)`` horizontal sub-dynamics (open loop)."""

    q1, q2, v1, v2 = _PLANE_STATE
    u1, u2 = _PLANE_CONTROLS
    dt = _rational(params.timestep)
    update = (
        q1 + dt * v1 + dt**2 / 2 * u1,
        q2 + dt * v2 + dt**2 / 2 * u2,
        v1 + dt * u1,
        v2 + dt * u2,
    )
    return ControlledDiscreteSystem(
        state=_PLANE_STATE,
        controls=_PLANE_CONTROLS,
        update=update,
        control_bounds=Box(
            lower=(-params.horizontal_thrust, -params.horizontal_thrust),
            upper=(params.horizontal_thrust, params.horizontal_thrust),
        ),
    )


def horizontal_plane_control_law(
    params: DroneParams = DroneParams(),
) -> dict[sp.Symbol, sp.Expr]:
    """The per-axis guard-band law on the coupled plane: ``(u1, u2) = g(q, v)``."""

    q1, q2, v1, v2 = _PLANE_STATE
    u1, u2 = _PLANE_CONTROLS
    q1_min, q1_max = params.q1_bounds
    q2_min, q2_max = params.q2_bounds
    return {
        u1: _horizontal_law(q1, v1, q1_min, q1_max, params),
        u2: _horizontal_law(q2, v2, q2_min, q2_max, params),
    }


def horizontal_plane_closed_loop(params: DroneParams = DroneParams()) -> DiscreteSystem:
    """The autonomous ``(q1, q2, v1, v2)`` closed loop under the guard-band law."""

    return horizontal_plane_system(params).closed_loop(horizontal_plane_control_law(params))


def horizontal_plane_controller(
    params: DroneParams = DroneParams(),
) -> Callable[[int, Sequence[float]], tuple[float, ...]]:
    """A numeric ``(step, (q1, q2, v1, v2)) -> (u1, u2)`` law for plane rollouts."""

    law = horizontal_plane_control_law(params)
    compiled = sp.lambdify(_PLANE_STATE, [law[symbol] for symbol in _PLANE_CONTROLS], "numpy")

    def controller(step: int, state: Sequence[float]) -> tuple[float, ...]:
        return tuple(float(value) for value in compiled(*state))

    return controller


# A safe planar start: upper-left, coasting in +q1 above the centered obstacle,
# staying clear of the standoff annulus throughout the pass.
DEFAULT_PLANE_INITIAL_STATE: tuple[float, ...] = (-0.7, 0.6, 0.25, 0.0)


def horizontal_plane_rollout(
    params: DroneParams = DroneParams(),
    *,
    initial_state: Sequence[float] = DEFAULT_PLANE_INITIAL_STATE,
    step_count: int = DEFAULT_STEP_COUNT,
) -> DiscreteRolloutResult:
    """Deterministically iterate the coupled horizontal-plane guard-band loop."""

    return discrete_rollout(
        horizontal_plane_system(params),
        horizontal_plane_controller(params),
        initial_state=initial_state,
        step_count=step_count,
    )


system = build_system()
