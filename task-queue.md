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

3. **FE-023: Distinguish disturbance-robust obligations in the obligation ledger**
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

4. **FE-024: Annotate the disturbance set on Tier-3 stages**
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

5. **FE-025: Surface adapter-stub descriptors in the IR inspector**
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

6. **FE-026: Per-obligation worst-margin readout aligned to the rollout**
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

7. **FE-027: Label each barrier lane for intersection-safe-set packages**
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

8. **FE-028: Verification catalog overview from the package discovery index**
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

9. **FE-029: Show the package Tier/regime badge in the catalog (after BE-054)**
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

10. **FE-030: Render the measured violation reference scenario (after BE-056)**
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

BE-050 is done: the first intersection-safe-set problem is published.
`scripts/export_verification_problems.py` added `drone_geofence_obstacle_problem`
+ its trajectory, registered as a seventh viewer example, reusing the BE-048
coupled `(q1, q2)` coasting kinematics (planar velocity a bounded parameter) and
assumptions. The published `drone-geofence-obstacle` package carries two barrier
candidates together — the geofence box barrier `B_geo = max(q1Min-q1, q1-q1Max,
q2Min-q2, q2-q2Max)` and the keep-out barrier `B_obs = rho - |q - c|` — whose safe
set is the intersection `{max(B_geo, B_obs) <= 0}` (inside the geofence box AND
outside the obstacle). Each barrier carries a worst-case one-step obligation
(`B + dt*Vmax <= 0`) plus an initial-containment obligation; the geofence claim
holds within the inner interval and the keep-out claim within the standoff annulus,
both in the guard-band interior, with measured nonnegative signed margins. Every
obligation is `external-required` and both barriers are candidates only. Nothing
claims proof/certification.

BE-051 is done: the vertical altitude axis is now disturbance-robust.
`systems/drone_point_mass.py` gained `DisturbanceSpec.assert_vertical_authority`
/ `vertical_authority_margin` (the asymmetric `min(u3Max-g, g-u3Min)` condition),
`vertical_disturbed_axis_system` (the matched additive disturbance `w3` on the
gravity-offset altitude step), and `vertical_disturbed_axis_closed_loop` (the
set-valued successor map retaining `w3` as a parameter). `scripts/
export_verification_problems.py` added `drone_vertical_disturbed_geofence_problem`
+ its nominal trajectory, registered as an eighth viewer example. The published
`drone-disturbed-vertical-geofence-axis` package carries the geofence barrier
candidate, a robust floor/ceiling forward-invariance obligation baking in the
worst-case-over-`W` term `B(F_nom) + dt^2/2*w` (cites the disturbance bound, the
disturbance-tightened robust speed bound `|v3| <= (a-w)*dt/2` with `a` the binding
asymmetric authority margin, the inner-interval driftBound region, and the robust
braking margin) plus an initial-containment obligation, and measured
`proofStatuses` that hold within their assumption region with a nonnegative
worst-case signed margin. Nothing claims proof/certification.

BE-052 is done: the first coupled worst-case avoidance problem is published.
`systems/drone_point_mass.py` gained `horizontal_plane_disturbed_coasting` — the
disturbed interior coasting map on the `(q1, q2)` plane carrying the planar
velocity `(v1, v2)` and disturbance `(w1, w2)` as bounded parameters of the
set-valued map. `scripts/export_verification_problems.py` added
`drone_disturbed_obstacle_keepout_problem` + its nominal trajectory, registered as
a ninth viewer example, reusing the BE-048 standoff/interior assumptions plus the
disturbance bound. The published `drone-disturbed-obstacle-keepout` package carries
the keep-out barrier candidate and a robust avoidance obligation baking in both
worst cases `rho - |q - c| + dt*Vmax + dt^2/2*sqrt(2)*w` (cites the planar velocity
bound and the planar disturbance bound, both non-plane/external-required, plus the
standoff annulus, interior, and the disturbance-aware standoff margin) plus an
initial-containment obligation, and measured `proofStatuses` that hold within the
standoff annulus with a nonnegative worst-case signed margin. Nothing claims
proof/certification.

BE-053 is done: the disturbed horizontal geofence package now carries the robust
self-reproducing velocity bound (Tier-3 P2). `drone_disturbed_geofence_problem`
gained a `robust-velocity-bound-barrier` candidate `|v1| - (uh + w)*dt` and a
`robust-velocity-bound:one-step-invariance` obligation whose expression bakes in
the worst-case `+dt*w` gust (`|v1_nom+| + dt*w <= (uh + w)*dt`), cites the
disturbance bound plus the nominal self-reproducing velocity bound it is asserted
from, and measured-holds with a nonnegative worst-case signed margin. The
enlargement is exactly consumed by the gust, so the margin is tight (zero) at
`|v1| = uh*dt`; because a coasting interior step under persistent wind grows the
speed by `dt*w`, the obligation is honestly asserted from the nominal bound (the
largest set one disturbed step keeps within `Bh(3)`), not self-reproducing from
`Bh(3)` itself. The existing robust P1 and initial-containment obligations are
unchanged. Nothing claims proof/certification.

