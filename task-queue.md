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

1. **FE-021: Mark the tightest measured-holds margin on the phase-plane stage**
   - Goal: The stage marks measured **violations** on the `(q1, v1)` plane, but a
     measured-holds status also exports its worst sampled point, projection, and
     signed `margin` (BE-036) — the closest the evidence came to the obligation
     boundary. Surface that closest-approach point for holding obligations (the
     drone's four obligations all hold within their assumption regions, so today
     the plane shows no margin annotation at all), drawn distinctly from a
     violation marker and labeled as measured slack, so the ledger's signed margin
     is also legible geometrically. Keep it honest: a tight hold is still measured
     evidence, never a discharge.
   - Scope: `viewer/src/verificationStage.ts` (a holds-margin marker beside the
     existing violation markers), `viewer/src/data/verification.ts` if the worst
     point/margin needs wider exposure, and the viewer visual test.
   - Acceptance: selecting the drone shows a closest-approach marker for its
     holding obligations, visually distinct from violation markers and labeled
     measured, with the violation path unchanged; the rigor labeling stays honest;
     `npm run build` and the visual test pass.

2. **FE-022: Surface the package component inventory in the IR inspector**
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

## Backend Queue

_Direction (VISION §11): stop expanding the IR in the abstract. The whole queue
now drives **one flagship controlled system end-to-end** — backend model →
verification package → (later) frontend. The package contract exists (BE-039) and
the case studies carry per-obligation assumptions (BE-034). The flagship model has
arrived (`DRONE_MODEL_SPEC.md`): a **guard-band feedback-controlled, geofenced
point-mass drone**, whose canonical model is a **discrete** exact zero-order-hold
map with a per-axis piecewise (Piecewise) controller and a **box / forward-
invariance barrier** certificate — not Lyapunov (there is no equilibrium). BE-040
is done (`systems/drone_point_mass.py`: the Tier-1 discrete plant, guard-band law,
and a safe rollout). Route **Tier-1 geofence (P1) + velocity bound (P2)** first;
Tier-2 obstacle (P4) and Tier-3 disturbance come later. Keep generated data
uncommitted. Never label anything proved/certified — the engine proposes; external
backends dispose._

BE-041 is done: the Tier-1 **drone geofence problem** (`drone_geofence_problem`,
the decoupled `(q1, v1)` horizontal axis) is published to the viewer with the
geofence safe/inner regions, `(q1, v1)` geometry, the box-barrier candidate, the
honest forward-invariance + initial-containment obligations (the box barrier's
non-increase condition is false, so it is not used), and a discrete
candidate-value certificate series (`measured.py` now supports discrete dynamics).

BE-036 is done: region-grid `proofStatuses` now carry a numeric signed worst
`margin` to the obligation boundary (nonnegative when the sampled check holds,
negative when violated), the IR round-trips it, and the export contract validates
the optional `worst` record (value/point/time/margin), rejecting malformed shapes.

BE-042 is done: the drone now exports measured `proofStatuses` for both
obligations. `sampled_region_proof_statuses` gained an opt-in
`restrict_to_assumption_regions` flag that samples each obligation only where its
plane-expressible domain assumptions hold; the drone uses it so forward-invariance
is measured inside `speedBound` (where one guard-band step holds the geofence,
margin >= 0) instead of over all velocities (where it overshoots). Both statuses
carry BE-036 margins at rigor `measured`; pendulum/spring sampling is unchanged.

BE-043 is done: the drone is now a complete flagship verification package.
`drone_geofence_problem` carries the full spec-G assumption set (`speedBound`,
`velBound`, `dtSmall`, `driftBound`) and the three Tier-1 barrier candidates with
their one-step invariance obligations — geofence P1 forward-invariance (+ initial
containment), velocity P2 self-reproducing bound, and S_in inner-set invariance —
each obligation citing the assumptions it needs and measured-holding within its
stated region. `generate_verification_problems` now also writes one BE-039
package per example (`--package-dir`, default `data/generated/verification/
packages`, ignored); the drone package re-reads in Python with manifest,
discrete dynamics, assumptions, safe set, three candidates, four obligations,
per-obligation measured `proofStatuses`, three candidate-value series, and full
`(q1, v1)` geometry. Nothing claims proof/certification.

1. **BE-044: Backend adapter stubs in the verification package**
   - Goal: Include optional adapter-stub descriptors in the package describing how
     external backend *categories* (reachability, SOS/certificate synthesis,
     deductive prover) would consume each obligation — descriptors of target and
     required shape only, no discharge, preserving the tool-agnostic posture.
   - Scope: `engine/verification/` (adapter-stub descriptors alongside the
     existing capability/target-requirement modules), the package writer in
     `engine/export/verification_package.py`, and `tests/`.
   - Acceptance: the drone package lists adapter stubs naming a target backend
     category and the obligation shape it would need, all honestly
     non-discharging; the export contract validates; focused tests pass.

2. **BE-045: Verification-package discovery index**
   - Goal: Write a deterministic discovery index alongside the generated packages
     (mirroring the inspection-artifact and viewer indexes) so external tools and
     the viewer can enumerate every package without walking the directory tree —
     one entry per package naming its `package.json` path, model, status, and
     component/obligation counts. Pure cataloging; it claims nothing beyond the
     rigor of the packages it lists.
   - Scope: `engine/export/verification_package.py` (an index builder/validator
     beside the manifest), `scripts/generate_verification_problems.py` (write the
     index next to the packages), and `tests/`.
   - Acceptance: package generation also writes a contract-valid index that
     re-reads in Python and references every written package's manifest; the index
     round-trips; generated data stays uncommitted; focused tests pass.

3. **BE-046: Vertical altitude-axis (q3, v3) Tier-1 geofence package**
   - Goal: Add the decoupled vertical altitude axis as a second flagship package,
     reusing the BE-043 structure but exercising the asymmetric vertical regime —
     gravity, hover thrust, floor/ceiling guard bands, and the `[u3Min, u3Max]`
     thrust box — with the P1 floor/ceiling invariance and P2 vertical velocity
     bound (spec E `B3`) obligations under the corresponding spec-G assumptions.
   - Scope: `systems/drone_point_mass.py` (a `vertical_axis_*` sub-dynamics
     mirror of the horizontal axis), `scripts/export_verification_problems.py`,
     and `tests/`.
   - Acceptance: generation publishes a complete, contract-valid vertical-axis
     package with measured `proofStatuses`, rendering on the `(q3, v3)` plane;
     nothing claims proof/certification; generated data stays uncommitted; focused
     tests pass.
