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

_**Direction change — render the new physics (mirrors the backend pivot).** The
Verification view stays as built, but the frontend's active work now follows the
physics-for-visualization backend directions (BE-082..BE-106). The viewer renders
backend-generated manifest/trajectory data and **must not re-derive physics**; new
capability arrives as documented renderer hints and export channels, drawn by the
viewer, never recomputed in it._

_**Reuse, don't duplicate (VISION §9).** The three physics families below compose a
small shared rendering vocabulary rather than three bespoke render stacks. Build the
foundation block (FE-037..FE-039) first; the family lenses depend on it. Keep the
existing honesty discipline: qualitative readouts with no raw decimals, consistent
on-stage legends, and renderer-hint-driven framing._

_**Strict dependency on backend exports.** Each family task names the `BE-0xx` task
whose export it consumes; pick it up only after that backend export has landed and
validated. The viewer renders the schema — it never invents UI against unstable or
absent data. This direction stays decoupled from the Verification domain (no
cross-links, no Systems-side safety overlay)._

### Direction D — Relativity & electrodynamics rendering

_Render the special-relativity, relativistic-dynamics, and covariant-electrodynamics
exports produced by backend Direction D (`BACKEND_PHYSICS_ROADMAP.md`). The viewer
draws backend-generated worldlines, spacetime diagrams, relativistic trajectories,
and field/invariant readouts and **must not re-derive physics** — Lorentz transforms,
proper time, four-momentum, and EM invariants are computed in Python and arrive as
manifest/trajectory schema and renderer hints. Each task names the `BE-1xx` task whose
export it consumes and may only start after that export has landed and validated. Keep
the existing honesty discipline: qualitative on-stage legends, no raw decimal dumps,
renderer-hint-driven framing; measured invariants are shown as measured. This direction
stays decoupled from the Verification domain (no cross-links, no safety overlay)._

1. **FE-068: Surface proper-time vs coordinate-time and the invariant interval readout (consumes BE-118/BE-119)**
   - Goal: Show an honest, qualitative readout of accumulated proper time vs coordinate
     time and the conserved (measured) invariant interval along the worldline.
   - Scope: Systems-domain readout panel/legend, viewer data plumbing, visual test.
   - Acceptance: the interval is shown as a measured conserved quantity (not "proved");
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
     proved or certified; `npm run build` and the visual test pass.

5. **FE-072: Render the scalar field-density mode/surface and its measured conservation readout (consumes BE-134)**
   - Goal: Draw the scalar field-density configuration (mode surface) and surface the
     measured stress-energy conservation residual honestly.
   - Scope: Systems-domain renderer for `system_kind="field-density"`, reuse of existing
     surface/mode rendering, visual test.
   - Acceptance: the field-density surface renders from BE-134 export; the conservation
     residual is shown as measured evidence; `npm run build` and the visual test pass.

## Backend Queue

_**Direction change — back to the physics engine for visualizations (VISION §3,
§9, §13).** The verification/CPS line (BE-070s) is paused. The backend now returns
to its theory-first mechanics core and grows the physics that the viewer can
render. The thesis is unchanged: Python is the source of mathematical truth and
computes + exports deterministic data; TypeScript renders. New capability crosses
the boundary as documented manifest/export schema and renderer hints, never as
physics re-derived in the viewer. Actual TypeScript rendering of these new
primitives is tracked separately in the frontend queue; these backend tasks
deliver the math, the deterministic export, and the schema contract._

_Three coherent directions, each grounded in existing modules. Tasks are ordered
by implementation readiness within each direction: foundations first, then systems
that use them, then the export/schema that carries them to the viewer. Conserved
quantities and structural identities are first-class; conservation/structure
**diagnostics computed from rollouts stay labeled `measured`** (level 1 evidence),
consistent with the rigor ladder — a clean energy trace is evidence, not a
theorem. Keep `systems/` definitions thin and symbolic, reusable logic in
`engine/`, and generated data uncommitted._

_This direction stays cleanly separated from the verification/CPS track: no
shared modules, no cross-links, no drone-specific coupling._

### Direction B — Fields, waves & continuum

_Lift the engine from particle trajectories to fields over space and to wave
phenomena. Builds on `engine/dynamics/media.py`, `ray_bundle.py`, `ray_diagnostics.py`,
and `variable_speed_wavefront`, and gives the viewer genuinely new visual primitives
(scalar fields, vector glyphs, field lines, mode shapes, wavefront surfaces)._

### Direction D — Relativity, relativistic dynamics & electrodynamics

_Add covariant physics depth along the staged path in `BACKEND_PHYSICS_ROADMAP.md`:
special-relativity primitives, then relativistic particle dynamics, then covariant
classical electrodynamics, then a thin field-density layer, with a deferred quantum
sketch. New abstractions live in two new packages, `engine/relativity/` and
`engine/electrodynamics/`, and **reuse** the existing signature-agnostic
`engine/dynamics/metric.py` (Minkowski is a constant Lorentzian metric) and the
`engine/fields/` calculus + measured Gauss/Stokes checks. Every new physical
invariant flows through the existing pipeline: conserved quantities as `Conserved`/
`series` with **measured** `invariant_residuals`; physical constraints (mass-shell,
sub-luminal, gauge condition, exterior domain) as `AssumptionSpec`; conservation/
constraint claims as `ObligationSpec` (`rigor="external-required"`, never
self-discharged). Keep `systems/` thin and symbolic, reusable logic in `engine/`,
generated data uncommitted, and add no new dependencies (SymPy/NumPy/SciPy suffice).
Tasks are ordered by readiness: foundations first, then the systems that use them,
then export/verification integration. This direction stays decoupled from the
verification/CPS track (no shared modules, no cross-links)._