BE-054 is done: the package discovery index now records an IR-derived Tier/regime
descriptor. `engine/export/verification_package.py` gained a `PackageRegime`
value object (`nominal` vs `disturbance-robust`, with the disturbance parameter
names and the obligation ids quantified over them) and a `_problem_regime` helper
that classifies a problem from its IR alone — a package is disturbance-robust when
it carries a bounded disturbance-set assumption whose parameters the set-valued
dynamics range over and that at least one obligation cites; otherwise nominal
(reading neither the model name nor the package id, so a frozen-velocity coasting
parameter is correctly *not* mistaken for a disturbance). `build_package_manifest`
derives the regime, `PackageManifest`/`PackageIndexEntry` carry it optionally and
backward-compatibly (absent on older indexes), `build_package_index` propagates it,
and both `read_package` (entry vs IR) and `read_package_index` (entry vs manifest)
reject regime drift. The three disturbance-robust drone packages are distinguished
from the six nominal ones from IR data alone. Pure cataloging; nothing claims
proof/certification.

BE-055 is done: the disturbed vertical altitude package now carries the robust
self-reproducing velocity bound (Tier-3 P2), the vertical mirror of BE-053.
`drone_vertical_disturbed_geofence_problem` gained a `robust-velocity-bound-barrier`
candidate `|v3| - (reach + w)*dt` and a `robust-velocity-bound:one-step-invariance`
obligation that bakes in the worst-case `+dt*w` gust (`|v3_nom+| + dt*w <=
(reach + w)*dt`), cites the disturbance bound plus the nominal self-reproducing
vertical velocity bound, and measured-holds with a nonnegative worst-case signed
margin. The nominal bound uses the asymmetric **reach** `= max(u3Max-g, g-u3Min)`
(the larger margin) because the **interior** binds: the hover branch cancels
gravity, so a coasting interior step is velocity-preserving and the brakes never
overshoot `reach*dt`. The *binding* margin `a = min(u3Max-g, g-u3Min)` governs the
separate robust speed precondition (P1), not this bound — so, like BE-053, the
obligation is honestly asserted from the nominal bound, not self-reproducing from
the enlarged `(reach + w)*dt`. The existing robust floor/ceiling and
initial-containment obligations are unchanged. Nothing claims proof/certification.

1. **BE-056: Export the Tier-2 boundary-corner violation reference scenario**
   - Goal: Every published package only *holds*, so the engine's measured-violation
     surface is never exercised end-to-end. Export the DRONE_MODEL_SPEC §L.2 / Tier-2
     "load-bearing diagonal corner" scenario as a second trajectory on the obstacle
     keep-out problem that approaches and enters the unsafe set, and emit measured
     `proofStatuses` carrying a **negative** signed `margin` for the avoidance
     obligation, using the existing event-based unsafe-set entry detection
     (integrator-located entry time). This makes a measured violation a concrete,
     honest rigor-level-1 artifact — evidence the run left the set on this rollout,
     never a disproof of the candidate.
   - Scope: `scripts/export_verification_problems.py` (the violation-scenario
     trajectory and its sampled statuses on `drone_obstacle_keepout_problem`),
     `engine/verification/measured.py` if violation sampling needs a seam, and
     `tests/`.
   - Acceptance: the obstacle package exports a violation scenario whose avoidance
     `proofStatus` reports a negative worst-case margin with an integrator-located
     entry, distinct from the holding rollout; the holding scenario is unchanged;
     the violation is labeled measured evidence only; nothing claims
     proof/certification; generated data stays uncommitted; focused tests pass.

2. **BE-057: Cross-package consistency validator for the drone flagship**
   - Goal: The flagship now spans seven drone packages sharing one model
     (DRONE_MODEL_SPEC §N cross-artifact consistency), but nothing checks that they
     agree. Add a helper that validates all drone packages against a single
     `DroneParams` and shared assumption/geometry conventions — same parameter
     values, consistent geofence/inner-set/obstacle geometry, consistent assumption
     bounds — so the packages cannot silently drift apart. Pure validation; it
     asserts consistency, it does not certify safety.
   - Scope: `engine/export/verification_package.py` or a small
     `engine/verification/` helper (cross-package consistency check), and `tests/`.
   - Acceptance: a test asserts the published drone packages share consistent
     params, geometry, and assumption bounds, and fails loudly on an injected
     mismatch; nothing claims proof/certification; generated data stays uncommitted;
     focused tests pass.

