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

_**Direction change — render the new physics (mirrors the backend pivot).** The
Verification view stays as built, but the frontend's active work now follows the
physics-for-visualization backend directions (BE-082..BE-106). The viewer renders
backend-generated manifest/trajectory data and **must not re-derive physics**; new
capability arrives as documented renderer hints and export channels, drawn by the
viewer, never recomputed in it._

_**Reuse, don't duplicate (VISION §9).** The three physics families below compose a
small shared rendering vocabulary rather than three bespoke render stacks. Build the
foundation block (FE-037..FE-039) first; the family lenses depend on it. Keep the
existing honesty discipline: qualitative readouts with no raw decimals, consistent
on-stage legends, and renderer-hint-driven framing._

_**Strict dependency on backend exports.** Each family task names the `BE-0xx` task
whose export it consumes; pick it up only after that backend export has landed and
validated. The viewer renders the schema — it never invents UI against unstable or
absent data. This direction stays decoupled from the Verification domain (no
cross-links, no Systems-side safety overlay)._

### Direction C — Curved-geometry rendering

1. **FE-049: Surface-embedding mesh with geodesic drawn on the surface**
    - Goal: Render an exported surface-of-revolution embedding mesh with the geodesic
      polyline drawn on the surface in embedded coordinates.
    - Scope: a surface-geodesic lens in `viewer/src/threeScene.ts`, `viewer/src/data/
      manifest.ts` / `trajectory.ts` for the mesh and embedded curve, renderer-hint
      framing, and the viewer visual test.
    - Acceptance: the mesh and the geodesic-on-surface draw from exported data only;
      great circles render correctly on the sphere; `npm run build` and the visual
      test pass.
    - Depends on: BE-100 (surface geodesics), BE-101 (embedding export schema).

2. **FE-050: Curvature coloring on the surface mesh**
    - Goal: Color the surface-embedding mesh by the exported curvature scalar field
      using the FE-038 color+legend layer, making curvature visible.
    - Scope: the surface-geodesic lens, `viewer/src/data/manifest.ts` for the
      curvature field, reuse of FE-038, and the viewer visual test.
    - Acceptance: the mesh colors by exported curvature with an honest legend; flat
      regions and high-curvature regions read distinctly; `npm run build` and the
      visual test pass.
    - Depends on: BE-105 (curvature scalar-field export); reuses FE-049.

3. **FE-051: Parallel-transport frame animation (holonomy)**
    - Goal: Animate the exported transported frame along a curve / closed loop on a
      curved surface, making the holonomy angle legible.
    - Scope: the surface-geodesic lens, `viewer/src/playback.ts`, `viewer/src/data/
      trajectory.ts` for the transported frame, and the viewer visual test.
    - Acceptance: the transported vector animates along the curve and the holonomy
      angle around a loop is visible; flat-space transport shows no rotation;
      `npm run build` and the visual test pass.
    - Depends on: BE-104 (parallel transport / holonomy export).

4. **FE-052: Effective-potential and orbit lens for Kepler / Schwarzschild**
    - Goal: Render the exported effective potential with turning points alongside the
      orbit, surfacing bound/unbound/precessing classification for central-force and
      GR orbits.
    - Scope: extend `viewer/src/effectivePotentialCanvas.ts` and/or
      `viewer/src/phasePotentialCanvas.ts`, `viewer/src/data/manifest.ts` for the
      effective-potential / turning-point channel, and the viewer visual test.
    - Acceptance: the effective potential, turning points, and orbit draw from
      exported data; precession is visible for the GR case; the orbit class displays
      qualitatively; `npm run build` and the visual test pass.
    - Depends on: BE-102 (orbit classification), BE-103 (Schwarzschild geodesics).

### Verification track (paused)

_These two verification-view tasks predate the direction change and are kept for
continuity. They are **deprioritized** while the frontend follows the physics
directions; pick them up only on explicit request._

5. **FE-035: Draw the certified enclosure box on the phase-plane stage**
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

6. **FE-036: Surface certified-numeric coverage in the catalog (after a discovery-index certified count)**
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

_**Direction change — back to the physics engine for visualizations (VISION §3,
§9, §13).** The verification/CPS line (BE-070s) is paused. The backend now returns
to its theory-first mechanics core and grows the physics that the viewer can
render. The thesis is unchanged: Python is the source of mathematical truth and
computes + exports deterministic data; TypeScript renders. New capability crosses
the boundary as documented manifest/export schema and renderer hints, never as
physics re-derived in the viewer. Actual TypeScript rendering of these new
primitives is tracked separately in the frontend queue; these backend tasks
deliver the math, the deterministic export, and the schema contract._

