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

1. **FE-032: Surface the certified-numeric (level-2) status on the rigor ladder (after BE-074)**
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

1. **BE-077: Validate reachability adapter artifacts in package reads**
    - Goal: Once BE-076 writes non-discharging reachability handoff files, make package
      reads validate that every reachability artifact references a real obligation,
      matches the problem dynamics/box contract, and is labeled non-discharging.
    - Scope: `engine/export/verification_package.py`, `engine/verification/`
      reachability artifact readers, and `tests/`.
    - Acceptance: package reads reject a tampered reachability artifact or one that
      claims discharge; valid generated packages round-trip; obligations remain
      `external-required`; focused tests pass.

2. **BE-078: Summarize reachability handoff coverage in package reports**
    - Goal: Surface how many non-discharging reachability handoff artifacts each
      generated package exports, so the backend inventory shows which obligations
      have concrete handoff files without implying discharge.
    - Scope: `engine/export/verification_package.py` (package summary/index metadata
      if needed), `engine/verification/reachability.py`, and `tests/`.
    - Acceptance: the package summary or a deterministic companion report lists
      reachability handoff counts per package; missing/empty handoff inventories are
      represented honestly; no entry claims proof or certification; focused tests pass.
