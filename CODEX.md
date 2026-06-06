# Plan

Build the next phase around the existing contract: Python defines systems and
generated data, `scripts/example_specs.py` registers gallery metadata/lenses,
and the viewer renders manifest-driven trajectories. The backend already has
Lagrangian/Hamiltonian mechanics, Noether quantities, fixed-step RK4
integration, trajectory JSON export, manifest export, six registered examples,
and tests covering equations, invariants, and manifest shape.

## Scope

- In: new example systems, reusable generation helpers, manifest/spec
  expansion, better existing lenses, focused visual primitives, tests and
  regenerated data.
- Out: real-time Python server, high-performance solvers, binary data formats,
  full viewer redesign.

## Action items

[ ] Pick 3-4 next examples by visual payoff and backend fit: double pendulum,
central-force variants, bead on hoop, driven oscillator, or constrained
pendulum.

[ ] Add a small reusable generator helper around
`engine.numerics.integrate_fixed_step`, `Trajectory.from_arrays`, parameter
defaults, viewer-copy output, and invariant series sampling.

[ ] Add each new example as `systems/<name>.py`, register it in
`scripts/example_specs.py`, and create a focused `scripts/generate_<name>.py`.

[ ] Extend lens metadata only where needed: reuse `configuration-space`,
`configuration-phase`, and `effective-potential` first; add new lens kinds only
for genuinely new visual grammar.

[ ] Improve existing visuals by upgrading reusable primitives in
`viewer/src/threeScene.ts`, `viewer/src/flow.ts`,
`viewer/src/pendulumCanvas.ts`, and
`viewer/src/effectivePotentialCanvas.ts`: animated trail heads, clearer axes,
better scale framing, orbit/field affordances, and less generic background
treatment.

[ ] Make the manifest carry more visual hints where Python already knows the
structure: embedding bounds, central bodies, force-field vectors, constraint
surfaces, or preferred camera framing.

[ ] Add symbolic tests for each new system's Euler-Lagrange equations, energy,
Noether charges, and any effective-potential reductions.

[ ] Add trajectory tests that verify state schema, JSON export, invariant
flatness, and domain-specific behavior such as staying on a constraint or
preserving angular momentum.

[ ] Regenerate all outputs with `python -m scripts.generate_all_examples`, then
validate with `pytest -q`, `cd viewer && npm run build`, and visual tests
against the local Vite server.

## Open questions

- Should the next priority be "more examples quickly" or "make the current six
  feel substantially better"?
- Do you want examples to stay classical-mechanics focused, or start moving
  toward fluids/relativity/field visualizations?
