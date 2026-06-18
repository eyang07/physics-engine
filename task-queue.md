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

1. **FE-022: Surface the package component inventory in the IR inspector**
   - Goal: The header now downloads the BE-039 bundle, but a reader can only see
     its components as a one-line tooltip. Add a read-only package section to the
     collapsible IR details that lists the manifest's model, status, and counts
     and each indexed component (kind, filename, description), so the bundle's
     contents are inspectable without downloading. Render only what the manifest
     exports and keep the rigor honest — the bundle gathers measured/candidate
     parts and discharges nothing.
   - Scope: `viewer/src/verificationPanel.ts` (a package detail section fed the
     loaded manifest), `viewer/src/styles.css`, and the viewer visual test.
   - Acceptance: selecting a problem with a published package shows its component
     inventory in the IR details (each component's kind and filename, plus the
     manifest model/status/counts); a problem without a package shows no package
     section; nothing reads as proved; `npm run build` and the visual test pass.

2. **FE-023: Distinguish disturbance-robust obligations in the obligation ledger**
   - Goal: Five drone packages are now Tier-3 disturbance-robust (BE-049/051/052),
     but the obligation ledger renders a robust forward-invariance obligation
     (quantified over the wind box `W`, with the worst-case `dt^2/2*w` term baked
     in) identically to a nominal one. Add an honest "robust (∀ disturbance ∈ W)"
     badge to obligations whose IR carries a disturbance bound / set-valued
     successor, and surface the disturbance bound the obligation cites. Read it
     only from data already in the IR; a robust obligation is still
     external-required, never discharged.
   - Scope: `viewer/src/verificationPanel.ts` (ledger obligation card), the IR
     reader in `viewer/src/data/verification.ts` if the disturbance descriptor
     needs exposure, `viewer/src/styles.css`, and the viewer visual test.
   - Acceptance: selecting a Tier-3 package shows the robust badge and cited
     disturbance bound on its robust obligations; nominal (Tier-1/2) packages show
     no such badge; obligations stay `external-required`; nothing reads as proved;
     `npm run build` and the visual test pass.

3. **FE-024: Annotate the disturbance set on Tier-3 stages**
   - Goal: A Tier-3 stage renders the rollout and regions, but the wind box `W =
     [-w, w]` the robust obligation is quantified over is invisible. Add an honest,
     read-only annotation of the disturbance bound `w` (and, where plane-expressible,
     its effect on the tightened safe margin) to the stage for packages that carry
     a disturbance spec, so a reader can see what the robustness is *against*. Draw
     nothing for nominal packages.
   - Scope: `viewer/src/verificationStage.ts` (disturbance annotation), the IR
     reader in `viewer/src/data/verification.ts` if needed, `viewer/src/styles.css`,
     and the viewer visual test.
   - Acceptance: selecting a Tier-3 package shows the disturbance-bound annotation;
     a nominal package shows none; the rollout/region rendering is unchanged;
     nothing reads as proved; `npm run build` and the visual test pass.

4. **FE-025: Surface adapter-stub descriptors in the IR inspector**
   - Goal: Each package now carries optional non-discharging adapter stubs (BE-044)
     naming external backend categories (reachability, SOS/certificate synthesis,
     deductive prover) that could consume each obligation, but the viewer never
     shows them. Add a read-only adapter-stub section to the IR details listing,
     per obligation, the applicable categories and the obligation shape each would
     have to handle — every entry labeled `discharges: false`. Render only what the
     stubs component exports.
   - Scope: `viewer/src/verificationPanel.ts` (adapter-stub detail section),
     `viewer/src/data/verification.ts` if the stubs need exposure,
     `viewer/src/styles.css`, and the viewer visual test.
   - Acceptance: a package with adapter stubs shows them in the IR details, each
     marked non-discharging with its category and target; a package without stubs
     shows no section; obligations stay `external-required`; `npm run build` and the
     visual test pass.

