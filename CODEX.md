# CODEX.md

Guidance for Codex agents working in this repo.

This is a learning-oriented analytical mechanics engine. Prefer clear,
inspectable code that mirrors the mathematics over cleverness or performance.

## Current Architecture

- Python is the source of truth for mechanics and generated data.
- TypeScript/Vite is the browser viewer; it renders exported data and should
  not re-derive physics.
- `systems/` contains pure physical definitions.
- `scripts/example_specs.py` is the registry that connects systems to
  parameters, state schema, conserved quantities, effective potentials, and
  visualization lenses.
- `engine/export/manifest.py` emits the shared manifest consumed by the viewer.

## Implemented Mechanics

- Lagrangian systems on `TQ` with coordinates `(q, qdot)`.
- Hamiltonian systems on `T*Q` with coordinates `(q, p)`.
- Legendre transforms, Euler-Lagrange equations, energies, Hamilton equations,
  Poisson brackets, symplectic helpers, and Liouville checks.
- Noether support via infinitesimal symmetry generators and derived charges.
- Kepler radial reduction with exported effective potential
  `V_eff(r) = ell^2 / (2 m r^2) - m mu / r`.

## Manifest Contract

The manifest carries:

- system metadata, parameters, state variables, projections, and data paths;
- conserved quantities with Noether generator and charge LaTeX;
- structured derivations: Lagrangian, generalized momenta, Euler-Lagrange
  equations, Legendre transform, Hamiltonian flow, Noether charges, and
  effective potentials;
- a top-level lens registry, with each system referencing lens ids.

Trajectories carry sampled invariant `series` so the viewer can show
conservation as flat lines.

## Viewer State

- `viewer/src/main.ts` loads systems and lens labels from the manifest.
- `structurePanel.ts` renders the structured derivation and invariant lanes.
- `pendulumCanvas.ts` renders the 2D pendulum motion/phase lens.
- `effectivePotentialCanvas.ts` renders Kepler's radial effective-potential
  lens.
- `threeScene.ts` renders the current 3D/phase-space lenses.

## Working Rules

- Keep systems separate from presentation metadata.
- Generated data is disposable; regenerate it from scripts after manifest or
  system changes.
- Add symbolic or conservation tests when adding mechanics.
- Keep the viewer manifest-driven whenever practical.

## Verification

```sh
pytest -q
python -m scripts.generate_all_examples
cd viewer && npm run build
cd viewer && npm run dev
cd viewer && npm run test:visual
```

Visual tests expect a dev server at `http://127.0.0.1:5173/`.