_Phase 0 (`BE-114`, roadmap), Phase 1 (`BE-115`..`BE-120`), and Phase 2
(`BE-121`..`BE-124`, relativistic particle dynamics + mass-shell/four-momentum
verification export) have landed; the roadmap lives at
[`BACKEND_PHYSICS_ROADMAP.md`](BACKEND_PHYSICS_ROADMAP.md), with the helpers at
`engine/relativity/minkowski.py`, `engine/relativity/four_vectors.py`,
`engine/relativity/lorentz.py`, and `engine/relativity/worldline.py`, and the
mass-shell/four-momentum obligation glue at
`engine/verification/relativity_adapter.py`._

#### Phase 3 — Covariant classical electrodynamics (`engine/electrodynamics/`)

1. **BE-130: Add the general relativistic charged-particle system**
    - Goal: A charged particle in a configurable static EM field via the covariant Lorentz
      force, the flagship Phase-3 example; the existing non-relativistic
      `charged_particle.py` is kept as the Newtonian counterpart.
    - Scope: `systems/relativistic_charged_particle.py` (new), generator,
      `scripts/example_specs.py`, `tests/`.
    - Acceptance: trajectory + manifest deterministic; mass-shell, four-velocity norm²,
      and EM invariants exported as measured series; the non-relativistic limit matches
      `charged_particle.py`; tests pass.

2. **BE-131: Add Maxwell-source constraint diagnostics and EM-invariant obligations**
    - Goal: Reuse the existing measured Gauss-flux/planar-Stokes/div-curl checks in
      `engine/fields/diagnostics.py` to report Maxwell source constraints (`div B = 0`,
      `div E = rho/eps0`) for EM systems, and surface EM invariants as external-required
      obligations with measured statuses.
    - Scope: generator integration with `engine/fields/diagnostics.py`,
      `engine/verification/` glue, `tests/`.
    - Acceptance: an EM system reports measured source-constraint residuals and emits
      EM-invariant obligations (`rigor="external-required"`, measured-holds); no claim of
      proof or certification; tests pass.

#### Phase 4 — Thin field-theoretic abstractions (symbolic + sampled only; no PDE solver)

3. **BE-132: Add a Lagrangian field-density object with symbolic Euler-Lagrange**
    - Goal: A minimal field-density value object `L(phi, d_mu phi, x)` that produces the
      symbolic Euler-Lagrange equation for one scalar field — structure only, **no**
      time-stepping PDE integrator.
    - Scope: `engine/fieldtheory/density.py` (new), `tests/`.
    - Acceptance: the Euler-Lagrange expression for a Klein-Gordon-style density matches
      by hand; the object validates free symbols like the existing fields; tests pass.

4. **BE-133: Add symbolic stress-energy and a measured conservation residual**
    - Goal: Symbolic `T_mu_nu` for a scalar field density plus a **measured** sampled
      `d_mu T^mu_nu` residual over field configurations, consistent with the rigor ladder
      (sampling is evidence, not a theorem).
    - Scope: `engine/fieldtheory/` (extend), `engine/fields/diagnostics.py` reuse,
      `tests/`.
    - Acceptance: `T_mu_nu` is symmetric for the scalar density; the sampled divergence
      residual is near zero for an on-shell configuration and labeled measured; tests pass.

5. **BE-134: Add the scalar field-density example and export**
    - Goal: A Klein-Gordon-style scalar field-density gallery system exporting its
      density, Euler-Lagrange form, and measured `T_mu_nu` conservation residual under a
      new `system_kind="field-density"`.
    - Scope: `systems/scalar_field_density.py` (new), generator, `scripts/example_specs.py`,
      `tests/`.
    - Acceptance: deterministic export; the manifest round-trips the new `system_kind`;
      the measured conservation residual is surfaced honestly; tests pass.

#### Phase 5 — Quantum exploratory (DEFERRED / RESEARCH-GATED — DO NOT START)

6. **BE-135: (UNSCHEDULED, gated) Sketch a finite-dimensional Hilbert / spin-precession toy**
    - Goal: Research placeholder only — a finite-dimensional Hilbert state under a unitary
      `FirstOrderSystem` flow (spin precession), with measured norm/probability
      invariants. **No QED, no QFT, no PDE.** Do not implement until Phases 1-3 have landed
      and a concrete verification use-case justifies it.
    - Scope: none yet (the design sketch lives in `BACKEND_PHYSICS_ROADMAP.md`).
    - Acceptance: this task stays unstarted; it is promoted to a real task only with an
      explicit go-ahead and a stated justification recorded in the roadmap.