5. **FE-026: Per-obligation worst-margin readout aligned to the rollout**
   - Goal: Certificate lanes plot candidate values over the rollout, but the
     measured signed worst `margin` (BE-036) per obligation is shown only as a
     static ledger number. Add a small, honest worst-margin readout for the
     selected obligation, aligned to the rollout timeline, so the closest approach
     to the boundary is legible in time as well as value. Measured stays measured.
   - Scope: `viewer/src/certificateLanes.ts` (margin readout), `viewer/src/data/
     verification.ts` if the per-obligation worst record needs exposure,
     `viewer/src/styles.css`, and the viewer visual test.
   - Acceptance: selecting an obligation shows its worst sampled margin aligned to
     the rollout, consistent with the ledger value; nothing recomputes physics in
     TypeScript; nothing reads as proved; `npm run build` and the visual test pass.

6. **FE-027: Label each barrier lane for intersection-safe-set packages**
   - Goal: The geofence∩obstacle package (BE-050) carries two candidate barriers
     together — the geofence box barrier and the signed-distance keep-out barrier
     `B_obs = rho - |q - c|` — but the certificate lanes do not name which lane is
     which or that safety is their intersection `{max(B_geo, B_obs) <= 0}`. Label
     each lane by its barrier and surface the intersection semantics honestly, so a
     reader can tell the box barrier from the keep-out barrier. Both stay
     candidates.
   - Scope: `viewer/src/certificateLanes.ts` (lane labeling), the IR reader if
     barrier identity needs exposure, `viewer/src/styles.css`, and the viewer
     visual test.
   - Acceptance: the intersection package shows each barrier lane named and the
     intersection semantics stated; single-barrier packages are unchanged; both
     barriers stay labeled candidate; `npm run build` and the visual test pass.

7. **FE-028: Verification catalog overview from the package discovery index**
   - Goal: The Verification view wires examples one by one, but the published
     discovery index (`packages.index.json`, surfaced on the viewer index by
     BE-047) already lists every package by model, status, and counts. Add a
     read-only catalog overview that lists all packages from the index — model,
     status, region/obligation/candidate counts — as a grounded package picker,
     rather than re-deriving the list per example. Render only what the index
     exports.
   - Scope: `viewer/src/verificationPanel.ts` or `viewer/src/home.ts` (catalog
     overview), `viewer/src/data/verification.ts` (read the published index),
     `viewer/src/styles.css`, and the viewer visual test.
   - Acceptance: the catalog lists every indexed package with its model/status/
     counts and selecting one opens its problem; a missing index degrades to the
     existing per-example list; nothing reads as proved; `npm run build` and the
     visual test pass.

8. **FE-029: Show the package Tier/regime badge in the catalog (after BE-054)**
   - Goal: Once the discovery index carries the Tier/regime descriptor (BE-054 —
     nominal Tier-1/2 vs disturbance-robust Tier-3), surface it as an honest badge
     on each catalog entry so a reader can tell a nominal geofence package from a
     disturbance-robust one without opening it. Read only the index descriptor;
     claim nothing beyond the rigor of the listed package.
   - Scope: `viewer/src/verificationPanel.ts` or `viewer/src/home.ts` (catalog
     badge, builds on FE-028), `viewer/src/data/verification.ts`,
     `viewer/src/styles.css`, and the viewer visual test.
   - Acceptance: each catalog entry shows its Tier/regime badge matching the index
     descriptor; entries without the descriptor show no badge; nothing reads as
     proved; `npm run build` and the visual test pass.

9. **FE-030: Render the measured violation reference scenario (after BE-056)**
    - Goal: Every published package currently *holds*, so the viewer's measured
      violation surface (red worst-violation markers and legend) is never
      exercised. Once the Tier-2 boundary-corner violation scenario exports
      (BE-056) — a second trajectory with measured `proofStatuses` carrying a
      negative signed margin — render it: emphasize the negative-margin violation
      markers and name the obligation that the run left, making the honest "this
      simulated run entered the unsafe set" state concrete on the rigor ladder.
    - Scope: `viewer/src/verificationStage.ts` (violation emphasis for the new
      scenario), `viewer/src/data/verification.ts` if scenario selection needs
      exposure, `viewer/src/styles.css`, and the viewer visual test.
    - Acceptance: the violation scenario shows its measured violation markers and
      named obligation with a negative margin, visually distinct from a holding
      run; holding packages are unchanged; the violation is labeled measured
      evidence, never a disproof of safety; `npm run build` and the visual test
      pass.

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
