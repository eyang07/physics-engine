# Task Queue

This file is the shared implementation queue for coding agents working in this
repository. Tasks are ranked in the order they should be attempted, with the
most immediately implementable task first in each section.

## Agent Workflow

- Pick exactly one task from either the frontend or backend queue.
- Before editing, verify that the task still matches the current repository
  state and does not duplicate uncommitted work.
- Keep the Python-to-TypeScript boundary intact: Python computes and exports;
  TypeScript renders generated data.
- When the task is complete, remove it from this queue in the same change.
- Do not add tasks for generated data under `data/generated/` or
  `viewer/public/data/*.json`.

## Task Format

Each task should use this structure:

```md
1. **TASK-ID: Short imperative title**
   - Goal: One sentence describing the outcome.
   - Scope: Main files or modules expected to change.
   - Acceptance: Concrete checks, tests, or visible behavior that prove the task
     is done.
```

## Frontend Queue

_Active frontend work is Systems-domain rendering only. The viewer renders
backend-generated manifest/trajectory data and **must not re-derive physics**;
new capability arrives as documented renderer hints and export channels, drawn by
the viewer, never recomputed in it._

_Keep the existing honesty discipline: qualitative readouts with no raw decimals,
consistent on-stage legends, renderer-hint-driven framing, and measured results
labeled as measured._

### Direction D — Relativity & electrodynamics rendering

_Render the special-relativity, relativistic-dynamics, and covariant-electrodynamics
exports produced by backend Direction D. The viewer draws backend-generated
worldlines, spacetime diagrams, relativistic trajectories,
and field/invariant readouts and **must not re-derive physics** — Lorentz transforms,
proper time, four-momentum, and EM invariants are computed in Python and arrive as
manifest/trajectory schema and renderer hints. Each task names the backend export it
consumes and may only start after that export has landed and validated._

1. **FE-068: Surface proper-time vs coordinate-time and the invariant interval readout (consumes BE-118/BE-119)**
   - Goal: Show an honest, qualitative readout of accumulated proper time vs coordinate
     time and the conserved (measured) invariant interval along the worldline.
   - Scope: Systems-domain readout panel/legend, viewer data plumbing, visual test.
   - Acceptance: the interval is shown as a measured conserved quantity;
     proper vs coordinate time are visually distinct; `npm run build` and the visual
     test pass.

2. **FE-069: Render the twin-paradox dual-worldline comparison (consumes BE-120)**
   - Goal: Draw both twin worldlines between shared endpoints with their measured
     proper-time totals contrasted.
   - Scope: reuse the FE-067 spacetime renderer for two worldlines, comparison readout,
     visual test.
   - Acceptance: the accelerated twin's shorter proper time is visible and labeled
     measured; both worldlines share one diagram; `npm run build` and the visual test pass.

3. **FE-070: Render the relativistic charged-particle / cyclotron / E×B trajectories with field glyphs (consumes BE-128/BE-129/BE-130)**
   - Goal: Draw the relativistic charged-particle trajectories alongside the static
     E/B field using the existing vector-glyph/field-line rendering vocabulary.
   - Scope: Systems-domain renderer for `system_kind="covariant-em"`, reuse of existing
     field rendering primitives, visual test.
   - Acceptance: gyration and the E×B drift are visible against the field glyphs from the
     backend export; the viewer does not recompute the trajectory or fields; `npm run
     build` and the visual test pass.

4. **FE-071: Surface the Faraday invariants and mass-shell as qualitative readouts (consumes BE-125/BE-131)**
   - Goal: Show the EM invariants (`F_mu_nu F^mu_nu`, `E·B`) and the mass-shell residual
     as measured, qualitative on-stage readouts with no raw decimal dumps.
   - Scope: Systems-domain legend/readout, viewer data plumbing, visual test.
   - Acceptance: invariants render as measured conserved quantities; nothing reads as
     stronger than measured evidence; `npm run build` and the visual test pass.

5. **FE-072: Render the scalar field-density mode/surface and its measured conservation readout (consumes BE-134)**
   - Goal: Draw the scalar field-density configuration (mode surface) and surface the
     measured stress-energy conservation residual honestly.
   - Scope: Systems-domain renderer for `system_kind="field-density"`, reuse of existing
     surface/mode rendering, visual test.
   - Acceptance: the field-density surface renders from BE-134 export; the conservation
     residual is shown as measured evidence; `npm run build` and the visual test pass.

## Backend Queue

_No backend tasks queued. Backend implementations are marked complete for now._
