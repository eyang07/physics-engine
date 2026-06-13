# Frontend Status

The frontend is a Vite/TypeScript viewer. It consumes Python-generated manifest
and trajectory data; it must not re-derive physics.

## Current Capabilities

- Persistent workbench shell: a top bar with a hard top-level domain menu
  (**Systems** for simulation/visualization vs. **Verification** for the safety
  and proof-obligation surfaces) plus an About dialog. The app boots straight
  into the Systems workbench — no splash gate.
- Systems domain laid out as a three-pane workbench: an always-visible catalog
  rail that swaps the stage directly, the visualization stage, and an inspector.
- Verification domain with a read-only inspector for the exported
  verification-problem IR: a problem catalog rail plus a rendered document
  showing the dynamics, regions (safe/unsafe/initial/domain, color-coded),
  candidate certificates with their linked obligations, and the proof
  obligations themselves — every claim rendered with KaTeX and every status
  labeled honestly by rigor (`candidate` / `external-required`, never "proved").
  Data comes from `scripts/generate_verification_problems.py`
  (`viewer/public/data/verification/`).
- Playback controls.
- Mathematical structure panels for symbolic backend exports.
- Invariant lanes and sampled series display.
- 2D canvas lenses for pendulum, effective-potential views, and wavefront/ray
  bundles.
- Three.js scenes for configuration-space, phase-space, orbit, field, spring,
  and attractor views.
- Renderer-hint-based camera framing and a fit-to-system reset control.
- Playwright visual regression coverage for all examples and fit-to-system
  behavior on desktop/mobile.

## Scope

- In: manifest-driven rendering, controls, lens polish, diagnostics display,
  visual regression coverage, frontend ergonomics, and viewer-only styling.
- Out: physics derivation, solver behavior, new systems, export-contract design,
  generated data shape, and backend diagnostics. Those belong in
  `docs/BACKEND.md`.

## Verification

Build/type-check:

```sh
cd viewer
npm run build
```

Visual regression tests require the Vite dev server at `http://127.0.0.1:5173/`:

```sh
cd viewer
npm run dev
cd viewer
npm run test:visual
```

The Vite main-bundle chunk-size warning is known and non-fatal.

## Next Work

1. Add a manifest-driven diagnostics panel for exported backend diagnostics,
   starting with Lorenz/Hénon-Heiles finite-time Lyapunov metadata and the
   Hénon-Heiles Poincare section.
2. Add a focused Poincare-section lens for Hénon-Heiles using exported
   `(x, p_x)` section points.
3. Define parameter-family UI behavior around backend-generated variants and
   avoid arbitrary browser-side regeneration.
4. Cross-link the domains: jump from a controlled system in Systems to its
   verification problem, and render the IR's safe/unsafe-set geometry on a stage
   alongside the trajectory.
5. Later, add candidate certificate values along trajectories and a proof-status
   surface once backend metadata is exported through the manifest.
