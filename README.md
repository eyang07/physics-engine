# physics-engine

A physics engine built primarily as a tool for learning classical mechanics
and beyond. The emphasis is on understanding the mathematics first, with
implementation following the theory rather than the other way around.

## Motivation

I'm studying the Lagrangian and Hamiltonian formulations of mechanics from a
pure-mathematics perspective. This repo is where I turn that theory into code.
Topics I expect to touch as I go:

- Lagrangian and Hamiltonian mechanics
- Noether's theorem (symmetries and conserved quantities)
- Liouville's theorem (phase-space volume preservation)
- An informal introduction to manifolds and symplectic geometry

## Goals

- Implement mechanics in a way that mirrors the underlying math, so the code
  doubles as a study aid.
- Prioritize clarity and mathematical fidelity over performance, at least
  early on.
- Describe motion in concise mathematical files, then turn those descriptions
  into beautiful interactive animations.
- Use the engine to explore vector fields, black-hole geodesics, fluid flows,
  and other visualizations of dynamics.
- Build a growing gallery of examples that can be viewed through multiple
  mathematical lenses: physical motion, phase space, Hamiltonian flow, energy
  surfaces, vector fields, and conserved quantities.

## Architecture

The project is split into two layers:

- **Python math engine** — defines mechanical systems, derives or states their
  equations of motion, integrates trajectories and fields, and exports
  simulation data.
- **TypeScript visualization layer** — loads exported simulation data and
  renders interactive graphics in the browser.

The boundary between the layers should stay simple: Python produces structured
state over time; TypeScript turns that state into visuals.

The mechanics layer uses a small amount of differential-geometric vocabulary,
kept concrete and chart-based:

- Lagrangian systems live on a tangent bundle chart `TQ` with coordinates
  `(q, qdot)`.
- Hamiltonian systems live on a cotangent bundle chart `T*Q` with coordinates
  `(q, p)`.
- The Legendre transform maps regular Lagrangian systems from `TQ` to `T*Q` by
  `p_i = partial L / partial qdot_i`.
- Hamiltonian geometry includes canonical Poisson brackets, symplectic
  matrices, Hamiltonian vector fields, Liouville divergence checks, and
  canonical-transformation checks.
- Coordinate changes should expose both tangent pushforwards and cotangent
  pullbacks so generalized velocities and momenta transform correctly.

For small examples, JSON is fine. For larger simulations such as fluids or
black-hole visualizations, the project may later use binary or chunked formats
such as `.npz`, HDF5, Zarr, Arrow, or custom buffers.

## Rough Shape

A likely starting structure:

- `engine/` — Python package for mechanics, numerical methods, and export
  helpers.
  - `engine/mechanics/` — Lagrangian systems, Hamiltonian systems, coordinate
    charts, bundle charts, transforms, constraints, and symmetries.
- `systems/` — concise mathematical descriptions of systems such as
  oscillators, pendulums, geodesics, and fluids.
- `viewer/` — TypeScript browser app for interactive rendering.
- `data/generated/` — exported trajectories, vector fields, grids, and other
  generated simulation artifacts.

Current examples include:

- simple pendulum
- geodesics on a sphere
- charged particle in a uniform magnetic field
- uniform gravitational field
- ideal spring
- Kepler problem

## Non-goals (for now)

- High-performance or real-time simulation.
- Being a general-purpose game/physics engine.

## Status

Early and exploratory. Direction and scope will shift as my understanding
does. The current direction is Python for the mathematical core and TypeScript
for the browser-based visualization layer.