3. **BE-058: Encode the full `Obstacle.Valid` assumption triple on the keep-out
   package**
   - Goal: The obstacle keep-out package (BE-048) cites only a standoff-sizing
     precondition, but DRONE_MODEL_SPEC §337/§711 requires the full `Obstacle.Valid`
     triple: (1) dilated obstacle inside the inner safe set, (2) separation (band
     narrower than half the obstacle, single-valued controller), (3) braking
     adequacy (band dominates one-step drift at the velocity cap). Add all three as
     explicit assumptions the avoidance obligation cites, marking the non-plane ones
     external-required. This makes the avoidance claim's preconditions complete and
     honest.
   - Scope: `scripts/export_verification_problems.py` (add the three assumptions to
     `drone_obstacle_keepout_problem` and have the avoidance obligation cite them),
     `systems/drone_point_mass.py` if the `ObstacleSpec` needs the derived margins,
     and `tests/`.
   - Acceptance: the keep-out package carries the three `Obstacle.Valid` assumptions
     with the avoidance obligation citing them; plane-expressible ones are sampled,
     non-plane ones are external-required; the measured avoidance `proofStatus` is
     unchanged where it already held; nothing claims proof/certification; generated
     data stays uncommitted; focused tests pass.

4. **BE-059: Boundary-approaching margin scenario for the Tier-1 geofence axis**
   - Goal: The Tier-1 geofence rollout sits comfortably inside the safe set, so its
     measured holds-margin is large and uninformative (and gives FE-021 little to
     show). Export the DRONE_MODEL_SPEC §L.2 boundary-approaching scenario: a second
     trajectory that drives the horizontal axis near the geofence boundary so the
     measured forward-invariance margin is small but nonnegative, exercising the
     closest-approach surface with a tight, honest margin. Still measured evidence,
     never a discharge.
   - Scope: `scripts/export_verification_problems.py` (the margin-scenario
     trajectory and sampled statuses on `drone_geofence_problem`), and `tests/`.
   - Acceptance: the geofence package exports a boundary-approaching scenario whose
     forward-invariance `proofStatus` reports a small nonnegative worst-case margin
     with its closest-approach point, distinct from the comfortable rollout; the
     existing scenario is unchanged; nothing claims proof/certification; generated
     data stays uncommitted; focused tests pass.

5. **BE-060: Robustness-aware adapter stubs for quantified-over-disturbance
   obligations**
   - Goal: The adapter-stub catalog (BE-044) derives reachability/SOS/deductive
     stubs from each obligation's classified target, but a Tier-3 robust obligation
     (set-valued successor, quantified over the wind box `W`, worst-case term baked
     in) is a distinct obligation *shape* that an external backend must handle
     differently. Extend the stub descriptors so robust obligations carry an honest
     robustness flag and the disturbance set they quantify over, derived only from
     IR data. Every stub stays non-discharging.
   - Scope: `engine/verification/adapter_stubs.py` (robustness-aware stub shape),
     `engine/export/verification_package.py` if the descriptor validation needs
     extending, and `tests/`.
   - Acceptance: robust obligations' stubs record the robustness flag and
     disturbance set; nominal obligations' stubs are unchanged; `read_package`
     validates the extended descriptors; every stub stays `discharges: false` and
     obligations stay `external-required`; nothing claims proof/certification;
     generated data stays uncommitted; focused tests pass.

6. **BE-061: Cross-package human-readable catalog summary report**
   - Goal: The discovery index (BE-045) is machine-readable, but there is no
     human-readable cross-package summary like the inspection adapter's per-problem
     report. Add a writer that emits one deterministic summary across all packages —
     per package: model, Tier/regime (BE-054), obligation count and how many hold
     vs. are violated under measured sampling, and the worst signed margin — so a
     reader can survey the flagship at a glance. Pure cataloging; it reports
     measured status, it certifies nothing.
   - Scope: `engine/export/verification_package.py` or a thin `scripts/` entry
     point reading the published packages/index, and `tests/`.
   - Acceptance: the summary report lists every package with its model, regime,
     hold/violation counts, and worst margin, consistent with the per-package
     manifests; it is deterministic and re-readable; nothing claims
     proof/certification; generated data stays uncommitted; focused tests pass.

7. **BE-062: Disturbance-robust geofence∩obstacle intersection package**
    - Goal: BE-050 publishes the nominal geofence∩obstacle intersection and
      BE-049/052 publish Tier-3 robust geofence and obstacle packages, but there is
      no robust *intersection* package. Combine them: on the coupled `(q1, q2)`
      plane carry both the geofence box barrier and the keep-out barrier with their
      robust worst-case one-step obligations (each baking in the disturbance term as
      in BE-049/052), safe set `{max(B_geo, B_obs) <= 0}`, under the spec-G plus
      disturbance assumptions. This is the natural capstone of the nominal/robust ×
      single/intersection matrix.
    - Scope: `scripts/export_verification_problems.py` (add
      `drone_disturbed_geofence_obstacle_problem` + its nominal trajectory, register
      it as a viewer example), `systems/drone_point_mass.py` if a combined disturbed
      coasting map is needed, and `tests/`.
    - Acceptance: the published robust intersection package carries both barriers as
      candidates, each with a robust worst-case avoidance/forward-invariance
      obligation citing the disturbance bound, and measured `proofStatuses` holding
      within their assumption regions with nonnegative worst-case margins; both
      barriers stay candidate and obligations external-required; nothing claims
      proof/certification; generated data stays uncommitted; focused tests pass.
