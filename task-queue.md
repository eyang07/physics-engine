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

1. **FE-035: Draw the certified enclosure box on the phase-plane stage**
   - Goal: An obligation's certified-numeric enclosure (FE-032) records the box it
     is sound over in state-variable coordinates, but the stage never shows where
     on the phase plane that box lies. Draw a read-only certified-box overlay on
     the (q1, v1) stage for obligations whose enclosure box is plane-expressible,
     so a reader can see the region the obligation was certified sound over. Draw
     nothing for obligations with no certified enclosure or a non-plane box.
     Honest — "sound over this box under this model", never "safe".
   - Scope: `viewer/src/verificationStage.ts` (certified-box overlay),
     `viewer/src/data/verification.ts` if the box needs exposure to the stage,
     `viewer/src/styles.css`, and the viewer visual test.
   - Acceptance: a package with a plane-expressible certified box shows the box
     overlay on the stage; a package with no certified enclosure shows none; the
     rollout/region rendering is otherwise unchanged; nothing reads as proved;
     `npm run build` and the visual test pass.

2. **FE-036: Surface certified-numeric coverage in the catalog (after a discovery-index certified count)**
   - Goal: The catalog lists every package's region/obligation/candidate counts
     and Tier/regime, but not how many of its obligations reach level 2. Once the
     discovery index carries a per-package certified-numeric count, surface it as
     an honest catalog readout (e.g. "2/4 certified-numeric") so a reader can tell
     which packages climb the rigor ladder without opening them. Read only the
     index count; certified-numeric is a sound enclosure, never proved or safe.
   - Scope: `viewer/src/data/verification.ts` (read the certified count from the
     discovery index), `viewer/src/main.ts` (catalog readout), `viewer/src/
     styles.css`, and the viewer visual test.
   - Acceptance: each catalog entry shows its certified-numeric coverage from the
     index; entries without the count show none; nothing reads as proved;
     `npm run build` and the visual test pass.

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

1. **BE-079: Cross-check reachability handoff coverage against certified coverage**
    - Goal: Ensure the reachability handoff inventory stays aligned with the
      certified-status coverage report: every handoff-backed obligation is a real
      certified-numeric obligation, and missing handoffs are reported rather than
      silently ignored.
    - Scope: `engine/export/verification_package.py`,
      `engine/verification/reachability.py`, and `tests/`.
    - Acceptance: a backend validator reports certified obligations with and without
      reachability handoffs; it rejects a handoff for a non-certified obligation; no
      report claims proof or external discharge; focused tests pass.

2. **BE-080: Add a reachability handoff dependency index**
    - Goal: Make each package's reachability handoff prerequisites inspectable
      without opening every artifact, by publishing a deterministic dependency
      index that maps handoffs to obligation ids, enclosure status ids, assumption
      ids, and domain-constraint counts.
    - Scope: `engine/verification/reachability.py`,
      `engine/export/verification_package.py`, and `tests/`.
    - Acceptance: the reachability index lists each artifact's obligation id,
      enclosure status id, obligation assumption ids, domain-constraint count,
      `discharges=false`, and `externalStatus="external-required"`; package
      readback validates the dependency index against the artifacts and IR; no
      entry claims proof, certification, or discharge; focused tests pass.
