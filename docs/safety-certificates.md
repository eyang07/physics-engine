# Safety / Certificate Metadata — Design Spec (v0)

Advances `docs/VISION.md` §11 priority 2, building on the controlled-dynamics
layer (`docs/controlled-dynamics.md`). Status: **implemented** (see
Verification at the bottom).

## Goal

Represent safe/unsafe sets, obstacles, and *candidate* barrier / Lyapunov
certificates as structured backend data, together with the proof obligations
an external sound method would have to discharge. The engine **proposes and
measures; it never certifies**: every check the engine itself can run is
rigor level 1 (sampled / simulation-supported) or a symbolic identity, and
results are labeled accordingly. Backend-only: no manifest, gallery, or
viewer change.

## Design decisions

1. **Sets are sublevel sets.** v0 represents regions as
   `SublevelSet = {x : g(x) <= level}` over the state symbols. Boxes, balls,
   half-spaces, and corridors are all expression choices. The signed quantity
   `margin(x) = level - g(x)` (nonnegative inside) is the single numeric
   interface; obstacles are unsafe sets and need no separate type.
2. **A safety specification is data, not behavior.** `SafetySpecification`
   bundles one safe set, zero or more unsafe sets, and an optional initial
   set over a shared state tuple. Its only computation is a *measured*
   trajectory report (worst safe margin, per-unsafe-set first entry).
3. **Certificate candidates carry their own proof obligations.**
   `LyapunovCandidate` (V, equilibrium, optional domain) and
   `BarrierCandidate` (B, candidate-invariant region `{B <= 0}`) generate
   `ProofObligation` records — canonical statements
   `expression <comparison> 0 on region` — via Lie derivatives along a given
   closed-loop `FirstOrderSystem`. Obligations are structured data plus
   sampling evidence, and `engine.verification` serializes them into the
   backend-agnostic verification-problem IR.
4. **Sampling is deterministic and honestly labeled.** `grid_points` builds
   deterministic grids (no RNG); `sample_obligation` evaluates an obligation
   on points, restricted to its region, and returns an `ObligationSample`
   with `rigor="measured"`, the worst value and worst point, and an explicit
   note that a clean sample is *not* a certificate. A found violation, by
   contrast, *is* a genuine counterexample.
5. **Conventions.** Barrier convention: the candidate-safe/invariant region
   is `{B <= 0}`; obligations are `B <= 0` on the initial set, `B > 0` on
   each unsafe set, and `dB/dt <= 0` on `{B <= 0}` (a sufficient,
   stronger-than-boundary condition; noted in the docstring). Lyapunov
   obligations: `V = 0` at the equilibrium (symbolic identity), `V > 0` on
   the domain excluding the equilibrium, `dV/dt <= 0` on the domain.
   Invariant-set candidates are expressed in v0 as the sublevel form of
   `BarrierCandidate`.
6. **Deferred (out of v0):** SOS/LP certificate synthesis, validated-numeric
   checks (rigor level 2), external proof discharge, control barrier functions
   with class-K margins, time-varying sets, manifest export of safety geometry,
   and any viewer rendering.

## Files

- `engine/dynamics/safety.py` — `SublevelSet`, `SafetySpecification`,
  `TrajectorySafetyReport` / `UnsafeSetReport`, `ProofObligation`,
  `ObligationSample`, `LyapunovCandidate`, `BarrierCandidate`,
  `lie_derivative`, `grid_points`, `sample_obligation`.
- `tests/test_safety_certificates.py` — obligations below.
- `engine/dynamics/__init__.py` — exports.
- `engine/verification/` — backend-agnostic verification-problem IR and
  safety adapter for serializing proof obligations without proof results
  (spec in `docs/verification-ir.md`).
- `tests/test_verification_ir.py` — IR serialization and adapter checks.
- Doc updates: `README.md`, `docs/BACKEND.md`, `docs/VISION.md` §11 item
  statuses, and test-count baselines.

## Invariants / proof obligations (for this implementation)

1. **Margins (proven on examples).** `SublevelSet.margin` is `level - g(x)`,
   positive inside, negative outside, zero on the boundary, for ball and
   corridor examples.
2. **Lie derivative (proven).** `lie_derivative(V, system)` equals
   `dV/dt + grad(V) . f` symbolically; for the damped oscillator
   `x' = v, v' = -k x - c v` with `V = (k x^2 + v^2)/2` it simplifies to
   `-c v^2`.
3. **Lyapunov candidate (proven + measured).** For that oscillator the
   equilibrium-value obligation holds symbolically; sampling the decrease
   and positivity obligations on a grid that includes the origin finds no
   violation (origin excluded from the strict obligation); flipping the
   damping sign yields a counterexample with the violating point reported.
4. **Barrier candidate (measured).** For the PD-stabilized upright pendulum
   and corridor barrier `B = (theta - pi)^2 - 0.25`: unsafe-exclusion and
   non-increase obligations sampled on deterministic grids behave as
   measured in the implementation run; the rollout's trajectory report shows
   a positive worst-case safe margin and no unsafe-set entry, and a
   deliberately tight corridor reports first entry at `t = 0`.
5. **Honest labeling (proven by construction).** Every `ObligationSample`
   and `TrajectorySafetyReport` carries `rigor="measured"`; a satisfied
   sample's note states it is not a certificate. Nothing in this module can
   emit "certified" or "proved".
6. **Determinism (measured).** `grid_points` and repeated samples are
   bit-identical.

## Verification commands

```sh
pytest tests/test_safety_certificates.py tests/test_verification_ir.py -q
pytest -q
```

No generator or viewer commands: nothing crosses the manifest boundary.

## Out of scope

Everything listed under "Deferred" in the design decisions, plus any change
to the manifest/export schema and any frontend surface.

## Verification record

Implemented and verified 2026-06-12: `pytest -q` green including
`tests/test_safety_certificates.py` and `tests/test_verification_ir.py` (see
`docs/BACKEND.md` baseline for the current count). Obligations above hold with
the tolerances encoded in the tests; IR serialization records obligations for
external discharge without proof results.
