# Task Queue

This file is the shared implementation queue for coding agents working in this
repository. Tasks are ranked in the order they should be attempted, with the
most immediately implementable task first in each section.

## Agent Workflow

- Pick exactly one task from either the frontend or backend queue.
- Before editing, verify that the task still matches the current repository
  state and does not duplicate uncommitted work.
- Keep the Python-to-TypeScript boundary intact: Python computes and exports;
  TypeScript renders generated data.
- When the task is complete, remove it from this queue in the same change.
- If either queue has fewer than two tasks after removal, add coherent next
  tasks for that side before finishing. Keep new tasks ordered by
  implementation readiness.
- Do not add tasks for generated data under `data/generated/` or
  `viewer/public/data/*.json`.

## Task Format

Each task should use this structure:

```md
1. **TASK-ID: Short imperative title**
   - Goal: One sentence describing the outcome.
   - Scope: Main files or modules expected to change.
   - Acceptance: Concrete checks, tests, or visible behavior that prove the task
     is done.
```

## Frontend Queue

_The backend package contract is stable (BE-043) and the flagship drone renders
correctly in the Verification view (FE-019 done): the catalog lists it, its
`(q1, v1)` phase plane animates, all three barrier lanes draw (the inner-set value
coasting positive as the rollout leaves `S_in`, shown honestly), and the
four-obligation ledger surfaces each obligation's signed `margin` (BE-036) and the
assumption region its evidence was sampled within (BE-042/BE-043). The viewer now
also publishes and renders the BE-039 package bundle (FE-020 done): each problem's
`package.json` manifest is fetched and the header offers a self-contained bundle
download — manifest + components — distinct from the IR download and claiming no
discharge. The view renders the rigor ladder, obligation/assumption cards, the
verdict ledger, certificate lanes, and both export paths generically. The tasks
below make the measured margin geometrically legible and surface the package
inventory in the inspector. Keep rendering honest — measured stays measured,
candidates stay candidates, nothing reads as proved._

1. **FE-034: Surface the adapter-stub backend categories overview**
   - Goal: The adapter-stub section (FE-025) lists, per obligation, the external
     categories that could consume it, but the categories' own descriptors — each
     category's summary and what it `consumes` / `produces` — are exported in the
     stubs component yet only surfaced as a one-line tooltip. Add a read-only
     "backend categories" overview to the adapter-stub section listing each
     category once (reachability, SOS/certificate synthesis, deductive prover)
     with its summary and consumes/produces, every entry labeled non-discharging.
     Render only what the stubs component exports.
   - Scope: `viewer/src/verificationPanel.ts` (categories overview within the
     adapter-stub section), `viewer/src/styles.css`, and the viewer visual test.
   - Acceptance: a package with adapter stubs shows the backend categories with
     their summary and consumes/produces, each marked non-discharging; a package
     without stubs shows no section; obligations stay `external-required`; nothing
     reads as proved; `npm run build` and the visual test pass.

2. **FE-032: Surface the certified-numeric (level-2) status on the rigor ladder (after BE-074)**
   - Goal: The dossier rigor ladder currently pins every problem at level 1
     (measured), because the viewer export carries no level-2 status. Once the
     backend exports the `certified-numeric` per-obligation status into the
     viewer data (BE-074), surface it honestly: mark each certified obligation at
     rigor level 2 (a sound enclosure under stated assumptions) distinctly from
     measured-only and external-required, and reflect the highest established
     rung on the certification scale. A certified-numeric status is "sound over
     this box under this model", never "safe" — keep the levels strictly
     distinct and nothing reading as proved.
   - Scope: `viewer/src/verificationPanel.ts` (rigor ladder + obligation ledger),
     `viewer/src/data/verification.ts` (read the certified status), `viewer/src/
     styles.css`, and the viewer visual test.
   - Acceptance: an obligation exporting a certified-numeric status shows level-2
     rigor distinct from measured and external; the certification scale reflects
     the highest established rung; problems without any certified status are
     unchanged at level 1; nothing reads as proved; `npm run build` and the
     visual test pass.

## Backend Queue

_Direction (VISION §7, §11): the flagship drone is now routed end-to-end at **rigor
level 1 (measured)**, and the nominal/robust × single/intersection matrix is
complete — twelve verification packages (Tier-1 geofence horizontal + vertical,
P1 + P2; Tier-2 obstacle keep-out; the geofence∩obstacle intersection; the
measured-violation and boundary-margin scenarios; and the Tier-3 disturbance-robust
variants through the robust-intersection capstone), all carried by the BE-039
package contract, the BE-045 discovery index with BE-054 regime metadata, BE-060
robustness-aware adapter stubs, the BE-057 consistency validator, and the BE-061
cross-package summary. Depth on this one flagship still outranks breadth; the engine
must not become drone-specific elsewhere either._

_**The next direction — climb the rigor ladder (level 1 → level 2).** Every
obligation today is checked by *sampling* (a clean grid is evidence between samples,
never a bound). This pathway makes **rigor level 2 (certified numerical bounds)**
real for the flagship: sound *enclosures* of each one-step obligation over its
stated assumption box, making the IR's `reachability` adapter category concrete
instead of a stub. The engine still proposes; it does not prove — a certified
enclosure is "sound over this box under this model," never "safe."_

_**Soundness plan (how level-2 claims stay honest):**_
_- **Exact-rational interval arithmetic (sound by exactness)** for the polynomial
  obligations. The drone's exact zero-order-hold map and `DroneParams` are rational,
  so the geofence / velocity / inner-set / intersection / Tier-3 worst-case forms are
  polynomials over `sympy.Rational`; interval arithmetic on rationals has **no
  rounding at all**, so the enclosure property holds by construction. This covers
  most of the family._
