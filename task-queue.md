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

### Direction C — Curved-geometry rendering

_No active curved-geometry rendering tasks queued; add the next coherent
geometry/gravitation rendering task here when starting new frontend work._

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

1. **FE-067: Render the relativistic free-particle worldline on a Minkowski spacetime diagram (consumes BE-119)**
   - Goal: Draw a 1+1 (or 2+1) Minkowski spacetime diagram with light cones and the
     backend worldline plotted on it, framed by renderer hints — no physics recomputed
     in the viewer.
   - Scope: a new Systems-domain renderer for `system_kind="relativistic-worldline"`,
     viewer manifest/trajectory consumption, `viewer` visual test.
   - Acceptance: the worldline and light cones render from BE-119 export; the diagram
     reads as a spacetime plot (time axis labeled); `npm run build` and the visual test
     pass; no values are recomputed client-side.

2. **FE-068: Surface proper-time vs coordinate-time and the invariant interval readout (consumes BE-118/BE-119)**
   - Goal: Show an honest, qualitative readout of accumulated proper time vs coordinate
     time and the conserved (measured) invariant interval along the worldline.
   - Scope: Systems-domain readout panel/legend, viewer data plumbing, visual test.
   - Acceptance: the interval is shown as a measured conserved quantity (not "proved");
     proper vs coordinate time are visually distinct; `npm run build` and the visual
     test pass.

3. **FE-069: Render the twin-paradox dual-worldline comparison (consumes BE-120)**
   - Goal: Draw both twin worldlines between shared endpoints with their measured
     proper-time totals contrasted.
   - Scope: reuse the FE-067 spacetime renderer for two worldlines, comparison readout,
     visual test.
   - Acceptance: the accelerated twin's shorter proper time is visible and labeled
     measured; both worldlines share one diagram; `npm run build` and the visual test pass.

4. **FE-070: Render the relativistic charged-particle / cyclotron / E×B trajectories with field glyphs (consumes BE-128/BE-129/BE-130)**
   - Goal: Draw the relativistic charged-particle trajectories alongside the static
     E/B field using the existing vector-glyph/field-line rendering vocabulary.
   - Scope: Systems-domain renderer for `system_kind="covariant-em"`, reuse of existing
     field rendering primitives, visual test.
   - Acceptance: gyration and the E×B drift are visible against the field glyphs from the
     backend export; the viewer does not recompute the trajectory or fields; `npm run
     build` and the visual test pass.

5. **FE-071: Surface the Faraday invariants and mass-shell as qualitative readouts (consumes BE-125/BE-131)**
   - Goal: Show the EM invariants (`F_mu_nu F^mu_nu`, `E·B`) and the mass-shell residual
     as measured, qualitative on-stage readouts with no raw decimal dumps.
   - Scope: Systems-domain legend/readout, viewer data plumbing, visual test.
   - Acceptance: invariants render as measured conserved quantities; nothing reads as
     proved or certified; `npm run build` and the visual test pass.

6. **FE-072: Render the scalar field-density mode/surface and its measured conservation readout (consumes BE-134)**
   - Goal: Draw the scalar field-density configuration (mode surface) and surface the
     measured stress-energy conservation residual honestly.
   - Scope: Systems-domain renderer for `system_kind="field-density"`, reuse of existing
     surface/mode rendering, visual test.
   - Acceptance: the field-density surface renders from BE-134 export; the conservation
     residual is shown as measured evidence; `npm run build` and the visual test pass.

### Verification UI redesign — minimal formal-methods workbench

_Reconfigure the Verification domain shell from the decorative "dossier" register
into a minimal, precise verification workbench. Full design rationale, layout,
vocabulary, visual language, and acceptance criteria live in
[`UI_RECONFIGURATION_PLAN.md`](UI_RECONFIGURATION_PLAN.md). Direction: migrate the
verification shell to **React + Tailwind + Radix** with a **light technical (no
serif)** theme. Each module below is self-contained and should leave `npm run
build` green on its own; pick them up in order (later modules depend on earlier
ones). **Hard constraint:** do not touch the physics animation system — the
Systems domain renderers, numerical integration, trajectory generation, and
`PlaybackClock` playback semantics must behave exactly as today. Keep verification
honesty intact: `external-required`, and measured evidence never rendered as
proved/certified._

1. **FE-062: DocketRail — verification problem list**
   - Goal: A narrow, collapsible problem/package list that drives selection.
   - Scope: `viewer/src/verification/`.
   - Acceptance: selecting a problem loads it; the list scales to a multi-package
     catalog without layout breakage; `npm run build` passes.

