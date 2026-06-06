# physics-engine

A learning-oriented analytical mechanics engine with a browser viewer. Python
is the source of truth for the mechanics and generated data; the TypeScript
viewer renders exported trajectories, symbolic derivations, invariants, and
visual lenses without re-deriving the physics.

## Current Shape

- `engine/` contains the Python mechanics and export code.
- `systems/` contains pure symbolic system definitions.
- `scripts/example_specs.py` is the gallery registry for parameters, state
  schema, projections, conserved quantities, effective potentials, and lenses.
- `scripts/generate_all_examples.py` regenerates trajectories and the manifest.
- `viewer/` is a Vite/TypeScript app that consumes `viewer/public/data`.
- `data/generated/` stores the generated Python-side outputs.

## Backend Tools

The engine currently supports:

- Lagrangian systems on tangent bundle charts `(q, qdot)`.
- Hamiltonian systems on cotangent bundle charts `(q, p)`.
- Euler-Lagrange equations, generalized momenta, energy, Legendre transforms,
  Hamilton equations, Poisson brackets, symplectic matrices, Hamiltonian vector
  fields, Liouville checks, canonical-transformation checks, coordinate
  pullbacks/pushforwards, holonomic constraints, and Noether charges.
- Fixed-step RK4 trajectory integration and JSON export.
- A manifest contract that exports symbolic derivations, lens metadata,
  parameter ranges, state schemas, projections, conserved quantities, and
  effective potentials.

## Current Examples

- Simple pendulum
- Geodesic on a sphere
- Charged particle in a uniform magnetic field
- Uniform gravitational field
- Ideal spring
- Kepler problem with radial effective potential

## Viewer

The viewer renders a system gallery, playback controls, mathematical structure
panels, invariant lanes, a 2D pendulum lens, a Kepler effective-potential lens,
and Three.js scenes for configuration-space, phase-space, orbit, field, and
spring views.

## Development

Install Python dependencies in your preferred environment, then install viewer
dependencies:

```sh
cd viewer
npm install
```

Regenerate all examples and manifest data:

```sh
python -m scripts.generate_all_examples
```

Run the viewer:

```sh
cd viewer
npm run dev
```

Run verification:

```sh
pytest -q
cd viewer && npm run build
```

Visual tests expect the Vite dev server at `http://127.0.0.1:5173/`:

```sh
cd viewer
npm run test:visual
```

## Direction

The next phase is to add more examples and improve the existing visual lenses
while keeping the boundary simple: Python exports structured physics data;
TypeScript turns that data into inspectable, interactive visuals.
