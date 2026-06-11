# Dynamical Systems Plan

The mechanics engine should keep its Lagrangian/Hamiltonian layer, but Lorenz
needs a parallel backend for general first-order dynamical systems. The goal is
to support non-conservative flows, attractors, stability diagnostics, and later
chaos/bifurcation views without forcing everything through analytical mechanics.

## Minimal Lorenz Slice

[x] Add `engine/dynamics/first_order.py` with a `FirstOrderSystem` that carries
state symbols, parameter symbols, RHS expressions, symbolic Jacobian,
divergence, fixed-point solving, linearization, and `numerical_rhs(...)`.

[x] Add an adaptive integrator wrapper around `scipy.integrate.solve_ivp` with
tolerances, max step, optional transient discard, and uniform resampling for
viewer playback.

[x] Add `systems/lorenz_attractor.py` with parameters `sigma`, `rho`, `beta`
and state `(x, y, z)`.

[x] Add a Lorenz generator that exports trajectory data, speed series,
trajectory bounds, divergence, fixed points, and Jacobian eigenvalues at fixed
points.

[x] Extend the manifest/spec layer enough to register a non-mechanics
first-order-flow example without breaking current mechanics examples.

[x] Add viewer lens support for an `attractor-3d` animation: fading trajectory,
live point, sparse vector-flow cues, fixed-point markers, and restrained
dark-stage styling matching the current visual system.

[x] Add focused tests for Lorenz RHS, divergence, fixed points, Jacobian
eigenvalues, adaptive integration output shape, exported metadata, and manifest
registration.

## Backend Shape

- `engine/dynamics/` contains general dynamical-system tools.
- `FirstOrderSystem` represents `dx/dt = f(t, x, params)`.
- Mechanics systems can remain in `engine/mechanics/`; when useful, they can be
converted to first-order systems for shared flow diagnostics.
- The export boundary should stay the same: Python exports structured state,
series, metadata, and diagnostics; TypeScript renders them.

## Diagnostics To Add Over Time

- Fixed points and symbolic/numeric Jacobians.
- Eigenvalues and stability classification at equilibria.
- Divergence and volume contraction/expansion.
- Speed, radius, and distance-from-equilibrium series.
- Trajectory bounds and recommended camera framing.
- Approximate Lyapunov exponents.
- Poincare sections.
- Parameter sweeps and bifurcation diagrams.
- Basin sampling for multistable systems.

## Viewer Lens Ideas

- `attractor-3d`: trajectory ribbon/tail, live point, fixed points, sparse flow
  particles.
- `vector-field-3d`: local arrows or advected particles through a sampled field.
- `time-series`: stacked coordinate traces.
- `poincare-section`: sampled intersections with a section plane.
- `bifurcation`: parameter sweep plot with highlighted current parameter.

## First Target

The first non-mechanics example should be the Lorenz attractor. It exercises the
new first-order-system backend, adaptive integration, dissipative-flow
diagnostics, and attractor-style rendering while staying mathematically compact.
