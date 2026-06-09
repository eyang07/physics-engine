# Frontend Status And Plan

The frontend is a Vite/TypeScript viewer that consumes generated Python data.
It should not re-derive physics. Its job is to turn manifest-driven
trajectories, symbolic derivations, diagnostics, and renderer hints into clear,
interactive visuals.

## Current Status

[x] Viewer: Vite/TypeScript app that consumes generated data and renders the
gallery, playback controls, structure panels, invariant lanes, 2D canvas lenses,
potential/effective-potential lenses, and Three.js views.

[x] Verification after the wavefront lens addition: `pytest -q` passes with 167
tests, `cd viewer && npm run build` passes, and `cd viewer && npm run
test:visual` passes with desktop/mobile coverage. The visual suite now includes
the all-examples pass and the fit-to-system camera-reset regression on desktop
and mobile. The viewer build emits a non-fatal Vite chunk-size warning for the
main JavaScript bundle.

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

[x] Add lightweight visual regression coverage for the fit-to-system control.
The Playwright visual suite now opens each Three.js-heavy system, clicks
`#fitToSystem`, and asserts the active WebGL canvas still has meaningful pixels
after the camera reset on desktop and mobile.

## Open questions

- Should the viewer preserve per-system camera state, or always return to the
  exported camera when switching systems?
- Should parameter changes wait for backend regeneration support, or should the
  frontend first support precomputed variants?

## Next Best Three Items

1. Add a diagnostics panel for exported backend diagnostics. Start with
   Lorenz and Hénon-Heiles finite-time Lyapunov metadata plus Hénon-Heiles
   Poincare-section metadata, consuming Python outputs without recomputing
   dynamics.

2. Add a focused Poincare-section lens for Hénon-Heiles. Render the exported
   `(x, p_x)` section points separately from the trajectory phase portrait.

3. Define parameter-family UI behavior around backend-generated variants or
   sweeps. Avoid arbitrary browser-side regeneration until the backend data
   contract is settled.

## Itinerary

1. Add a manifest-driven diagnostics panel for exported diagnostics.
2. Add a Poincare-section lens for Hénon-Heiles.
3. Consider parameter UI behavior once backend support for regenerated or
   precomputed variants is defined.
4. Keep visual polish focused on diagnostic readability before adding new
   frontend surfaces.

Latest baseline: `pytest -q` (167 tests), `cd viewer && npm run build`, and the
Playwright visual suite (4 tests: all-examples desktop/mobile and
fit-to-system desktop/mobile) all pass after adding the fit-to-system
camera-reset regression.
