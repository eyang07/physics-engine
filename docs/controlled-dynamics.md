# Controlled Dynamics Layer — Design Spec (v0)

Advances `docs/VISION.md` §11 priority 1. Status: **implemented** (see
Verification at the bottom).

## Goal

Extend the dynamics layer from autonomous flows `dx/dt = f(t, x; params)` to
controlled flows

```text
dx/dt = f(t, x, u, d; params)
```

with explicit control symbols `u`, disturbance symbols `d`, box-shaped
admissible sets, closed-loop reduction to the existing `FirstOrderSystem`
layer, and deterministic rollouts under a numeric control law. This is the
prerequisite for safe sets, certificate candidates, and the
verification-problem IR. Backend-only: no manifest, gallery, or viewer change.

## Design decisions

1. **Closed-loop reduction is the load-bearing move.** A symbolic feedback law
   `u = pi(t, x)` substituted into the controlled RHS yields a plain
   `FirstOrderSystem`, so every existing diagnostic (Jacobian, divergence,
   fixed points, linearization, FTLE, invariant residuals) applies to
   closed-loop systems with zero new code.
2. **Admissible sets are value objects, honesty-first.** v0 supports
   axis-aligned boxes (`Box`) for controls and disturbances. Rollouts *measure
   and report* bound violations; they never silently clip. Saturation is a
   modeling decision the caller makes explicitly (e.g. by clipping inside the
   control law via `Box.clip`).
3. **The open-loop system stays symbolic; rollout laws are numeric.** Symbolic
   laws go through `closed_loop(...)`; arbitrary numeric policies (eventually
   learned ones) go through `rollout(...)`, which composes lambdified
   dynamics with a Python callable `u(t, x)`.
4. **Anchor system: the controlled pendulum** (`systems/controlled_pendulum.py`,
   torque-actuated, with damping). Smallest step from existing code; cart-pole
   or a drone point-mass can follow once safety metadata exists. Backend-only,
   not registered in the gallery.
5. **Deferred from the controlled-dynamics layer itself:** real certificate
   synthesis and proof discharge. The discrete-time analogue
   `x_{k+1} = F(x_k, u_k, d_k)`, originally deferred here, is now implemented
   (`docs/discrete-dynamics.md`). Safe/unsafe sets, certificate candidates,
   proof obligations, and the verification IR are handled by later backend
   layers. Stochastic disturbances are out; `d` is a deterministic input
   channel in v0.

## Files

- `engine/dynamics/controlled.py` — `Box`, `ControlledFirstOrderSystem`,
  `RolloutResult`, `rollout`.
- `systems/controlled_pendulum.py` — torque-controlled damped pendulum.
- `tests/test_controlled_dynamics.py` — obligations below.
- `engine/dynamics/__init__.py` — exports.
- Doc updates: `README.md`, `docs/BACKEND.md`, `docs/VISION.md` §8 status
  note / §11, and test-count baselines.

## API sketch

```python
@dataclass(frozen=True)
class Box:                       # axis-aligned admissible set
    lower: tuple[float, ...]
    upper: tuple[float, ...]
    # contains(values, tolerance), violation(values) -> float, clip(values)

@dataclass(frozen=True)
class ControlledFirstOrderSystem:
    state: tuple[sp.Symbol, ...]
    controls: tuple[sp.Symbol, ...]
    rhs: tuple[sp.Expr, ...]
    disturbances: tuple[sp.Symbol, ...] = ()
    parameters: tuple[sp.Symbol, ...] = ()
    time: sp.Symbol = t
    control_bounds: Box | None = None
    disturbance_bounds: Box | None = None
    # state_jacobian (df/dx), control_jacobian (df/du),
    # disturbance_jacobian (df/dd), is_equilibrium(x*, u*, d*),
    # closed_loop(control_law, disturbance_law) -> FirstOrderSystem,
    # numerical_rhs(control, disturbance, substitutions) -> rhs(t, x)

def rollout(system, control, *, initial_state, t_span, dt,
            disturbance=None, substitutions=None) -> RolloutResult
    # RolloutResult: time, states, controls, disturbances,
    # control_violation, disturbance_violation (measured suprema, 0 if none)
```

## Invariants / proof obligations

1. **Closed-loop reduction (proven).** `closed_loop({u: pi})` produces a
   `FirstOrderSystem` whose RHS equals the controlled RHS with `u -> pi`
   substituted; leftover control/disturbance symbols raise.
2. **Control Jacobian (proven).** For the controlled pendulum,
   `df/du = (0, 1/(m l^2))^T` exactly.
3. **Mechanics consistency (proven).** With `u = 0` and zero damping, the
   closed-loop pendulum conserves `E = m l^2 w^2 / 2 - m g l cos(theta)`
   symbolically.
4. **Equilibrium family (proven).** Gravity compensation
   `u* = m g l sin(theta*)` makes every `(theta*, 0)` an equilibrium,
   symbolically, as a family in `theta*`.
5. **Stabilization (measured).** A PD law about the upright equilibrium gives
   a closed-loop linearization with all eigenvalue real parts negative, and a
   rollout from a nearby state converges to upright within stated tolerance.
6. **Admissibility reporting (measured).** A rollout whose torque demand
   exceeds `control_bounds` reports a positive violation; a clipped law
   reports zero violation. No silent clipping.
7. **Determinism (measured).** Two identical rollouts produce identical
   arrays.

## Verification commands

```sh
pytest tests/test_controlled_dynamics.py -q   # targeted
pytest -q                                     # full backend suite
```

No generator or viewer commands: nothing crosses the manifest boundary.

## Out of scope

Real certificate synthesis or proof discharge; any manifest/schema change;
any gallery or viewer work; stochastic disturbances; control synthesis
(LQR/MPC) beyond hand-written test laws. (The discrete-time analogue, out of
scope here, has since been implemented: `docs/discrete-dynamics.md`.)

## Verification record

Implemented and verified 2026-06-12: `pytest -q` green including
`tests/test_controlled_dynamics.py` (see `docs/BACKEND.md` baseline for the
current count). Obligations 1–4 hold symbolically; 5–7 measured with the
tolerances encoded in the tests.