2. **FE-063: Apply the light-technical visual language and token deltas (drop serif)**
   - Goal: Remove the serif remap in the `tokens.css` `#verificationDomain` block,
     set the UI font to IBM Plex Sans + mono with KaTeX restricted to math spans,
     surface the Tailwind theme from the existing tokens, and add a `--pending`
     (graphite, dashed) status plus fill/outline variants for proved-vs-measured.
   - Scope: `viewer/src/design/tokens.css`, Tailwind theme config,
     `viewer/src/styles.css` (verification block).
   - Acceptance: no serif prose remains; one type scale; status color is the only
     saturation in the view; `npm run build` passes; verification baselines updated
     intentionally.

3. **FE-064: Replace the four legend overlays with one compact legend and selection linking**
    - Goal: Remove `.verif-violation-legend`, `.verif-holds-legend`,
      `.verif-roles-legend`, and `.verif-disturbance-annotation`; add a single
      collapsible legend showing only the marks present, and link obligation
      selection to plot highlighting (region + margin marker).
    - Scope: `viewer/src/verification/`, `viewer/src/verificationStage.ts` render hooks.
    - Acceptance: the plot is readable without a legend-heavy decode; selecting an
      obligation highlights its geometry and margin marker; `npm run build` passes.

4. **FE-065: Move playback and full detail into a collapsible bottom strip**
    - Goal: Relocate the rollout playback controls and the formal detail (dynamics,
      region definitions, enclosure boxes) into a Radix Collapsible bottom strip,
      collapsed by default, with playback behavior preserved exactly.
    - Scope: `viewer/src/verification/`.
    - Acceptance: playback behaves identically to today; detail is collapsed by
      default; `npm run build` passes.

5. **FE-066: Document the verification UI shell and refresh its visual baselines**
    - Goal: Document the redesigned verification shell and its boundary from the
      physics pipeline, and regenerate the verification-domain visual baselines.
    - Scope: `docs/FRONTEND.md`, `viewer` visual baselines (verification only).
    - Acceptance: `pytest -q`, `npm run build`, and `npm run test:visual` pass;
      Systems baselines unchanged; verification baselines updated deliberately.

### Verification track (paused)

_These two verification-view tasks predate the direction change and are kept for
continuity. They are **deprioritized** while the frontend follows the physics
directions; pick them up only on explicit request._

4. **FE-035: Draw the certified enclosure box on the phase-plane stage**
    - Goal: An obligation's certified-numeric enclosure (FE-032) records the box it
      is sound over in state-variable coordinates, but the stage never shows where
      on the phase plane that box lies. Draw a read-only certified-box overlay on
      the (q1, v1) stage for obligations whose enclosure box is plane-expressible,
      so a reader can see the region the obligation was certified sound over. Draw
      nothing for obligations with no certified enclosure or a non-plane box.
      Honest — "sound over this box under this model", never "safe".
    - Scope: `viewer/src/verificationStage.ts` (certified-box overlay),
      `viewer/src/data/verification.ts` if the box needs exposure to the stage,
      `viewer/src/styles.css`, and the viewer visual test.
    - Acceptance: a package with a plane-expressible certified box shows the box
      overlay on the stage; a package with no certified enclosure shows none; the
      rollout/region rendering is otherwise unchanged; nothing reads as proved;
      `npm run build` and the visual test pass.

5. **FE-036: Surface certified-numeric coverage in the catalog (after a discovery-index certified count)**
    - Goal: The catalog lists every package's region/obligation/candidate counts
      and Tier/regime, but not how many of its obligations reach level 2. Once the
      discovery index carries a per-package certified-numeric count, surface it as
      an honest catalog readout (e.g. "2/4 certified-numeric") so a reader can tell
      which packages climb the rigor ladder without opening them. Read only the
      index count; certified-numeric is a sound enclosure, never proved or safe.
    - Scope: `viewer/src/data/verification.ts` (read the certified count from the
      discovery index), `viewer/src/main.ts` (catalog readout), `viewer/src/
      styles.css`, and the viewer visual test.
    - Acceptance: each catalog entry shows its certified-numeric coverage from the
      index; entries without the count show none; nothing reads as proved;
      `npm run build` and the visual test pass.

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

### Direction C — Geometry & gravitation (geometric mechanics / relativity)

_Deepen the differential-geometry strand: geodesics on curved surfaces and
spacetimes, curvature, parallel transport, and orbital structure. Generalizes
`engine/dynamics/metric.py` (today the 2-sphere and equatorial Schwarzschild) and
`systems/sphere_geodesic.py`, and gives the viewer curved-space trajectories and
embedding diagrams._

