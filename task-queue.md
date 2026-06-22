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

1. **FE-052: Effective-potential and orbit lens for Kepler / Schwarzschild**
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

2. **FE-053: Wormhole embedding funnel with the geodesic on the surface**
    - Goal: Render the exported Ellis-wormhole embedding mesh (the funnel through the
      throat) with the geodesic drawn on the surface, reusing the surface-geodesic
      mesh primitive (FE-049) so reflected vs traversing geodesics read from the data.
    - Scope: extend the surface-geodesic lens (or a thin wormhole variant) in
      `viewer/src/threeScene.ts`, `viewer/src/data/trajectory.ts` to read
      `metadata.wormholeGeometry` (`embeddingMesh` + `geodesic`, the same `surface-mesh`
      schema FE-049 already parses), `viewer/src/rendererRegistry.ts`, and the viewer
      visual test.
    - Acceptance: the funnel mesh and the geodesic-on-surface draw from exported data
      only; the throat is visible; a reflected geodesic turns back without crossing the
      throat while a traversing one passes through; `npm run build` and the visual test
      pass.
    - Depends on: BE-109/BE-110 (wormhole embedding + radial potential), BE-112
      (non-radial reflected preset); reuses FE-049.

3. **FE-054: Measured tidal geodesic-deviation readout**
    - Goal: Surface the exported measured geodesic-deviation diagnostic (neighbor
      separation / tidal focusing) along a GR orbit, so tidal convergence/divergence is
      legible as an honest measured series, never a proof.
    - Scope: a small diagnostics lane/overlay reusing existing diagnostics-panel
      primitives, `viewer/src/data/trajectory.ts` for
      `metadata.diagnostics.geodesicDeviation` (separation + relative-separation series),
      and the viewer visual test.
    - Acceptance: the separation series draws from exported data with a `measured`
      label and qualitative endpoints (converging / diverging), the neighbor's initial
      offset is shown, nothing reads as proved; `npm run build` and the visual test pass.
    - Depends on: wormhole `diagnostics.geodesicDeviation` (landed), BE-113
      (Schwarzschild geodesic-deviation diagnostic).

### Verification track (paused)

_These two verification-view tasks predate the direction change and are kept for
continuity. They are **deprioritized** while the frontend follows the physics
directions; pick them up only on explicit request._

4. **FE-035: Draw the certified enclosure box on the phase-plane stage**
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

5. **FE-036: Surface certified-numeric coverage in the catalog (after a discovery-index certified count)**
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

_No active physics tasks queued; add the next coherent geometry/gravitation task
here when starting new backend work._

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
