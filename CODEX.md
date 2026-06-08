# Project Status And Plan

Build the next phase around the existing contract: Python defines systems and
generated data, `scripts/example_specs.py` registers gallery metadata/lenses,
and the viewer renders manifest-driven trajectories. The backend already has
Lagrangian/Hamiltonian mechanics, first-order dynamical systems, Noether
quantities, fixed-step RK4 integration, adaptive `solve_ivp` integration,
trajectory JSON export, manifest export, nine registered examples, and tests
covering equations, invariants, generation helpers, manifest shape, and the
newer example systems.

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
and visualization lenses.

[x] Viewer: Vite/TypeScript app that consumes generated data and renders the
gallery, playback controls, structure panels, invariant lanes, 2D canvas lenses,
potential/effective-potential lenses, and Three.js views.

[x] Registered examples: simple pendulum, geodesic on a sphere, charged particle
in a uniform magnetic field, uniform gravitational field, ideal spring, Kepler
problem, bead on a rotating hoop, Lorenz attractor, and Hénon-Heiles system.

[x] Verification as of the latest skim: `pytest -q` passes with 145 tests, and
`cd viewer && npm run build` passes. The viewer build emits a non-fatal Vite
chunk-size warning for the main JavaScript bundle.

## Scope

- In: new example systems, reusable generation helpers, manifest/spec
  expansion, better existing lenses, focused visual primitives, tests and
  regenerated data.
- Out: real-time Python server, high-performance solvers, binary data formats,
  full viewer redesign.

## Action items

[x] Pick and add the next examples with visual payoff and backend fit. The repo
now includes bead on hoop, Lorenz attractor, and Hénon-Heiles in addition to the
original mechanics examples.

[x] Add a small reusable generator helper around
`engine.numerics.integrate_fixed_step`, `Trajectory.from_arrays`, parameter
defaults, viewer-copy output, and invariant series sampling.

[x] Add each completed new example as `systems/<name>.py`, register it in
`scripts/example_specs.py`, and create a focused `scripts/generate_<name>.py`.

[x] Extend lens metadata where needed. Existing reusable lens kinds cover most
examples, and newer lens kinds now include `attractor-3d`, `potential-contour`,
and Hamiltonian-flow variants for richer systems.

[x] Improve existing visuals by upgrading reusable primitives in
`viewer/src/threeScene.ts`, `viewer/src/flow.ts`,
`viewer/src/pendulumCanvas.ts`, and
`viewer/src/effectivePotentialCanvas.ts`: animated trail heads, clearer axes,
better scale framing, orbit/field affordances, and less generic background
treatment.

[x] Run the Playwright visual test suite against the local Vite server and
inspect generated screenshots for desktop/mobile regressions across all lenses.

[x] Add the first renderer-hints slice where Python already knows the geometry.
These hints are not physics results; they are presentation metadata that lets
the viewer frame each system consistently without hardcoded TypeScript guesses.
Kepler now exports orbit bounds, camera framing, central-body geometry,
radial-ring geometry, and central-force sampling bounds. Bead on hoop now
exports hoop bounds, camera framing, hoop radius/echo geometry, and rotation
axis geometry.

[ ] Extend renderer hints to the remaining high-value scenes: Lorenz attractor
extent/camera, Hénon-Heiles potential-surface framing, charged-particle field
sampling, sphere radius, and gravity-field sampling bounds.

[x] Add symbolic tests for completed new systems' Euler-Lagrange equations,
energy, Noether charges, first-order diagnostics, and effective-potential or
potential-contour reductions where applicable.

[x] Add trajectory tests that verify state schema, JSON export, invariant
flatness, and domain-specific behavior such as staying on a constraint,
preserving angular momentum, or exporting first-order-flow diagnostics.

[x] Regenerate all outputs with `python -m scripts.generate_all_examples` after
the Kepler/bead renderer-hints change, then validate with `pytest -q`, `cd
viewer && npm run build`, and visual tests against the local Vite server.

[ ] Repeat regeneration and validation after the next data/spec change.

## Open questions

- Should the next priority be more examples or making the current nine feel
  substantially better?
- Do you want examples to stay classical-mechanics focused, or start moving
  toward fluids/relativity/field visualizations?

## Next Best Realistic Item

Extend renderer hints to the remaining high-value scenes before adding new
physics. The first slice is implemented for Kepler and bead on hoop, proving
the contract and viewer path. The next realistic improvement is to apply the
same pattern to systems that still have viewer-side scale and sampling guesses.

These hints answer questions like:

- What bounds should an attractor or potential-contour lens use?
- What domain should a sparse field/vector visualization sample?
- What radius should a sphere scene use if the generated system changes?
- What field region should charged-particle and gravity visualizations sample?

Recommended implementation sequence:

1. Add Lorenz renderer hints from its existing exported trajectory bounds.
2. Add Hénon-Heiles renderer hints from `potentialSurface` ranges.
3. Add sphere/charged/gravity hints from existing physical parameters and
   trajectory extents.
4. Keep fallbacks in `viewer/src/threeScene.ts` so old data remains renderable.
5. Regenerate data and rerun `pytest -q`, `cd viewer && npm run build`, and
   `cd viewer && npm run test:visual`.

Latest baseline: `pytest -q`, `cd viewer && npm run build`, and the Playwright
visual suite all pass. The visual suite passed 2 tests covering desktop and
mobile rendering across the registered examples after the Kepler/bead renderer
hints change.
