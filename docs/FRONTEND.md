# Frontend Status And Plan

The frontend is a Vite/TypeScript viewer that consumes generated Python data.
It should not re-derive physics. Its job is to turn manifest-driven
trajectories, symbolic derivations, diagnostics, and renderer hints into clear,
interactive visuals.

## Current Status

[x] Viewer: Vite/TypeScript app that consumes generated data and renders the
gallery, playback controls, structure panels, invariant lanes, 2D canvas lenses,
potential/effective-potential lenses, and Three.js views.

[x] Reference verification after the wavefront lens addition: `pytest -q`
passed (178 tests at the time; the backend suite has since grown to 204 with
backend-only additions), `cd viewer && npm run build` passes, and `cd viewer &&
npm run test:visual` passes with desktop/mobile coverage. Use this as the full
baseline for broad/release-style checks; small frontend iterations should
prefer `npm run build` or a focused visual check only when relevant. The viewer
build emits a non-fatal Vite chunk-size warning for the main JavaScript bundle.

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

[x] Run the Playwright visual test suite against the local Vite server for broad
visual changes and inspect generated screenshots for desktop/mobile regressions
across all lenses. For small UI wiring changes, prefer a focused check.

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

[x] Add lightweight visual regression coverage for the fit-to-system control.
The Playwright visual suite now opens each Three.js-heavy system, clicks
`#fitToSystem`, and asserts the active WebGL canvas still has meaningful pixels
after the camera reset on desktop and mobile.

## Open questions

- Should the viewer preserve per-system camera state, or always return to the
  exported camera when switching systems?
- How should the viewer expose backend-generated parameter variants without
  implying arbitrary browser-side regeneration?

## Next Best Three Items

1. Add a diagnostics panel for exported backend diagnostics. Start with
   Lorenz and Hénon-Heiles finite-time Lyapunov metadata plus Hénon-Heiles
   Poincare-section metadata, consuming Python outputs without recomputing
   dynamics.

2. Add a focused Poincare-section lens for Hénon-Heiles. Render the exported
   `(x, p_x)` section points separately from the trajectory phase portrait.

3. Define parameter-family UI behavior around backend-generated variants or
   sweeps. Start from the manifest `variants` field and avoid arbitrary
   browser-side regeneration.

## Itinerary

1. Add a manifest-driven diagnostics panel for exported diagnostics.
2. Add a Poincare-section lens for Hénon-Heiles.
3. Consider parameter UI behavior for backend-generated precomputed variants.
4. Keep visual polish focused on diagnostic readability before adding new
   frontend surfaces.

Latest reference baseline: `cd viewer && npm run build` and the Playwright
visual suite (4 tests: all-examples desktop/mobile and fit-to-system
desktop/mobile) last verified green after the fit-to-system camera-reset
regression; the backend suite is now `pytest -q` with 204 tests (media models,
ray diagnostics, and metric geometry were added backend-only, so the viewer
build and visual suite were not re-run for them). Do not treat the full visual
suite as mandatory for every small frontend edit.
