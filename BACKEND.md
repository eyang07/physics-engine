# Backend Status And Plan

The backend is the Python source of truth for systems, symbolic mechanics,
general dynamical systems, numerical integration, generated trajectories, and
the manifest contract consumed by the TypeScript viewer.

## Current Status

[x] Core analytical mechanics layer: Lagrangian systems, Hamiltonian systems,
Euler-Lagrange equations, Legendre transforms, energy, Noether charges, Poisson
brackets, symplectic utilities, constraints, and coordinate transforms.

[x] General first-order dynamics layer for systems that are not naturally
conservative mechanics examples: symbolic RHS, Jacobian, divergence, fixed
points, linearization, and numerical RHS generation.

[x] Numerical/export layer: fixed-step RK4 integration, adaptive integration for
first-order flows, trajectory JSON export, reusable generation helpers,
Python-side generated outputs, and viewer-copy outputs.

[x] Manifest/spec layer: one registry for system metadata, parameters, state
schema, projections, conserved quantities, effective potentials, diagnostics,
visualization lenses, and renderer hints.

[x] Registered examples: simple pendulum, geodesic on a sphere, charged particle
in a uniform magnetic field, uniform gravitational field, ideal spring, Kepler
problem, bead on a rotating hoop, Lorenz attractor, and Hénon-Heiles system.

[x] Backend-only wavefront prototype: a variable-speed 2D medium now exports a
ray bundle and wavefront snapshots using cotangent Hamiltonian flow. It is not
registered in the gallery yet because the frontend does not have a ray-bundle
lens.

[x] Verification baseline: `pytest -q` passes with 149 tests. Full project
verification also includes `cd viewer && npm run build` and `cd viewer && npm
run test:visual`.

## Scope

- In: new system definitions, generator helpers, manifest/export contract,
  symbolic diagnostics, numerical integration behavior, generated data shape,
  backend tests, and renderer-hints production.
- Out: frontend UI controls, visual layout, canvas/WebGL rendering behavior, and
  Playwright-only visual polish. Those belong in `FRONTEND.md`.

## Completed Missions

[x] Add a small reusable generator helper around
`engine.numerics.integrate_fixed_step`, `Trajectory.from_arrays`, parameter
defaults, viewer-copy output, and invariant series sampling.

[x] Add new example systems as `systems/<name>.py`, register them in
`scripts/example_specs.py`, and create focused `scripts/generate_<name>.py`
entry points.

[x] Add bead on hoop, Lorenz attractor, and Hénon-Heiles in addition to the
original mechanics examples.

[x] Extend lens metadata only where needed. Existing reusable lens kinds cover
most examples, and newer lens kinds include `attractor-3d`,
`potential-contour`, and Hamiltonian-flow variants.

[x] Add symbolic tests for completed new systems' Euler-Lagrange equations,
energy, Noether charges, first-order diagnostics, and effective-potential or
potential-contour reductions where applicable.

[x] Add trajectory tests that verify state schema, JSON export, invariant
flatness, and domain-specific behavior such as staying on a constraint,
preserving angular momentum, or exporting first-order-flow diagnostics.

[x] Export renderer hints where Python already knows the geometry: Kepler orbit
bounds and central-body geometry, bead-on-hoop constraint geometry, Lorenz
scene-space bounds and transform, Hénon-Heiles potential-surface framing,
sphere radius, charged-particle field sampling, and gravity-field sampling.

[x] Fix the Lorenz renderer-hints bounds bug. The Lorenz scene applies a
center/scale transform before rendering, so renderer bounds must be exported in
scene space instead of raw Lorenz coordinates.

[x] Regenerate all outputs with `python -m scripts.generate_all_examples` after
renderer-hints changes and validate with the full backend/frontend baseline.

[x] Add the first backend-only microlocal/wave prototype: variable-speed 2D
wavefront propagation in a Gaussian slow-speed medium, exported as a ray bundle
with wavefront snapshots and Hamiltonian drift diagnostics.

## Next Best Realistic Item

Generalize the ray-bundle export helper before adding more microlocal or
general-relativity examples. The prototype generator works, but its bundle
assembly, wavefront snapshotting, Hamiltonian drift sampling, and renderer
bounds should become reusable backend utilities so future ray/geodesic examples
do not duplicate generator logic.

Recommended implementation sequence:

1. Move repeated ray-bundle assembly from
   `scripts/generate_variable_speed_wavefront.py` into a reusable helper.
2. Keep the helper generic over any `CotangentHamiltonianSystem` and list of
   initial states.
3. Preserve the current export shape: shared time, per-ray states, wavefront
   snapshots, renderer bounds, and Hamiltonian drift diagnostics.
4. Add focused tests for helper determinism and drift reporting.
5. Keep gallery registration blocked until the frontend has a real `ray-bundle`
   or `wavefront` lens.

## Backend Tools To Add

[x] Cotangent Hamiltonian system helper for principal symbols and ray/geodesic
flow.

[x] Ray-bundle trajectory export: multiple rays, shared time samples, per-ray
states, wavefront snapshots, and renderer bounds.

[x] First parameterized scalar wave-speed helper for a Gaussian slow-speed lens.

[ ] Generalize parameterized media helpers for scalar wave speed, refractive
index, or metric coefficients.

[ ] GR metric helper for fixed-background geodesic examples: Christoffel symbols
and geodesic RHS, starting with low-dimensional or symmetry-reduced metrics.

[ ] Diagnostics for wave/ray examples: Hamiltonian constraint drift, caustic
proximity, travel time, and wavefront envelope metadata.

## Itinerary

1. Add gallery registration only after the frontend has a dedicated ray-bundle
   lens.
2. Generalize the ray-bundle export helper so future microlocal/GR ray examples
   do not duplicate generator logic.
3. Add approximate Lyapunov exponent diagnostics for Lorenz or Hénon-Heiles.
4. Add a Poincare-section export for Hénon-Heiles.
5. Decide the parameter-interactivity backend strategy.
6. Add the next physics example after the data-contract direction is settled.

## Open Questions

- Should parameter interactivity use precomputed variants, local regeneration,
  or parameter sweeps?
- Should the next backend emphasis be chaos diagnostics or more classical
  mechanics examples?
- Should generated JSON remain the transport format, or should larger sweeps
  introduce a compact format later?
- Should microlocal/GR examples enter the main manifest before frontend lens
  support exists, or remain backend-only until the viewer can render them
  honestly?
