# Discrete-Time Controlled Dynamics — Design Spec (v0)

Completes the discrete half of `docs/VISION.md` §11 priority 1, deferred from
the continuous layer (`docs/controlled-dynamics.md`). Status: **implemented**
(see Verification record at the bottom).

## Goal

Represent discrete-time controlled systems
`x_{k+1} = F(k, x_k, u_k, d_k; params)` with the same shape, guarantees, and
honesty rules as the continuous layer: symbolic structure first, box-shaped
admissible sets, closed-loop reduction, and deterministic rollouts that
*measure and report* bound violations instead of clipping. Most real
controllers are sampled-data, and many external verification approaches are
natively discrete-time. Backend-only: no manifest, gallery, or viewer change.

## Design decisions

1. **Mirror the continuous layer, do not abstract over it.**
   `DiscreteSystem` and `ControlledDiscreteSystem`
   (`engine/dynamics/discrete.py`) parallel `FirstOrderSystem` and
   `ControlledFirstOrderSystem` — same field names, same validation, same
   closed-loop reduction semantics (missing disturbances default to zero;
   law-introduced symbols become parameters; leftover input symbols raise).
   A shared base abstraction would couple the two layers for little gain.
2. **The step index replaces time.** Systems carry a `step` symbol
   (default `k`, integer, non-negative) anywhere the continuous layer
   carries `time`; update expressions and feedback laws may reference it.
3. **Structure helpers match discrete semantics.** `fixed_points` solves
   `F(x) = x` (not `F(x) = 0`); stability of a linearization is a spectral
   radius question for the caller — the engine does not decide stability.
4. **Rollouts are deterministic and never clip.** `discrete_rollout`
   iterates the map under numeric laws `u(k, x)`, records applied controls
   and disturbances (steps `0..N-1`, one row fewer than states), and reports
   measured `Box` violations exactly like the continuous `rollout`.
5. **Euler discretization is an explicit modeling decision.**
   `euler_discretization(system, dt)` builds the forward-Euler map
   `x + dt f(x, u, d)` from an *autonomous* continuous system (controlled or
   not), carrying admissible boxes through and turning a symbolic `dt` into
   a parameter. The map approximates the sampled flow to first order; it is
   not the flow, and the docstring says so. Time-dependent systems raise.
6. **Verification IR encoding.** `engine.verification.system_codec` can now
   encode `DiscreteSystem` and `ControlledDiscreteSystem` as
   `DynamicsSpec(kind="discrete")` with `stepVariable`, `update`, and the
   same control/disturbance input records used by continuous dynamics.
7. **Discrete safety obligations are symbolic candidates.**
   `engine.dynamics.safety.discrete_difference` builds
   `V(k+1, F(k, x)) - V(k, x)`, and Lyapunov/barrier candidates can emit the
   discrete non-increase obligations `V(F) - V <= 0` and `B(F) - B <= 0`.
   These remain external-required proof obligations; sampling them is still
   measured evidence only.
8. **Controlled verification export preserves both models.** The
   controlled-discrete verification helpers close the system under a symbolic
   feedback law, derive obligations on that closed-loop map, and also export
   the original controlled map as `openLoopDynamics` with its
   control/disturbance bounds. The feedback law is metadata, not a proof
   certificate.
9. **Deferred (out of v0):** exact/zero-order-hold discretization,
   stochastic disturbances, discrete control synthesis, validated numerics,
   and proof discharge.

## Files

- `engine/dynamics/discrete.py` — `DiscreteSystem`,
  `ControlledDiscreteSystem`, `DiscreteRolloutResult`, `discrete_rollout`,
  `euler_discretization`, `DiscreteControlLaw`.
- `engine/verification/system_codec.py` — verification-IR codecs for
  closed-loop and controlled discrete systems.
- `engine/verification/safety_adapter.py` — closed-loop discrete and
  controlled-discrete feedback export helpers for Lyapunov/barrier
  obligations.
- `engine/dynamics/safety.py` — discrete one-step differences and candidate
  proof obligations.
- `engine/dynamics/__init__.py` — exports.
- `tests/test_discrete_dynamics.py` — obligations below.

## Invariants / proof obligations (for this implementation)

1. **Structure (proven on examples).** The logistic map's fixed points are
   `{0, (r-1)/r}` and its Jacobian is `r(1-2x)` symbolically.
2. **Closed-loop reduction (proven + measured).** A proportional-derivative
   law on the discrete double integrator yields a `DiscreteSystem` whose
   gains become parameters, whose linearization is Schur stable for the test
   gains, and whose iteration converges to the origin; non-control symbols,
   missing controls, and laws that reintroduce inputs raise.
3. **Honest rollouts (proven on examples).** An aggressive law's bound
   violation is reported (worst distance outside the box) while the applied,
   unclipped control drives the state; an explicitly saturated law reports
   zero violation.
4. **Euler bridge (measured).** The Euler-discretized controlled pendulum
   under the same PD law tracks the continuous RK4 rollout to 2e-2 over one
   second at `dt = 1e-3`; bounds carry through discretization; symbolic `dt`
   becomes a parameter; non-autonomous systems raise.
5. **Determinism (measured).** Repeated iterations are bit-identical.
6. **IR encoding (proven on examples).** Closed-loop and open-loop discrete
   systems serialize with `kind="discrete"`, `stepVariable`, update
   expressions, and admissible control/disturbance bounds.
7. **Discrete safety obligations (proven + measured).** The stable map
   `x_{k+1} = x_k/2` yields nonpositive one-step Lyapunov/barrier changes on
   sampled regions, while `x_{k+1} = 2 x_k` yields a counterexample.
8. **Controlled verification export (proven on examples).** A controlled
   discrete system with a symbolic feedback law serializes closed-loop
   obligations, the open-loop bounded channels, and feedback-law metadata
   deterministically.

## Verification commands

```sh
pytest tests/test_discrete_dynamics.py -q
pytest -q
```

No generator or viewer commands: nothing crosses the manifest boundary.

## Out of scope

Everything listed under "Deferred" above, plus manifest/export schema changes
and frontend surfaces.

## Verification record

Implemented and verified 2026-06-12: `pytest -q` green including
`tests/test_discrete_dynamics.py` (see `docs/BACKEND.md` baseline for the
current count).

Updated 2026-06-13: discrete-time dynamics can be encoded in the verification
IR through `dynamics_spec_from_discrete` and
`dynamics_spec_from_controlled_discrete`; focused tests pass with
`pytest tests/test_verification_ir.py tests/test_inspection_adapter.py tests/test_discrete_dynamics.py -q`.

Updated 2026-06-13: discrete-time Lyapunov/barrier proof obligations are
available through `LyapunovCandidate.discrete_proof_obligations` and
`BarrierCandidate.discrete_proof_obligations`; focused tests pass with
`pytest tests/test_safety_certificates.py tests/test_verification_ir.py tests/test_discrete_dynamics.py -q`.

Updated 2026-06-13: controlled-discrete Lyapunov/barrier exports are
available through
`verification_problem_from_controlled_discrete_lyapunov` and
`verification_problem_from_controlled_discrete_barrier`; focused tests pass
with
`pytest tests/test_verification_ir.py tests/test_inspection_adapter.py tests/test_safety_certificates.py tests/test_discrete_dynamics.py -q`.
