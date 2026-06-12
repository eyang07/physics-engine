# Symplectic Integrators — Design Spec (v0)

Structure-preserving integration for separable Hamiltonian systems, in line
with the theory-first principle (`docs/VISION.md` §3): long-run invariant
diagnostics should reflect the dynamics, not integrator drift. Status:
**implemented** (see Verification record at the bottom).

## Goal

Give Hamiltonian examples an integrator that preserves the symplectic
structure, so energy error stays bounded over long runs instead of drifting
secularly as with RK4/DOP853. Backend-only: generators and the viewer are
unchanged; switching generated examples to symplectic integration is a
separate, deliberate data-regeneration decision.

## Design decisions

1. **Split-form API for separable Hamiltonians.** `H = T(p) + V(q)` admits
   explicit symplectic methods. `engine.numerics.integrate_symplectic`
   takes two callables — `velocity(p) = dH/dp` and `force(q) = -dH/dq` —
   plus separate initial position/momentum, and returns `(times, states)`
   with rows `[q_0, ..., q_n, p_0, ..., p_n]`, matching
   `HamiltonianSystem.numerical_rhs` layout and the fixed-step time-grid
   conventions.
2. **Two methods, explicitly named.** `symplectic-euler` (order 1) and
   `stormer-verlet` (order 2, symmetric, time-reversible) — the standard
   explicit pair. Higher-order compositions (e.g. Yoshida) are future work.
3. **Separability is checked symbolically, not assumed.**
   `HamiltonianSystem.separable_split` verifies the Hamiltonian is
   autonomous and that every cross derivative `d^2 H / dq_i dp_j` vanishes
   before lambdifying the two halves; non-separable or time-dependent
   Hamiltonians raise. `HamiltonianSystem.is_separable` exposes the check.
4. **Honesty about what symplecticity buys.** A symplectic step preserves
   phase-space structure; trajectories are still approximate and energy
   error is bounded, not zero. The docstring says so.
5. **Deferred (out of v0):** non-separable methods (implicit midpoint),
   higher-order compositions, variational integrators for constrained
   systems, and switching generated examples to symplectic integration.

## Files

- `engine/numerics/integrators.py` — `symplectic_euler_step`,
  `stormer_verlet_step`, `integrate_symplectic`, `SplitRhs`.
- `engine/mechanics/hamiltonian.py` — `HamiltonianSystem.is_separable`,
  `HamiltonianSystem.separable_split`.
- `engine/numerics/__init__.py` — exports.
- `tests/test_symplectic_integrators.py` — obligations below.

## Invariants / proof obligations (for this implementation)

1. **Convergence order (measured).** Halving `dt` quarters the
   Störmer-Verlet global error and halves the symplectic-Euler error on the
   harmonic oscillator against the analytic solution.
2. **Bounded energy error (measured).** Over 10k Verlet steps of the
   harmonic oscillator the energy deviation stays below 5e-3 and the
   late-time error envelope does not exceed the early-time envelope — no
   secular drift.
3. **Symplecticity (measured).** The numerical Jacobian of one step of
   either method on the pendulum has unit determinant to 1e-7.
4. **Time reversibility (measured).** Verlet forward, momentum flip, Verlet
   forward, momentum flip returns the pendulum to its initial state to 1e-9.
5. **Rejection (proven).** Non-separable (`H = qp`), time-dependent, and
   unresolved-parameter Hamiltonians raise; unknown method names and
   mismatched position/momentum dimensions raise.

## Verification commands

```sh
pytest tests/test_symplectic_integrators.py -q
pytest -q
```

No generator or viewer commands: nothing crosses the manifest boundary.

## Out of scope

Everything listed under "Deferred" above, plus manifest/export schema changes
and frontend surfaces.

## Verification record

Implemented and verified 2026-06-12: `pytest -q` green including
`tests/test_symplectic_integrators.py` (see `docs/BACKEND.md` baseline for
the current count).
