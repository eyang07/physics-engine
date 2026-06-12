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
6. **Deferred (out of v0):** exact/zero-order-hold discretization, discrete
   safety obligations (`V(F(x)) - V(x) <= 0` analogues), discrete dynamics
   in the verification IR (`DynamicsSpec` is continuous-only in v1),
   stochastic disturbances, and discrete control synthesis.

## Files

- `engine/dynamics/discrete.py` — `DiscreteSystem`,
  `ControlledDiscreteSystem`, `DiscreteRolloutResult`, `discrete_rollout`,
  `euler_discretization`, `DiscreteControlLaw`.
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
