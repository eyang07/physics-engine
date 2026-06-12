# Candidate Generation — Design Spec (v0)

Advances `docs/VISION.md` §11 priority 2 ("the engine proposes") on top of the
safety/certificate layer (`docs/safety-certificates.md`). Status:
**implemented** (see Verification record at the bottom).

## Goal

Generate certificate *candidates* from standard constructions instead of
requiring every candidate to be hand-written. Generation changes nothing
about rigor: every output is a `LyapunovCandidate` or `BarrierCandidate`
carrying the same proof obligations as a hand-written one, and every numeric
suggestion is labeled `rigor="measured"`. Backend-only: no manifest, gallery,
or viewer change.

## Design decisions

1. **Quadratic Lyapunov candidates come from the Lyapunov equation.**
   `quadratic_lyapunov_from_linearization` solves `A^T P + P A = -Q`
   (SciPy `solve_continuous_lyapunov`) at a numeric equilibrium of the
   (closed-loop) system and proposes `V = (x - x*)^T P (x - x*)`.
2. **Unjustified constructions raise instead of proposing garbage.** The
   generator rejects points that are not equilibria (residual above
   tolerance), linearizations with unresolved symbols (substitutions are
   required for symbolic parameters), non-Hurwitz linearizations (max
   eigenvalue real part `>= 0`), invalid `Q` (must be symmetric positive
   definite), and a numerically non-positive-definite solved `P`.
3. **Generated candidates are ordinary candidates.** The result is a plain
   `LyapunovCandidate`; its obligations quantify over the full domain and
   still require external discharge. Being exact for the linearization
   guarantees nothing about the nonlinear system away from the equilibrium.
4. **Sublevel barriers reuse the Lyapunov-sublevel construction.**
   `barrier_from_lyapunov(candidate, level)` proposes `B = V - level` with
   candidate-invariant region `{V <= level}`; `level` must be positive so
   the region contains the equilibrium.
5. **Level suggestions are measured, not bounds.**
   `measured_infimum_over_set` returns the deterministic grid minimum of a
   function over a `SublevelSet` as a `MeasuredInfimum` whose `rigor` is
   locked to `"measured"` and whose note says the true infimum may be lower.
   Choosing a barrier level below the measured infimum of `V` over an unsafe
   set keeps the unsafe-exclusion obligation satisfied *on those samples*
   only.
6. **Deferred (out of v0):** SOS/LP synthesis, domain-size estimation
   (region-of-attraction sublevels), discrete-time constructions, control
   barrier functions, and validated-numeric level bounds.

## Files

- `engine/dynamics/candidates.py` — `quadratic_lyapunov_from_linearization`,
  `barrier_from_lyapunov`, `measured_infimum_over_set`, `MeasuredInfimum`.
- `engine/dynamics/__init__.py` — exports.
- `tests/test_candidate_generation.py` — obligations below.

## Invariants / proof obligations (for this implementation)

1. **Lyapunov equation (proven on examples).** For the linear damped
   oscillator the generated candidate satisfies `dV/dt = -x^T Q x` exactly
   (coefficient residuals below 1e-9), vanishes at the equilibrium, and its
   positivity/decrease obligations sample clean on a deterministic grid.
2. **Rejection (proven).** Non-equilibrium points, symbolic parameters
   without substitutions, non-Hurwitz linearizations, and invalid `Q` all
   raise with specific messages.
3. **Barrier construction (proven + measured).** `B = V - level` matches
   symbolically; the non-increase obligation samples clean on `{B <= 0}`.
4. **Measured labeling (proven by construction).** `MeasuredInfimum` cannot
   be constructed with any rigor other than `"measured"`.
5. **End to end (measured).** The PD-stabilized upright pendulum's generated
   quadratic candidate samples a clean decrease obligation near the
   equilibrium and exports through the verification IR with
   `kind="lyapunov"`, `status="candidate"`.

## Verification commands

```sh
pytest tests/test_candidate_generation.py -q
pytest -q
```

No generator or viewer commands: nothing crosses the manifest boundary.

## Out of scope

Everything listed under "Deferred" above, plus manifest/export schema changes
and frontend surfaces.

## Verification record

Implemented and verified 2026-06-12: `pytest -q` green including
`tests/test_candidate_generation.py` (see `docs/BACKEND.md` baseline for the
current count).