_- **mpmath outward-rounded intervals only where irrationals appear** — the keep-out
  distance `sqrt(...)` and the planar `sqrt(2)` factor. mpmath (already a SymPy
  dependency) gives sound `sqrt` enclosures; the trusted-irrational surface is two
  nodes. No hand-rolled directed-rounding floats — the credibility-critical failure
  mode is avoided._
_- **Fail-closed lowering.** A whitelist of IR expression nodes
  (Add / Mul / Pow[int] / Rational / Abs / Max / Min / sqrt) with proven-enclosing
  handlers (including the even-power-straddling-zero case); anything else raises
  rather than returning a possibly-unsound number._
_- **Containment property-test suite — the backstop.** Sample points inside each
  box, evaluate in exact reference arithmetic, assert every value lies inside the
  computed enclosure. The lane lives or dies on this suite._
_- **Tag gated on the trusted path; soundness ≠ tightness.** A `certified-numeric`
  status is emitted only by the sound evaluator; a too-loose enclosure stays
  `measured` / `external-required` (an honest "not certified"), never a false
  verdict. Tightening (branch partitioning, affine forms) improves tightness only and
  can never affect soundness._

_Keep generated data uncommitted. `certified-numeric` is rigor level 2 (a sound
enclosure under stated assumptions), strictly distinct from `measured` (level 1) and
from any external `proved` / `certified` result. The engine proposes; external
backends dispose._

1. **BE-071: Robust set-valued enclosure over the disturbance box (Tier-3)**
   - Goal: Certify the Tier-3 robust obligations by enclosing the worst case over the
     disturbance box `W` (carrying `w` as an interval parameter), so the robust
     forward-invariance / avoidance claims gain level-2 status quantified over every
     admissible disturbance.
   - Scope: `scripts/export_verification_problems.py` (attach to the disturbed
     packages), and `tests/`.
   - Acceptance: the Tier-3 packages carry certified-numeric robust statuses whose
     enclosures cover every disturbance in `W` (verified by sampling `w`); they stay
     measured-only where the enclosure does not close; generated data stays
     uncommitted; focused tests pass.

2. **BE-072: Certified keep-out avoidance via the mpmath sqrt path**
    - Goal: Certify the obstacle keep-out / intersection avoidance obligations — the
      `sqrt`-bearing distance barrier — exercising the mpmath enclosure layer, so the
      Tier-2 and intersection packages reach level 2.
    - Scope: `scripts/export_verification_problems.py` (attach to keep-out +
      intersection packages), and `tests/`.
    - Acceptance: the keep-out and geofence∩obstacle packages carry certified-numeric
      avoidance statuses whose enclosures (`sqrt` via mpmath, argument exact) satisfy
      the obligation over the standoff / interior box; measured statuses unchanged;
      nothing claims proof; generated data stays uncommitted; focused tests pass.

3. **BE-073: Affine-form refinement for the distance barrier**
    - Goal: Add an affine / Taylor-model enclosure form to tighten the `sqrt` distance
      barrier where pure intervals over-inflate (tightness only; soundness from the
      same trusted base), closing avoidance obligations the box form cannot.
    - Scope: `engine/numerics/intervals.py` or `engine/verification/` (affine form),
      and `tests/`.
    - Acceptance: the affine enclosure is tighter than the interval-box enclosure on
      the keep-out obligation while still containing every sampled value; a
      previously-too-loose avoidance obligation certifies; soundness tests pass;
      nothing claims proof.

4. **BE-074: Surface the certified level-2 status across the summary and rigor ladder**
    - Goal: Make the certified-numeric tier legible — extend the BE-061 cross-package
      summary and the package rigor ladder to report, per obligation, certified-numeric
      vs measured-only vs external-required, keeping the three rigor levels strictly
      distinct and nothing reading as proof.
    - Scope: `engine/export/verification_package.py` (summary + per-package certified
      counts), and `tests/`.
    - Acceptance: the summary reports each package's certified-numeric / measured-only
      / external counts (and worst certified margin alongside the measured one);
      certified is visually and structurally distinct from measured and from proved;
      the report stays deterministic; generated data stays uncommitted; focused tests
      pass.

5. **BE-075: Cross-package certified-status validator**
    - Goal: Validate, across the whole drone family, which obligations close at level 2
      and that every certified status is internally consistent (its enclosure satisfies
      the recorded verdict over the recorded box and its assumptions are recorded),
      failing loudly on a fabricated or inconsistent certified status.
    - Scope: `engine/verification/` or `engine/export/verification_package.py`, and
      `tests/`.
    - Acceptance: a validator re-checks that every published certified-numeric status'
      enclosure actually satisfies its obligation over the recorded box and rejects a
      tampered one; it reports the family-wide certified coverage; nothing claims
      proof; focused tests pass.

6. **BE-076: Real `reachability` export adapter (non-discharging handoff)**
    - Goal: Replace the reachability adapter *stub* with a concrete artifact — write
      each one-step obligation as an enclosure / reachability problem an external
      validated-numerics tool could consume, closing the IR's "optional backend
      adapter" loop without the engine discharging anything.
    - Scope: `engine/verification/` (reachability export adapter),
      `engine/export/verification_package.py` (optional package component), and
      `tests/`.
    - Acceptance: the adapter writes a deterministic, re-readable reachability problem
      file per obligation (dynamics, box, obligation), labeled non-discharging; no
      external result is fabricated; obligations stay external-required until a backend
      actually returns one; generated data stays uncommitted; focused tests pass.
