# physics-engine

A theory-first analytical mechanics and dynamical-systems engine with a browser
viewer. Python is the source of mathematical truth; the TypeScript viewer renders
exported trajectories, symbolic structure, diagnostics, and visual lenses without
re-deriving physics.

## Current Status

The project is a working v0.1 mechanics workbench with a growing v0.2 layer for
diagnostics, controlled dynamics, safety metadata, and verification artifacts.

- Python backend:
  - Lagrangian and Hamiltonian mechanics.
  - General first-order dynamical systems.
  - Controlled first-order systems with admissible boxes and deterministic
    rollouts, plus their discrete-time analogue
    `x_{k+1} = F(k, x_k, u_k, d_k)` with Euler discretization of autonomous
    continuous systems.
  - Cotangent Hamiltonian flow, ray bundles, parameterized media, and metric
    geometry helpers.
  - Diagnostics for invariants, Poincare sections, finite-time Lyapunov
    exponents, ray travel time, caustic proximity, and wavefront envelopes.
  - Safety/certificate candidate metadata: safe and unsafe sublevel sets,
    candidate Lyapunov/barrier functions, continuous and discrete proof
    obligations, and measured sampling checks, plus event-based unsafe-set
    entry detection with integrator-located (not grid-snapped) entry times.
  - Candidate generation: quadratic Lyapunov candidates from a Hurwitz
    linearization, sublevel barrier candidates, and measured level
    suggestions — proposals only, never certification.
  - Backend-agnostic verification-problem IR v2 encoding continuous and
    discrete dynamics, control/disturbance channels, explicit assumptions,
    candidate certificates, and obligations for external
    inspection/discharge, plus a stub inspection adapter that writes canonical
    problem JSON and a human-readable report. The engine does not certify or
    prove safety.
- Viewer:
  - Vite/TypeScript app with gallery navigation, playback controls, structure
    panels, invariant lanes, 2D canvas lenses, and Three.js scenes.
  - Dedicated wavefront/ray-bundle lens and fit-to-system camera reset for
    renderer-hint-backed scenes.

## Repository Layout

- `engine/mechanics/` - Lagrangian/Hamiltonian mechanics, symmetries,
  constraints, coordinates, Poisson/symplectic utilities.
- `engine/dynamics/` - first-order, controlled, cotangent, ray, media, metric,
  diagnostics, and safety-candidate tools.
- `engine/verification/` - versioned verification-problem IR and adapters.
- `engine/numerics/` - fixed-step RK4, adaptive, symplectic, and
  event-located integration.
- `engine/export/` - trajectory and manifest JSON contracts.
- `systems/` - pure symbolic system definitions.
- `scripts/` - example registry and deterministic data generators.
- `viewer/` - TypeScript/Three.js/KaTeX viewer.
- `tests/` - symbolic, numerical, export, and viewer-adjacent backend tests.

## Examples

Registered viewer examples:

- Simple pendulum
- Geodesic on a sphere
- Charged particle in a uniform magnetic field
- Uniform gravitational field
- Ideal spring
- Kepler problem
- Bead on a rotating hoop
- Lorenz attractor, including precomputed rho variants
- Hénon-Heiles system
- Variable-speed wavefront propagation

Backend-only examples and helpers include the controlled pendulum, metric
geometry reference constructors, safety/certificate candidate checks, and
verification-problem IR export.

## Development

Install viewer dependencies once:

```sh
cd viewer
npm install
```

Regenerate all trajectories and manifest data:

```sh
python -m scripts.generate_all_examples
```

Run backend tests:

```sh
pytest -q
```

Build the viewer:

```sh
cd viewer
npm run build
```

Run the viewer locally:

```sh
cd viewer
npm run dev
```

Visual tests expect the Vite dev server at `http://127.0.0.1:5173/`:

```sh
cd viewer
npm run test:visual
```

For small changes, run the narrowest relevant test/build first. Use the full
backend and viewer baseline for broad changes or release-style checks.

## Direction

The near-term backend direction is to harden the verification IR, safety
metadata, assumptions, and deterministic export contracts before adding more
case-study breadth. The near-term frontend direction is to expose exported
diagnostics and, later, safety/certificate metadata without recomputing physics
in TypeScript.
