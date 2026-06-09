# Frontend Status And Plan

The frontend is a Vite/TypeScript viewer that consumes generated Python data.
It should not re-derive physics. Its job is to turn manifest-driven
trajectories, symbolic derivations, diagnostics, and renderer hints into clear,
interactive visuals.

## Current Status

[x] Viewer: Vite/TypeScript app that consumes generated data and renders the
gallery, playback controls, structure panels, invariant lanes, 2D canvas lenses,
potential/effective-potential lenses, and Three.js views.

[x] Verification after the wavefront lens addition: `pytest -q` passes with 158
tests, `cd viewer && npm run build` passes, and `cd viewer && npm run
test:visual` passes with desktop/mobile coverage. The viewer build emits a
non-fatal Vite chunk-size warning for the main JavaScript bundle.

## Scope

- In: manifest-driven visual rendering, viewer controls, lens polish, visual
  regression coverage, and frontend ergonomics.
- Out: new physics systems, solver work, export contracts, generated data, or
  Python engine changes. Those belong in `BACKEND.md`.

## Action items

[x] Improve existing visuals by upgrading reusable primitives in
`viewer/src/threeScene.ts`, `viewer/src/flow.ts`,
`viewer/src/pendulumCanvas.ts`, and
`viewer/src/effectivePotentialCanvas.ts`: animated trail heads, clearer axes,
better scale framing, orbit/field affordances, and less generic background
treatment.

[x] Run the Playwright visual test suite against the local Vite server and
inspect generated screenshots for desktop/mobile regressions across all lenses.

[x] Add the first renderer-hints slice where Python already knows the geometry.
These hints are presentation metadata that lets the viewer frame each system
consistently without hardcoded TypeScript guesses. The frontend consumes them
for camera framing, scene bounds, reference geometry, and field/surface sample
domains.

[x] Extend renderer hints to the remaining high-value scenes: Lorenz attractor
extent/camera, Hénon-Heiles potential-surface framing, charged-particle field
sampling, sphere radius, and gravity-field sampling bounds.

[x] Fix the Lorenz renderer-hints bounds bug. The Lorenz scene applies a
center/scale transform before rendering, so the viewer needs scene-space bounds
from the generated data.

[x] Add a dedicated 2D ray-bundle/wavefront canvas lens for the variable-speed
wavefront example. The lens draws the medium, ray traces, historical
wavefronts, the active wavefront, and the center-ray marker from backend data.

[x] Add a small frontend affordance for renderer-hint-backed scenes: a
"Fit to system" control overlaid on the Three.js stage that reapplies the
exported camera position, target, and distance bounds without reloading the
trajectory. The button is shown only for the orbit-controlled 3D scenes, and
`ThreeScene.resetCamera()` restores the home framing captured in
`setVisualization` while leaving OrbitControls interaction intact.

## Open questions

- Should the viewer preserve per-system camera state, or always return to the
  exported camera when switching systems?
- Should parameter changes wait for backend regeneration support, or should the
  frontend first support precomputed variants?

## Next Best Realistic Item

Add a lightweight visual regression check that directly opens each
Three.js-heavy system and clicks the new "Fit to system" control, asserting
the active canvas still has meaningful rendered pixels after the camera reset.
The fit affordance now exists, so the next realistic improvement is to guard it
(and the renderer-hint framing it relies on) against regressions per system.

Recommended implementation sequence:

1. Extend `viewer/tests/visual.spec.ts` to iterate the Three.js systems, click
   `#fitToSystem`, and reuse the existing non-blank-canvas assertion.
2. Keep the current desktop/mobile coverage intact.
3. Rerun `pytest -q`, `cd viewer && npm run build`, and
   `cd viewer && npm run test:visual`.

## Itinerary

1. Add a lightweight visual regression check that directly opens each
   Three.js-heavy system and asserts its active canvas has meaningful rendered
   pixels after applying renderer hints and the fit-to-system reset.
2. Consider parameter UI behavior once backend support for regenerated or
   precomputed variants is defined.
3. Keep visual polish focused on the current examples before adding new
   frontend surfaces.

Latest baseline: `pytest -q` (158 tests), `cd viewer && npm run build`, and the
Playwright visual suite (2 tests, desktop + mobile) all pass after adding the
fit-to-system camera-reset control.
