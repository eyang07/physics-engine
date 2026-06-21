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

### Foundation — shared rendering vocabulary (do first)

_The foundation block (FE-037, FE-038, FE-039) is complete. FE-037 is the
renderer-hint registry with a graceful fallback (new backend lenses route to a
placeholder instead of a blank stage; existing systems render unchanged). FE-038
added the shared scalar→color scale (`scalarScale` in
`viewer/src/design/colormaps.ts`) and the reusable on-stage `scalar-legend`
overlay (`viewer/src/scalarLegend.ts`) — a colormap ramp keyed by qualitative,
decimal-free endpoints; the potential-contour lens is its first consumer. FE-039
added the shared field-surface primitive (`viewer/src/fieldSurface.ts`,
`FieldSurface`): a scalar grid lifted into a colored height surface, plus a
frame-driven `update(elapsed)` displacement-animation path; the Hénon–Heiles
potential surface is its first (static-mesh) consumer. The family lenses below
build on these — FE-044 / FE-048 / FE-050 reuse the scalar legend, and FE-046 /
FE-047 / FE-048 / FE-049 reuse the field surface (its animated path binds their
exported displacement grids)._

### Direction A — Rigid-body & many-body rendering

1. **FE-040: Attitude playback for rotating rigid bodies**
   - Goal: Drive a rotating three.js body from the exported orientation (quaternion)
     series and body-frame triad, so rigid-body systems show a body that spins, not
     a point that moves.
   - Scope: `viewer/src/threeScene.ts` (rigid-body scene), `viewer/src/data/
     trajectory.ts` (orientation channel), `viewer/src/playback.ts`, and the viewer
     visual test.
   - Acceptance: a rigid-body system animates its orientation with a visible body
     triad; the body returns to the same pose on loop; `npm run build` and the
     visual test pass.
   - Depends on: BE-089 (orientation/attitude export schema), BE-087/BE-088.

2. **FE-041: Polhode / momentum-sphere ∩ energy-ellipsoid lens**
   - Goal: Render the free asymmetric top's angular-momentum sphere, kinetic-energy
     ellipsoid, and the polhode curve traced on the body, making the intermediate-axis
     instability legible.
   - Scope: `viewer/src/threeScene.ts` (polhode lens), `viewer/src/data/
     trajectory.ts` / `manifest.ts` for the exported geometry, and the viewer visual
     test.
   - Acceptance: the sphere/ellipsoid/polhode draw from the exported geometry only;
     intermediate-axis motion visibly differs from the stable axes; `npm run build`
     and the visual test pass.
   - Depends on: BE-087 (polhode / energy-ellipsoid export).

3. **FE-042: N-body orbit trails with center-of-mass framing**
   - Goal: Render N-body systems as per-body orbit trails in 3D, framed on the
     center of mass, with per-body color and a legend.
   - Scope: `viewer/src/threeScene.ts` (orbit-trail scene), renderer-hint framing in
     `viewer/src/main.ts`, and the viewer visual test.
   - Acceptance: each body draws a distinct colored trail; the figure-eight and
     Sun–planets configurations frame sensibly on the COM; `npm run build` and the
     visual test pass.
   - Depends on: BE-082 (N-body system + export).

4. **FE-043: Normal-mode lens with mode selector and superposition scrub**
   - Goal: Add a lens that animates each exported normal-mode shape, with a mode
     selector and a control to scrub a superposition, for the coupled-oscillator
     (and small-oscillation) systems.
   - Scope: `viewer/src/threeScene.ts` or a mode lens, `viewer/src/structurePanel.ts`
     for the mode selector, `viewer/src/data/manifest.ts` for mode shapes/frequencies,
     and the viewer visual test.
   - Acceptance: selecting a mode animates its shape at its frequency; a superposition
     scrub blends modes; frequencies display qualitatively (no raw decimals);
     `npm run build` and the visual test pass.
   - Depends on: BE-083 (normal-mode analysis + coupled-oscillator export).

### Direction B — Field & wave rendering

5. **FE-044: Scalar-field lens (heatmap / contour)**
   - Goal: Render an exported scalar-field grid as a heatmap/contour using the
     FE-038 color+legend layer, for potentials and other scalar fields.
   - Scope: a scalar-field lens in `viewer/src/`, `viewer/src/data/manifest.ts` for
     the field channel, reuse of FE-038, and the viewer visual test.
   - Acceptance: a scalar field renders with a correct legend and honest qualitative
     scale; the grid is drawn as exported with no browser-side field evaluation;
     `npm run build` and the visual test pass.
   - Depends on: BE-091 (field grid export); consumes BE-093 potentials, reusable for
     BE-105 curvature.

6. **FE-045: Vector-field lens (glyphs + field lines)**
   - Goal: Render an exported vector-field grid as glyphs/quiver with magnitude→color,
     and draw the exported field-line / streamline polylines.
   - Scope: a vector-field lens in `viewer/src/`, `viewer/src/data/manifest.ts` /
     `trajectory.ts` for the glyph grid and polylines, reuse of FE-038, and the viewer
     visual test.
   - Acceptance: glyphs and field lines draw from exported data only; magnitude maps
     to the shared color legend; `npm run build` and the visual test pass.
   - Depends on: BE-091 (vector-field + field-line export), BE-092, BE-093.