_No active physics tasks queued; add the next coherent geometry/gravitation task
here when starting new backend work._

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

_Phase 0 (`BE-114`, roadmap) and Phase 1 `BE-115` (Minkowski metric helper),
`BE-116` (four-vector value object), `BE-117` (Lorentz transformations), and
`BE-118` (proper-time worldline) have landed; the roadmap lives at
[`BACKEND_PHYSICS_ROADMAP.md`](BACKEND_PHYSICS_ROADMAP.md), with the helpers at
`engine/relativity/minkowski.py`, `engine/relativity/four_vectors.py`,
`engine/relativity/lorentz.py`, and `engine/relativity/worldline.py`._

#### Phase 1 — Special-relativity primitives (`engine/relativity/`)

#### Phase 2 — Relativistic particle dynamics

1. **BE-123: Add a relativistic particle in a static potential**
    - Goal: A bound/scattering relativistic trajectory under a scalar/vector potential,
      demonstrating relativistic dynamics beyond constant force.
    - Scope: `systems/relativistic_particle_in_potential.py` (new), generator,
      `scripts/example_specs.py`, `tests/`.
    - Acceptance: an energy-type invariant and mass-shell are tracked as measured series;
      the non-relativistic limit matches the corresponding Newtonian system; tests pass.

2. **BE-124: Wire four-momentum conservation and mass-shell into verification export**
    - Goal: Expose mass-shell and four-momentum conservation as `ObligationSpec`s
      (`rigor="external-required"`) with measured `proofStatuses`, so relativistic
      systems participate in the verification pipeline without claiming proof.
    - Scope: `engine/verification/` integration glue, generator, `tests/`.
    - Acceptance: a relativistic system emits a verification problem whose obligations are
      external-required with measured-holds statuses along the trajectory; nothing reads
      as proved or certified; tests pass.

#### Phase 3 — Covariant classical electrodynamics (`engine/electrodynamics/`)

3. **BE-125: Add the Faraday field tensor and its invariants**
    - Goal: Build `F_mu_nu` from `(E, B)` (and later from `A_mu`) and expose the two EM
      invariants `F_mu_nu F^mu_nu` and `E . B` (`F *F`).
    - Scope: `engine/electrodynamics/field_tensor.py` (new),
      `engine/electrodynamics/__init__.py`, `tests/test_field_tensor.py`.
    - Acceptance: `F` is antisymmetric by construction; the two invariants match the
      `2(B^2 - E^2)` and `E.B` forms symbolically; tests pass.

4. **BE-126: Add the electromagnetic four-potential and gauge transform**
    - Goal: An `A_mu(x)` container with `F = dA` (exterior derivative) and a gauge
      transform `A_mu -> A_mu + d_mu chi` that leaves `F` invariant.
    - Scope: `engine/electrodynamics/four_potential.py` (new),
      `tests/test_four_potential.py`.
    - Acceptance: `F` derived from `A` is antisymmetric and gauge-invariant under a
      symbolic `chi`; the homogeneous Maxwell identity `dF = 0` holds symbolically; tests
      pass.

5. **BE-127: Add the covariant Lorentz force as a first-order system**
    - Goal: `dp^mu/dtau = q F^mu_nu u^nu` reduced to a `FirstOrderSystem` on the
      proper-time-parameterized worldline, reusing the Phase-1/2 primitives.
    - Scope: `engine/electrodynamics/lorentz_force.py` (new),
      `tests/test_lorentz_force.py`.
    - Acceptance: integrating the covariant force preserves four-velocity norm² and
      mass-shell (measured); the low-velocity limit reduces to `q(E + v x B)`
      symbolically; tests pass.

6. **BE-128: Add the relativistic cyclotron system (uniform B)**
    - Goal: A charged particle in a uniform magnetic field showing relativistic gyration,
      generalizing — not replacing — `systems/charged_particle.py`.
    - Scope: `systems/relativistic_cyclotron.py` (new), generator,
      `scripts/example_specs.py`, `tests/`.
    - Acceptance: the gyrofrequency matches `qB/(gamma m)`; `p_z` and the EM invariants
      are measured-conserved; a new `system_kind="covariant-em"` round-trips; tests pass.

7. **BE-129: Add the crossed-field E x B drift system**
    - Goal: A charged particle in crossed uniform E and B fields exhibiting the analytic
      `E x B / B^2` drift.
    - Scope: `systems/crossed_eb_drift.py` (new), generator, `scripts/example_specs.py`,
      `tests/`.
    - Acceptance: the measured drift velocity matches `E x B / B^2` within tolerance;
      deterministic export; tests pass.

