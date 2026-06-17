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
invariance barrier** certificate — not Lyapunov (there is no equilibrium). The
flagship is now routed broadly: nine verification packages span Tier-1 geofence
(horizontal + vertical, P1 + P2), Tier-2 obstacle keep-out and the
geofence∩obstacle intersection, and Tier-3 disturbance-robust variants of the
horizontal, vertical, and obstacle problems (each with robust P1 + P2), all
carried by the BE-039 package contract, the BE-045 discovery index (now with
BE-054 Tier/regime metadata), and BE-044 adapter stubs. The remaining work
deepens that flagship — measured-violation and boundary-margin scenarios, complete
Tier-2 assumptions, cross-package tooling, and a robust intersection capstone.
Keep generated data uncommitted. Never label anything proved/certified — the
engine proposes; external backends dispose._

BE-061 is done: the machine-readable discovery index now has a human-readable
companion. `engine/export/verification_package.py` gained `PackageSummary`,
`summarize_packages` / `read_package_summaries` (read the index and survey each
package's IR + manifest), and `render_package_summary_markdown` /
`write_package_summary`, which emit a deterministic `packages.summary.md` beside
the packages (wired into `write_verification_packages`). The table lists every
package with its model, regime (BE-054), obligation count, measured hold/violation
counts under sampling, and the worst (most negative) signed margin — e.g. the
`drone-obstacle-keepout-violation` row shows one measured-violated surface with a
`-0.250000` margin while the holding rows stay nonnegative. It is consistent with
the per-package manifests by construction and reports measured evidence only — a
measured-holds count is clean samples, never a proof or certificate. Nothing claims
proof/certification.

1. **BE-062: Disturbance-robust geofence∩obstacle intersection package**
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
