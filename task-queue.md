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

BE-044 is done: the package now carries optional non-discharging adapter-stub
descriptors. `engine/verification/adapter_stubs.py` catalogs three external
backend *categories* (reachability, SOS/certificate synthesis, deductive prover)
and derives, per obligation, one stub per category that could consume its
classified target — naming the category, the target, and the obligation shape
(region-scoping, assumptions, ...) it would have to handle. Malformed targets
yield no applicable stub. The package writer indexes them as an optional
`adapter-stubs` component (generation enables them via `include_adapter_stubs`);
`read_package` validates the descriptors against the IR. Every stub is honestly
non-discharging (`discharges: false`) and obligations stay `external-required`.

BE-045 is done: package generation now writes a deterministic discovery index
(`packages.index.json`) beside the packages. `engine/export/verification_package.py`
gained `PackageIndexEntry`/`PackageIndex` plus `build_package_index`,
`write_package_index`, and `read_package_index`; `write_verification_packages`
writes the index alongside every package (so both the data and viewer package
trees carry it). Each entry names the package's `<id>/package.json` path, model,
status, component kinds, and region/obligation/candidate counts. `read_package_index`
re-reads the index, validates its shape, and checks every referenced manifest
exists on disk with a matching `problemId`. Pure cataloging; it claims nothing
beyond the rigor of the packages it lists.

BE-046 is done: the decoupled vertical altitude axis is a second flagship
package. `systems/drone_point_mass.py` gained `vertical_axis_*` sub-dynamics
(the `(q3, v3)` open loop carrying the gravity offset, the extracted
`_vertical_law` floor/ceiling guard band, closed loop, controller, and rollout)
plus a `vertical_reach` param property. `scripts/export_verification_problems.py`
factored the BE-043 assembly into a shared `_AxisGeofenceSpec` /
`_drone_axis_geofence_problem` builder (the horizontal problem is byte-identical)
and added `drone_vertical_geofence_problem` + its trajectory, registered as a
fourth viewer example. The published `drone-vertical-axis` package carries the
three Tier-1 barriers, the floor/ceiling P1 + vertical P2 (spec E `B3`)
obligations under the spec-G assumptions, and measured `proofStatuses` that all
hold within their assumption regions, rendering on the `(q3, v3)` plane. Nothing
claims proof/certification.

BE-047 is done: the BE-045 package discovery index is now wired into the
viewer-served verification catalog. `validate_viewer_verification_index` accepts
an optional top-level `packageIndexPath` (validated against the published
`/data/verification/packages/packages.index.json`, rejected otherwise), and
`generate_verification_problems` emits it on the viewer `index.json` while the
package writer already publishes `packages.index.json` into the viewer package
tree. Pure wiring; it claims nothing beyond the rigor of the packages it lists.

BE-048 is done: the first Tier-2 problem is published. `systems/drone_point_mass.py`
gained the coupled `horizontal_plane_*` `(q1, q2, v1, v2)` sub-dynamics (per-axis
guard-band law, pure coasting in the interior) and an `ObstacleSpec` circular
keep-out geometry. `scripts/export_verification_problems.py` added
`drone_obstacle_keepout_problem` + its trajectory, registered as a fifth viewer
example. The published `drone-obstacle-keepout` package carries the signed-distance
keep-out barrier candidate (coupling `q1`/`q2`), a worst-case one-step avoidance
obligation and an initial-containment obligation, the spec-G assumptions (planar
velocity bound left for external discharge, the standoff annulus and geofence
interior plane-sampled, plus the standoff-sizing precondition), coasting kinematics
with the planar velocity as a bounded parameter, and measured `proofStatuses` that
hold within the standoff annulus, rendering on the `(q1, q2)` plane. Nothing claims
proof/certification.

BE-049 is done: the first Tier-3 problem is published. `systems/drone_point_mass.py`
gained the disturbed `(q1, v1)` sub-dynamics (`DisturbanceSpec` carrying the wind
box `W = [-w, w]` and its authority condition `uh - w > 0`,
`horizontal_disturbed_axis_system` adding the matched additive disturbance `w1` to
the control channel, and `horizontal_disturbed_axis_closed_loop` returning the
set-valued successor map that retains `w1` as a parameter). `scripts/
export_verification_problems.py` added `drone_disturbed_geofence_problem` + its
nominal trajectory, registered as a sixth viewer example. The published
`drone-disturbed-geofence-axis` package carries the geofence barrier candidate, a
robust forward-invariance obligation whose expression bakes in the exact
worst-case-over-`W` term `B(F_nom) + dt^2/2*w` (cites the disturbance bound, the
disturbance-tightened robust speed bound, the inner-interval driftBound region, and
the robust braking margin) plus an initial-containment obligation, and measured
`proofStatuses` that hold within their assumption region with a nonnegative
worst-case signed margin. The disturbance bound `|w1| <= w` is non-plane and left
for external discharge. Nothing claims proof/certification.

1. **BE-050: Coupled obstacle + geofence keep-out on the horizontal plane**
   - Goal: The Tier-2 obstacle package (BE-048) measures avoidance only within the
     geofence interior, leaving the geofence walls to the decoupled axis problems.
     Add a single coupled `(q1, q2)` problem that carries *both* the obstacle
     keep-out barrier and the geofence box barrier together, so one package shows
     the drone staying inside the geofence and outside the obstacle under the same
     guard-band law — the first problem whose safe set is an intersection of two
     candidate regions. Keep candidates candidate and obligations external-required.
   - Scope: `scripts/export_verification_problems.py` (extend the obstacle problem
     or add a companion problem assembling the geofence box barrier alongside the
     keep-out barrier on the coupled plane, reusing the BE-048 dynamics and
     assumptions), and `tests/`.
   - Acceptance: generation publishes a complete, contract-valid coupled package
     with measured `proofStatuses` for both the geofence and keep-out obligations
     on the `(q1, q2)` plane, each holding within its assumption region; nothing
     claims proof/certification; generated data stays uncommitted; focused tests
     pass.

2. **BE-051: Tier-3 disturbance-robust vertical altitude geofence package**
   - Goal: BE-049 made the horizontal axis disturbance-robust; the asymmetric
     vertical altitude axis is still nominal. Add the Tier-3 analogue on the
     `(q3, v3)` axis: the matched additive disturbance `w3` on the vertical
     zero-order-hold step (carrying the gravity offset), with a robust
     floor/ceiling forward-invariance obligation that holds for every admissible
     `w3`. The vertical authority condition is asymmetric (`u3Max - g - w > 0` and
     `g - u3Min - w > 0`), so the disturbance-tightened guard reach differs from the
     horizontal case. Keep candidates candidate and obligations external-required.
   - Scope: `systems/drone_point_mass.py` (a disturbed `(q3, v3)` sub-dynamics
     carrying `w3` and the vertical authority condition),
     `scripts/export_verification_problems.py` (the vertical disturbance-robust
     problem and a nominal trajectory), and `tests/`.
   - Acceptance: generation publishes a complete, contract-valid vertical
     disturbance-robust package whose floor/ceiling forward-invariance obligation
     cites the disturbance bound and measures worst-case margin across the
     disturbance set, holding within its assumption region on the `(q3, v3)` plane;
     nothing claims proof/certification; generated data stays uncommitted; focused
     tests pass.