8. **BE-130: Add the general relativistic charged-particle system**
    - Goal: A charged particle in a configurable static EM field via the covariant Lorentz
      force, the flagship Phase-3 example; the existing non-relativistic
      `charged_particle.py` is kept as the Newtonian counterpart.
    - Scope: `systems/relativistic_charged_particle.py` (new), generator,
      `scripts/example_specs.py`, `tests/`.
    - Acceptance: trajectory + manifest deterministic; mass-shell, four-velocity norm²,
      and EM invariants exported as measured series; the non-relativistic limit matches
      `charged_particle.py`; tests pass.

9. **BE-131: Add Maxwell-source constraint diagnostics and EM-invariant obligations**
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

10. **BE-132: Add a Lagrangian field-density object with symbolic Euler-Lagrange**
    - Goal: A minimal field-density value object `L(phi, d_mu phi, x)` that produces the
      symbolic Euler-Lagrange equation for one scalar field — structure only, **no**
      time-stepping PDE integrator.
    - Scope: `engine/fieldtheory/density.py` (new), `tests/`.
    - Acceptance: the Euler-Lagrange expression for a Klein-Gordon-style density matches
      by hand; the object validates free symbols like the existing fields; tests pass.

11. **BE-133: Add symbolic stress-energy and a measured conservation residual**
    - Goal: Symbolic `T_mu_nu` for a scalar field density plus a **measured** sampled
      `d_mu T^mu_nu` residual over field configurations, consistent with the rigor ladder
      (sampling is evidence, not a theorem).
    - Scope: `engine/fieldtheory/` (extend), `engine/fields/diagnostics.py` reuse,
      `tests/`.
    - Acceptance: `T_mu_nu` is symmetric for the scalar density; the sampled divergence
      residual is near zero for an on-shell configuration and labeled measured; tests pass.

12. **BE-134: Add the scalar field-density example and export**
    - Goal: A Klein-Gordon-style scalar field-density gallery system exporting its
      density, Euler-Lagrange form, and measured `T_mu_nu` conservation residual under a
      new `system_kind="field-density"`.
    - Scope: `systems/scalar_field_density.py` (new), generator, `scripts/example_specs.py`,
      `tests/`.
    - Acceptance: deterministic export; the manifest round-trips the new `system_kind`;
      the measured conservation residual is surfaced honestly; tests pass.

#### Phase 5 — Quantum exploratory (DEFERRED / RESEARCH-GATED — DO NOT START)

13. **BE-135: (UNSCHEDULED, gated) Sketch a finite-dimensional Hilbert / spin-precession toy**
    - Goal: Research placeholder only — a finite-dimensional Hilbert state under a unitary
      `FirstOrderSystem` flow (spin precession), with measured norm/probability
      invariants. **No QED, no QFT, no PDE.** Do not implement until Phases 1-3 have landed
      and a concrete verification use-case justifies it.
    - Scope: none yet (the design sketch lives in `BACKEND_PHYSICS_ROADMAP.md`).
    - Acceptance: this task stays unstarted; it is promoted to a real task only with an
      explicit go-ahead and a stated justification recorded in the roadmap.

### Verification track (paused)

_These two verification/CPS tasks predate the direction change above and are kept
for continuity. They are **deprioritized** while the backend focuses on the physics
directions; pick them up only if the physics queue is blocked or on explicit
request._

3. **BE-079: Cross-check reachability handoff coverage against certified coverage**
    - Goal: Ensure the reachability handoff inventory stays aligned with the
      certified-status coverage report: every handoff-backed obligation is a real
      certified-numeric obligation, and missing handoffs are reported rather than
      silently ignored.
    - Scope: `engine/export/verification_package.py`,
      `engine/verification/reachability.py`, and `tests/`.
    - Acceptance: a backend validator reports certified obligations with and without
      reachability handoffs; it rejects a handoff for a non-certified obligation; no
      report claims proof or external discharge; focused tests pass.

4. **BE-080: Add a reachability handoff dependency index**
    - Goal: Make each package's reachability handoff prerequisites inspectable
      without opening every artifact, by publishing a deterministic dependency
      index that maps handoffs to obligation ids, enclosure status ids, assumption
      ids, and domain-constraint counts.
    - Scope: `engine/verification/reachability.py`,
      `engine/export/verification_package.py`, and `tests/`.
    - Acceptance: the reachability index lists each artifact's obligation id,
      enclosure status id, obligation assumption ids, domain-constraint count,
      `discharges=false`, and `externalStatus="external-required"`; package
      readback validates the dependency index against the artifacts and IR; no
      entry claims proof, certification, or discharge; focused tests pass.
