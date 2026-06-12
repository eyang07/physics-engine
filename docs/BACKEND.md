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
problem, bead on a rotating hoop, Lorenz attractor, Hénon-Heiles system, and
variable-speed wavefront propagation.

[x] Wavefront prototype: a variable-speed 2D medium now exports a ray bundle and
wavefront snapshots using cotangent Hamiltonian flow, and the viewer renders it
with a dedicated 2D wavefront lens.

[x] Reference verification baseline: `pytest -q` passes with 222 tests. Full
project verification also includes `cd viewer && npm run build` and
`cd viewer && npm run test:visual`, but small backend iterations should use
targeted tests or specific generators first.

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
shared renderer-hints changes and validate with the full backend/frontend
baseline. For one-system output changes, prefer the specific generator while
iterating.

[x] Add the first backend-only microlocal/wave prototype: variable-speed 2D
wavefront propagation in a Gaussian slow-speed medium, exported as a ray bundle
with wavefront snapshots and Hamiltonian drift diagnostics.

[x] Generalize the ray-bundle export helper. Ray integration, shared time
sampling, wavefront snapshot records, renderer coordinate bounds, and
Hamiltonian drift reporting now live in reusable `engine.dynamics.ray_bundle`
utilities, and the variable-speed wavefront generator delegates to them without
changing generated JSON outputs.

[x] Add approximate finite-time Lyapunov diagnostics for Lorenz. The Lorenz
export now carries sampled largest-FTLE series data, local growth rates, and
metadata describing the variational-Jacobian method.

[x] Add a Poincare-section export for Hénon-Heiles. The generated trajectory now
exports interpolated `y = 0`, upward-crossing section points with `(x, p_x)`
axes, full state coordinates, momentum extras, and energy samples.

[x] Add invariant-residual tracking for known conserved quantities. Mechanics
trajectory metadata now carries measured max absolute, RMS, and relative
drift summaries keyed to the existing invariant series, with near-zero
references reported as absolute-only diagnostics.

[x] Add a finite-time Lyapunov diagnostic for Hénon-Heiles. The generated
trajectory now mirrors the Lorenz FTLE metadata and series shape while keeping
invariant residuals scoped to conserved quantities.

[x] Add parameter-sweep manifest support for selected systems. The manifest can
now attach deterministic precomputed `variants` to a system, and Lorenz exports
rho-family trajectories alongside the default path.

[x] Generalize parameterized media helpers. `engine.dynamics.media` now provides
reusable scalar wave-speed, refractive-index, and inverse-metric medium models
that each build a `CotangentHamiltonianSystem`, plus a parameterized Gaussian
slow-speed lens profile. The variable-speed wavefront system delegates to them
without changing generated JSON outputs, and symbolic tests pin the
refractive-index and conformal-metric reductions to the scalar-speed symbol.

[x] Add diagnostics for wave/ray examples. `engine.dynamics.ray_diagnostics`
now computes per-ray travel time (the eikonal phase integral of `xi . dq`,
with a measured residual against the exact `degree * p0 * s` model for
homogeneous symbols), caustic proximity via adjacent-ray finite-difference
spreading factors, and per-snapshot wavefront envelope metadata (arc length,
spreading range, coordinate bounds). The variable-speed wavefront export
carries these in an additive `rayDiagnostics` metadata block.

[x] Add the GR metric helper for fixed-background geodesic examples
(backend-only). `engine.dynamics.metric.MetricGeometry` derives Christoffel
symbols, a metric-compatibility residual that must vanish identically, the
geodesic equation as a `FirstOrderSystem`, and the cogeodesic
`InverseMetricMedium`. Reference constructors cover the round 2-sphere and the
equatorial Schwarzschild plane. Verified symbolically against textbook
Christoffel values, the Lagrangian route for the sphere geodesic, and the
Legendre transform; measured: a Schwarzschild circular orbit holds its radius
and Killing charges to 1e-12. No gallery/manifest entry until the viewer can
render the geometry honestly.

