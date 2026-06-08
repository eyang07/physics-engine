# Frontend Status And Plan

The frontend is a Vite/TypeScript viewer that consumes generated Python data.
It should not re-derive physics. Its job is to turn manifest-driven
trajectories, symbolic derivations, diagnostics, and renderer hints into clear,
interactive visuals.

## Current Status

[x] Viewer: Vite/TypeScript app that consumes generated data and renders the
gallery, playback controls, structure panels, invariant lanes, 2D canvas lenses,
potential/effective-potential lenses, and Three.js views.

[x] Verification after the renderer-hints rollout: `pytest -q` passes with 145
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

[ ] Add a small frontend affordance for renderer-hint-backed scenes, such as a
camera reset button or a "fit to system" action that reapplies the exported
camera/bounds without reloading the trajectory.

## Open questions

- Should the viewer preserve per-system camera state, or always return to the
  exported camera when switching systems?
- Should parameter changes wait for backend regeneration support, or should the
  frontend first support precomputed variants?

## Next Best Realistic Item

Add a small frontend affordance that uses the renderer-hints work directly.
The scenes now load with exported framing and geometry metadata; the next
realistic improvement is to let users recover that framing after orbiting,
zooming, or comparing systems.

These hints answer questions like:

- How does a user reset the camera to the system's exported best view?
- Can each scene expose a consistent "fit to system" behavior?
- Should the viewer preserve per-system camera state or always return to the
  exported camera when switching systems?

Recommended implementation sequence:

1. Add a small reset/fit control near the Three.js stage controls.
2. Expose a `resetCamera()` method on `ThreeScene` that reapplies the current
   scene's exported camera and distance bounds.
3. Keep the current OrbitControls interaction intact.
4. Rerun `pytest -q`, `cd viewer && npm run build`, and
   `cd viewer && npm run test:visual`.

## Itinerary

1. Add camera reset / fit-to-system control.
2. Add a lightweight visual regression check that directly opens each
   Three.js-heavy system and asserts its active canvas has meaningful rendered
   pixels after applying renderer hints.
3. Consider parameter UI behavior once backend support for regenerated or
   precomputed variants is defined.
4. Keep visual polish focused on the current nine examples before adding new
   frontend surfaces.

Latest baseline: `pytest -q`, `cd viewer && npm run build`, and the Playwright
visual suite all pass. The visual suite passed 2 tests covering desktop and
mobile rendering across the registered examples after the full renderer-hints
rollout and Lorenz bounds fix.
