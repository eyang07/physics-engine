# Frontend Status

The frontend is a Vite/TypeScript viewer. It consumes Python-generated manifest
and trajectory data; it must not re-derive physics.

## Current Capabilities

- Systems-only workbench shell: top bar, About dialog, always-visible system
  catalog, visualization stage, and inspector. The app boots straight into the
  Systems workbench.
- Parameter-family switch: for systems exporting manifest `variants` (e.g. the
  Lorenz rho family and ideal-spring stiffness family), the inspector loads each
  backend-generated variant's data in place.
- Mathematical structure panels for symbolic backend exports.
- Diagnostics panel for exported phase-space structure: finite-time Lyapunov
  estimate, Poincare-section crossings, per-invariant conservation-drift lanes,
  and measured geodesic-deviation lanes where exported.
- 2D canvas lenses for pendulum, effective-potential views, normal modes,
  wave/string systems, Poincare sections, scalar fields, vector fields,
  wavefront/ray bundles, and spacetime diagrams.
- Three.js scenes for configuration-space, phase-space, orbit, field, spring,
  attitude, rigid-body, N-body, membrane, and attractor views.
- Rigid-body lenses driven by exported geometry: the heavy symmetric top's
  attitude playback and the free asymmetric top's polhode lens both render
  backend-exported attitude/geometry data.
- N-body orbit lens: per-body trails and live markers, framed on exported
  center-of-mass data, with backend-generated variants loading in place.
- Normal-mode lens: exported mode shapes, frequencies, and superposition scrub
  are rendered without solving the eigenproblem in the browser.
- Renderer-hint-based camera framing and a fit-to-system reset control.
- Playwright visual regression coverage for all examples and fit-to-system
  behavior on desktop/mobile.

## Removed Verification Frontend

The previous frontend Verification workbench has been stripped pending a
redesign. This removes the old React/Radix/Tailwind shell, verification catalog,
state-space stage, certificate lanes, frontend verification data loaders, and
visual tests for that UI.

Backend verification IR/export support remains documented in `docs/BACKEND.md`.
Generated verification artifacts may still exist under ignored data paths, but
the viewer does not load or render them.

## Scope

- In: manifest-driven rendering, controls, lens polish, diagnostics display,
  visual regression coverage, frontend ergonomics, and viewer-only styling.
- Out: physics derivation, solver behavior, new systems, export-contract design,
  generated data shape, backend diagnostics, and proof discharge. Those belong in
  `docs/BACKEND.md`.

## Checks

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

1. Continue Systems-domain renderer work against backend-generated relativity and
   electrodynamics exports.
2. Keep the redesign surface clear: do not add frontend Verification code back
   until the replacement information architecture and contracts are chosen.
