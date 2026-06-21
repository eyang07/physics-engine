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
- Verification domain laid out as a verdict-first dashboard: a problem catalog
  rail, a large animated phase-plane **hero** (framed to the trajectory plus its
  safe/initial sets, with a color→role legend), a concise **summary** rail
  (compact rigor-level chip, the "safety properties (measured)" ledger,
  candidate-certificate lanes, and a backend-agnostic IR download), and a
  collapsed **"Problem details (IR)"** band holding the full IR: dynamics,
  regions, candidate certificates, proof obligations, measured statuses,
  assumptions, and the four-level rigor ladder. Every claim renders with KaTeX
  and every status is labeled honestly by rigor (`candidate` /
  `external-required` / measured, never "proved"). Cross-links navigate within the
  document (and auto-open the collapsed details), and selecting an obligation's
  evidence ↔ a certificate lane emphasizes the matching counterpart. Data comes
  from `scripts/generate_verification_problems.py`
  (`viewer/public/data/verification/`).
- Playback controls; both the Systems and Verification stages loop continuously
  (a finished run wraps and restarts rather than pausing at the end).
- Parameter-family switch: for systems exporting manifest `variants` (e.g. the
  Lorenz rho family and ideal-spring stiffness family), the inspector loads each
  backend-generated variant's data in place — no browser-side regeneration.
- Mathematical structure panels for symbolic backend exports.
- Invariant lanes and sampled series display.
- Diagnostics panel for exported phase-space structure: the finite-time Lyapunov
  estimate, Poincaré-section crossings, and per-invariant conservation-drift
  lanes (the measured `invariantResiduals`), all shown qualitatively with no raw
  decimals.
- 2D canvas lenses for pendulum, effective-potential views, and wavefront/ray
  bundles.
- Focused full-stage Poincaré-section lens for Hénon-Heiles, rendering the
  exported `(x, p_x)` crossings on the `y = 0` surface; crossings accrete as
  playback reaches each backend-located crossing time. Reads
  `metadata.poincareSections` only — no browser-side section finding.
- Systems and Verification are decoupled domains. The Systems workbench renders
  physics visuals only; all safety/verification surfaces (region geometry,
  candidate-certificate lanes, measured statuses) live entirely in the
  Verification domain. There is intentionally no Systems-side safety overlay and
  no cross-link between the two domains.
- Safety geometry on the Verification hero. The phase plane shades the exported
  `regionGeometry` set boundaries color-coded by role (safe/unsafe/initial),
  honoring each set's `convention`; the viewer draws the exported grids only and
  never evaluates the symbolic sets. Measured violations are marked on the stage
  with a focusable legend.
- Measured certificate lanes + status. The summary rail draws each candidate
  certificate's value `B(x(t))` and its flow derivative against the obligation
  threshold (e.g. `\dot B \le 0`), qualitatively and with no decimals, read from
  the exported `certificateSeries`. The IR details render the problem's
  `proofStatuses`: per-obligation sampled outcomes (`holds`/`violated`/`not
  sampled`) with the evaluation source, sample count, and worst sample. Both stay
  honest — a clean sample is evidence, never a discharge, and every obligation
  remains `external-required`.
- Three.js scenes for configuration-space, phase-space, orbit, field, spring,
  and attractor views.
- Rigid-body lenses driven by exported geometry: the heavy symmetric top's
  attitude playback orients a reusable body primitive (`AttitudeBody`) from the
  exported quaternion series, and the free asymmetric top's polhode lens draws
  the angular-momentum sphere, kinetic-energy ellipsoid, and their intersection
  (the polhode) from `metadata.rigidBodyGeometry`, highlighting the intermediate
  principal axis so the intermediate-axis instability reads clearly. The viewer
  renders the exported attitude and geometry; it never integrates Euler's
  equations.
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

1. Make the hero slot pluggable so a richer renderer (e.g. a drone's physical
   motion with geofence/obstacles + brief verification stats) can replace the
   phase-plane animation per system, driven by each problem's declared
   projection/state axes.
2. Generalize the safety surfaces across more exported problems (3-state and
   discrete-time cases) as the backend adds them; the certificate lanes still
   assume a 2-D phase projection.
3. Consider a complementary "safety margin over time" read (e.g. barrier value
   vs its threshold) alongside the hero for a clearer at-a-glance "is it staying
   safe?" signal.