[x] Add the controlled-dynamics layer (backend-only), per the design spec in
`docs/controlled-dynamics.md`. `engine.dynamics.controlled` provides
`ControlledFirstOrderSystem` (`x' = f(t, x, u, d; params)`) with state/control/
disturbance Jacobians, equilibrium residuals, closed-loop reduction to
`FirstOrderSystem` (so all existing diagnostics apply unchanged), box-shaped
admissible sets that are measured and reported — never silently clipped — and
deterministic rollouts under numeric control laws. Anchor system: the
torque-actuated damped pendulum (`systems/controlled_pendulum.py`, not in the
gallery). The discrete-time analogue is deferred.

[x] Add safety / certificate metadata (backend-only), per the design spec in
`docs/safety-certificates.md`. `engine.dynamics.safety` provides sublevel
safe/unsafe sets, measured trajectory safety reports, candidate barrier and
Lyapunov functions, symbolic Lie derivatives, proof-obligation records, and
deterministic sampled obligation checks labeled `rigor="measured"`. This is
candidate metadata and counterexample-finding support only; sound certificate
synthesis, proof discharge, validated numerics, IR serialization, manifest
export, and viewer surfaces remain deferred.

## Next Best Three Items

1. Define verification-problem IR v0 (`docs/VISION.md` §11 priority 3).
   Serialize the proof obligations emitted by safety/certificate metadata as a
   backend-agnostic inspection artifact, with no claim that obligations are
   discharged locally.

2. Extend parameter variants beyond Lorenz.
   Add Hénon-Heiles or another high-value system once the frontend can expose
   backend-generated variants without arbitrary browser-side regeneration.

3. Backend-only geodesic exploration on `MetricGeometry`.
   For example a Schwarzschild orbit family (precession, photon-sphere
   approach) exported as data for inspection, still outside the gallery
   manifest pending honest lens support.

## Backend Tools To Add

[x] Cotangent Hamiltonian system helper for principal symbols and ray/geodesic
flow.

[x] Ray-bundle trajectory export: multiple rays, shared time samples, per-ray
states, wavefront snapshots, and renderer bounds.

[x] Reusable ray-bundle generator utilities for cotangent Hamiltonian systems:
shared time integration, Hamiltonian drift reporting, wavefront records, and
coordinate bounds.

[x] First parameterized scalar wave-speed helper for a Gaussian slow-speed lens.

[x] Generalize parameterized media helpers for scalar wave speed, refractive
index, or metric coefficients (`engine.dynamics.media`).

[x] GR metric helper for fixed-background geodesic examples: Christoffel symbols
and geodesic RHS, starting with low-dimensional or symmetry-reduced metrics
(`engine.dynamics.metric.MetricGeometry`, with 2-sphere and equatorial
Schwarzschild reference constructors).

[x] Diagnostics for wave/ray examples: Hamiltonian constraint drift (in the
ray-bundle helper), caustic proximity, travel time, and wavefront envelope
metadata (`engine.dynamics.ray_diagnostics`).

[x] Controlled first-order dynamics with admissible boxes, closed-loop
reduction, and deterministic rollouts (`engine.dynamics.controlled`; design
spec in `docs/controlled-dynamics.md`).

## Example Generation Notes

- Review VisualPDE as an inspiration/reference source for future generated PDE
  examples, especially wave propagation, pattern formation, reaction-diffusion,
  and parameterized media demos.

## Itinerary

1. [x] Add invariant-residual tracking for known conserved quantities.
2. [x] Add parameter sweep manifests for selected systems.
3. [x] Generalize parameterized media helpers.
4. Decide the parameter-interactivity backend strategy.
5. Add the next physics example after the data-contract direction is settled.

## Open Questions

- How broad should the first frontend parameter-family UI be now that the
  backend manifest supports precomputed variants?
- Should the next backend emphasis be chaos diagnostics or more classical
  mechanics examples?
- Should generated JSON remain the transport format, or should larger sweeps
  introduce a compact format later?
- Should microlocal/GR examples enter the main manifest before frontend lens
  support exists, or remain backend-only until the viewer can render them
  honestly?