_Three coherent directions, each grounded in existing modules. Tasks are ordered
by implementation readiness within each direction: foundations first, then systems
that use them, then the export/schema that carries them to the viewer. Conserved
quantities and structural identities are first-class; conservation/structure
**diagnostics computed from rollouts stay labeled `measured`** (level 1 evidence),
consistent with the rigor ladder — a clean energy trace is evidence, not a
theorem. Keep `systems/` definitions thin and symbolic, reusable logic in
`engine/`, and generated data uncommitted._

_This direction stays cleanly separated from the verification/CPS track: no
shared modules, no cross-links, no drone-specific coupling._

### Direction B — Fields, waves & continuum

_Lift the engine from particle trajectories to fields over space and to wave
phenomena. Builds on `engine/dynamics/media.py`, `ray_bundle.py`, `ray_diagnostics.py`,
and `variable_speed_wavefront`, and gives the viewer genuinely new visual primitives
(scalar fields, vector glyphs, field lines, mode shapes, wavefront surfaces)._

### Direction C — Geometry & gravitation (geometric mechanics / relativity)

_Deepen the differential-geometry strand: geodesics on curved surfaces and
spacetimes, curvature, parallel transport, and orbital structure. Generalizes
`engine/dynamics/metric.py` (today the 2-sphere and equatorial Schwarzschild) and
`systems/sphere_geodesic.py`, and gives the viewer curved-space trajectories and
embedding diagrams._

1. **BE-112: Export a non-radial Ellis-wormhole geodesic preset with turning points**
    - Goal: Add an angular-momentum (`L != 0`) wormhole geodesic preset so the radial
      effective potential (BE-110) actually exhibits a reflected geodesic that turns
      around at the centrifugal barrier without crossing the throat, giving the viewer a
      concrete reflected/traversing contrast from Python-owned data.
    - Scope: `systems/wormhole.py` (a non-radial initial-state helper), `scripts/
      generate_wormhole.py`, `scripts/example_specs.py` (a parameter variant), docs, and
      `tests/`.
    - Acceptance: the new preset has nonzero conserved `L`, its analytic turning points
      match the integrated radial extrema to tolerance, the exported classification reads
      `reflected`, the measured throat-traversal diagnostic agrees (does not cross), the
      manifest declares the variant, and focused tests plus generation pass.

2. **BE-113: Export a measured geodesic-deviation diagnostic for the Schwarzschild bound orbit**
    - Goal: Give the Schwarzschild bound-timelike preset the same measured
      geodesic-deviation diagnostic the wormhole already exports, integrating a nearby
      equatorial geodesic and recording the metric separation/focusing series along the
      orbit so the viewer can show tidal convergence/divergence from Python-owned data.
    - Scope: `scripts/generate_schwarzschild.py` (reuse
      `MetricGeometry.geodesic_deviation_diagnostic` from the equatorial metric),
      `scripts/example_specs.py` (declare the diagnostic source), docs, and `tests/`.
    - Acceptance: the timelike payload carries a `diagnostics.geodesicDeviation`
      block with `rigor="measured"`, the separation series is finite and starts from the
      recorded initial offset, the neighbor stays outside the horizon, the manifest
      declares the diagnostic source, and focused tests plus generation pass.

### Verification track (paused)

_These two verification/CPS tasks predate the direction change above and are kept
for continuity. They are **deprioritized** while the backend focuses on the physics
directions; pick them up only if the physics queue is blocked or on explicit
request._

3. **BE-079: Cross-check reachability handoff coverage against certified coverage**
    - Goal: Ensure the reachability handoff inventory stays aligned with the
      certified-status coverage report: every handoff-backed obligation is a real
      certified-numeric obligation, and missing handoffs are reported rather than
      silently ignored.
    - Scope: `engine/export/verification_package.py`,
      `engine/verification/reachability.py`, and `tests/`.
    - Acceptance: a backend validator reports certified obligations with and without
      reachability handoffs; it rejects a handoff for a non-certified obligation; no
      report claims proof or external discharge; focused tests pass.

4. **BE-080: Add a reachability handoff dependency index**
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
