# CLAUDE.md

A learning-oriented analytical mechanics engine with a browser visualization
layer. Code exists to make the mathematics concrete — favor readable,
well-commented implementations that mirror the math over clever or fast ones.

## Architecture

Two layers, connected by generated data (Python is the single source of truth):

- **Python engine** (`engine/`) — symbolic mechanics (SymPy). Derives
  Euler–Lagrange equations, Hamiltonians (Legendre transform), energy, Poisson
  brackets, conserved quantities; integrates trajectories; exports data.
  - `engine/mechanics/` — Lagrangian/Hamiltonian systems, charts, transforms,
    symplectic + Poisson helpers, symmetries.
  - `engine/numerics/` — integrators (RK4).
  - `engine/export/` — `Trajectory` (states + named `series`) and `manifest.py`.
- **TypeScript viewer** (`viewer/`) — Vite + three.js + KaTeX. Loads the
  exported data and renders it; never recomputes physics.
- `systems/` — pure physical definitions; `scripts/` — generation + the
  manifest registry (`example_specs.py`).

## The manifest (the boundary)

`scripts/example_specs.py` declares each system once; `engine/export/manifest.py`
emits `manifest.json` carrying presentation metadata (parameters, named state
schema, projections, lenses) **and** symbolic physics as LaTeX (Lagrangian,
Hamiltonian, equations of motion, conserved quantities + their generating
symmetry). Trajectories also carry sampled invariant `series`. Adding a system =
one `systems/*.py` + one spec; a test fails the build if a spec drifts from its
system.

## Viewer design language

- **Structure over magnitude — no digits.** The UI shows invariants,
  symmetries, and flow, never decimals. The Structure panel renders symbolic
  L/H + equations of motion (KaTeX), conserved quantities as flat "stillness"
  lines, and parameters as unlabeled markers. Time is a loop-phase ring.
- **Deep-ink palette.** Chrome tokens in `viewer/src/design/tokens.css`
  (read by `theme.ts`); data colormaps in `colormaps.ts` (perceptual
  viridis/magma for scalar fields, cyclic twilight for angle/phase/direction).
- **One flow primitive.** `viewer/src/flow.ts` advects particles along a vector
  field (replacing arrow grids); built to scale to fluids later.
- **Modules.** `main.ts` orchestrates; logic lives in `playback.ts`,
  `home.ts`, `pendulumCanvas.ts`, `structurePanel.ts`, `flow.ts`,
  `threeScene.ts`, and `data/` (`manifest`, `source`, `trajectory`).
  `TrajectorySource` is a seam: `StaticSource` serves precomputed JSON today; a
  Python `GeneratedSource` can drop in for live parameter tuning.

## Working principles

- Math first: state the definition/equation in a comment, then implement it.
- Keep pieces small, pure, and inspectable.
- Add a conservation/known-equation check when adding a system or integrator.

## Verification

```sh
pytest -q
cd viewer && npm run build
cd viewer && npm run dev          # then visit http://127.0.0.1:5173/
cd viewer && npm run test:visual  # needs the dev server running
python -m scripts.generate_all_examples   # regenerate data + manifest
```

## Deferred / future work

Lens registry (composable visualizations across systems), rendering unification
(orthographic three.js replacing the 2D pendulum canvas), and the FastAPI
`GeneratedSource` for live parameter tuning (sliders are display-only for now).