7. **FE-046: 1D wave displacement animation (string and wave packet)**
    - Goal: Animate the exported 1D displacement/amplitude field for the vibrating
      string and the dispersive wave packet, including a standing/traveling toggle
      where the data supports it.
    - Scope: a 1D wave lens (reusing the FE-039 surface/line primitive),
      `viewer/src/playback.ts`, `viewer/src/data/trajectory.ts`, and the viewer visual
      test.
    - Acceptance: string modes and a traveling solution animate from exported series;
      the wave packet shows envelope spreading; `npm run build` and the visual test
      pass.
    - Depends on: BE-094 (string), BE-096 (wave packet).

8. **FE-047: 2D membrane mode surfaces with mode selector**
    - Goal: Render rectangular and circular membrane modes as animated displacement
      surfaces (reusing FE-039), with a mode selector and superposition.
    - Scope: a membrane lens, `viewer/src/structurePanel.ts` for the mode selector,
      `viewer/src/data/manifest.ts` for mode data, and the viewer visual test.
    - Acceptance: rectangular and circular modes animate as exported surfaces; the
      mode selector switches shapes; `npm run build` and the visual test pass.
    - Depends on: BE-095 (membrane modes export).

9. **FE-048: 2D wavefront / intensity surface lens**
    - Goal: Render the exported 2D wavefront surfaces and intensity field from the
      heterogeneous-media work, reusing the wavefront/ray bundle path and the FE-038
      color layer for intensity.
    - Scope: extend `viewer/src/wavefrontCanvas.ts` (or a three.js surface lens),
      `viewer/src/data/manifest.ts`, reuse of FE-038/FE-039, and the viewer visual
      test.
    - Acceptance: wavefront surfaces and intensity render from exported grids;
      intensity brightens near caustics consistent with the exported diagnostic;
      `npm run build` and the visual test pass.
    - Depends on: BE-097 (2D wavefront / intensity export).

### Direction C — Curved-geometry rendering

10. **FE-049: Surface-embedding mesh with geodesic drawn on the surface**
    - Goal: Render an exported surface-of-revolution embedding mesh with the geodesic
      polyline drawn on the surface in embedded coordinates.
    - Scope: a surface-geodesic lens in `viewer/src/threeScene.ts`, `viewer/src/data/
      manifest.ts` / `trajectory.ts` for the mesh and embedded curve, renderer-hint
      framing, and the viewer visual test.
    - Acceptance: the mesh and the geodesic-on-surface draw from exported data only;
      great circles render correctly on the sphere; `npm run build` and the visual
      test pass.
    - Depends on: BE-100 (surface geodesics), BE-101 (embedding export schema).

11. **FE-050: Curvature coloring on the surface mesh**
    - Goal: Color the surface-embedding mesh by the exported curvature scalar field
      using the FE-038 color+legend layer, making curvature visible.
    - Scope: the surface-geodesic lens, `viewer/src/data/manifest.ts` for the
      curvature field, reuse of FE-038, and the viewer visual test.
    - Acceptance: the mesh colors by exported curvature with an honest legend; flat
      regions and high-curvature regions read distinctly; `npm run build` and the
      visual test pass.
    - Depends on: BE-105 (curvature scalar-field export); reuses FE-049.

12. **FE-051: Parallel-transport frame animation (holonomy)**
    - Goal: Animate the exported transported frame along a curve / closed loop on a
      curved surface, making the holonomy angle legible.
    - Scope: the surface-geodesic lens, `viewer/src/playback.ts`, `viewer/src/data/
      trajectory.ts` for the transported frame, and the viewer visual test.
    - Acceptance: the transported vector animates along the curve and the holonomy
      angle around a loop is visible; flat-space transport shows no rotation;
      `npm run build` and the visual test pass.
    - Depends on: BE-104 (parallel transport / holonomy export).

13. **FE-052: Effective-potential and orbit lens for Kepler / Schwarzschild**
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

14. **FE-035: Draw the certified enclosure box on the phase-plane stage**
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

15. **FE-036: Surface certified-numeric coverage in the catalog (after a discovery-index certified count)**
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

### Direction A — Rigid-body & many-body classical mechanics

_From point masses to bodies with extent and to coupled systems: orientation,
inertia, Euler's equations, chaotic and integrable many-body motion, and normal
modes. Builds on `engine/mechanics/` (lagrangian, hamiltonian, symmetries) and the
trajectory/manifest export._

_Complete — all Direction A tasks (BE-081..BE-089) are done and committed. The
viewer-facing payloads (polhode geometry, normal modes, rigid-body orientation)
are now exported and ready for the paired frontend lenses (FE-040..FE-043)._

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

1. **BE-108: Add coordinate-domain guards for curved backgrounds**
    - Goal: Validate and export the coordinate/domain assumptions for fixed-background
      curved examples so invalid presets fail in Python instead of producing ambiguous
      viewer payloads.
    - Scope: `systems/schwarzschild.py`, `systems/wormhole.py`, the curved-background
      generators, `scripts/example_specs.py`, docs, and `tests/`.
    - Acceptance: invalid Schwarzschild horizon-crossing and invalid wormhole throat
      parameters are rejected with clear errors; trajectory metadata documents the
      fixed-background domain assumptions; focused tests and generation pass.

2. **BE-109: Export wormhole curvature fields**
    - Goal: Add deterministic curvature scalar samples for the Ellis-wormhole fixed
      background so the curved-background gallery can color the throat geometry from
      Python-owned data.
    - Scope: `systems/wormhole.py`, `scripts/generate_wormhole.py`,
      `scripts/example_specs.py`, docs, and `tests/`.
    - Acceptance: scalar curvature samples match the `MetricGeometry` symbolic
      expression to tolerance, the throat extremum is sampled, the manifest declares
      the scalar-field source, and focused tests plus generation pass.

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
