# Backend Physics Roadmap — Relativity, Relativistic Dynamics & Electrodynamics

This document is the source of truth for backend Direction D: adding covariant
physics depth (special relativity, relativistic particle dynamics, covariant
classical electrodynamics, and a thin field-theoretic layer) to the
theory-first engine. It is the design the `BE-114..BE-134` task-queue items
implement against.

The thesis is unchanged (`docs/VISION.md`): **Python is the source of
mathematical truth** and computes + exports deterministic data; **TypeScript
renders**. New capability crosses the boundary as documented manifest/export
schema and renderer hints, never as physics re-derived in the viewer. Frontend
rendering of these primitives is tracked separately in the frontend queue
(Direction D, `FE-067..FE-072`).

## 1. Audit — what already exists and is reused

This direction is deliberately additive: it **reuses** existing abstractions
rather than re-deriving tensor or field machinery. The relevant existing
modules are:

- `engine/dynamics/metric.py` — `MetricGeometry` holds metric coefficients
  `g_ij(q)` on a chart and is **signature-agnostic** (its docstring states "the
  formulas do not depend on signature"). It already provides the inverse
  metric, Christoffel symbols, geodesic equation as a `FirstOrderSystem`,
  curvature tensors, parallel transport, and measured geodesic-deviation
  diagnostics. Minkowski space is a constant Lorentzian metric, so the new
  relativity layer builds on `MetricGeometry` instead of a new tensor engine.
- `engine/dynamics/first_order.py` — `FirstOrderSystem` (`dx/dt = f(t, x;
  params)`), the common integration target. Every new dynamical system reduces
  to this.
- `engine/dynamics/diagnostics.py` — `invariant_residuals(...)` summarizes
  **measured** numerical drift for sampled invariant series. Every new physical
  invariant (interval, four-velocity norm², mass-shell, EM invariants) flows
  through this as `measured` evidence (rigor-ladder level 1).
- `engine/fields/fields.py` — `ScalarField` / `VectorField` value objects with
  `gradient`, `divergence`, `curl`, `laplacian`. Reused by the EM field
  containers and the field-density layer.
- `engine/fields/diagnostics.py` — measured field diagnostics:
  `MeasuredFieldGrid`, `MeasuredFieldIntegral`, `MeasuredFieldLawCheck` (law in
  `{"gauss", "stokes"}`), `measured_divergence_grid`, and
  `measured_curl_grid`. All enforce `rigor="measured"`. Reused for Maxwell
  source-constraint diagnostics (`div B = 0`, `div E = rho/eps0`).
- `engine/verification/ir.py` — the backend-agnostic verification IR. Physical
  constraints become `AssumptionSpec` (preconditions; `role` in `domain`,
  `parameter-domain`, `regularity`, `model`); conservation/constraint claims
  become `ObligationSpec` (canonical `expression comparison rhs`, hard-pinned
  to `rigor="external-required"` — obligations can never self-discharge);
  certificate proposals become `CandidateSpec` (`status="candidate"`).
- `engine/export/manifest.py` / `engine/export/trajectory.py` — the JSON
  manifest/trajectory contracts. `system_kind` defaults to `"mechanics"`; this
  direction adds new kinds (`relativistic-worldline`, `covariant-em`,
  `field-density`) through the same contract.
- `systems/charged_particle.py` and `systems/electromagnetic_field.py` — the
  existing **non-relativistic** charged-particle and static-field systems, kept
  as the Newtonian counterparts; the relativistic systems generalize, not
  replace, them.
- `scripts/example_specs.py` / `scripts/generate_all_examples.py` — thin
  generation entry points; new systems register here.

No existing module is modified by `BE-114`. Later tasks **extend** named
modules (e.g. `engine/relativity/worldline.py` in `BE-121`) but introduce no
breaking changes to the audited abstractions above.

## 2. Scope interpretation

"Covariant physics depth" here means classical, deterministic, exactly the
physics the existing pipeline can carry honestly:

- **In scope:** special-relativity kinematics (Minkowski metric, four-vectors,
  Lorentz transforms), proper-time particle dynamics, covariant Lorentz force,
  the Faraday tensor and its invariants, the four-potential and gauge freedom,
  and a **symbolic + sampled** scalar field-density layer (Euler–Lagrange and
  stress-energy structure only).
- **Out of scope (non-goals, §8):** any PDE time-stepping solver, quantum field
  theory, QED, second quantization, numerical relativity / dynamical
  spacetimes, and any claim of proof or certification from simulation. Sampling
  is evidence, never a theorem.

Units: relativistic systems use a single documented convention (geometrized
`c = 1` unless a system states otherwise), matching the existing
`schwarzschild_metric` geometrized-units convention in
`engine/dynamics/metric.py`.

## 3. Ranked candidates (why this ordering)

Tasks are ranked by **implementation readiness**: foundations that other tasks
import come first, then systems that consume them, then export/verification
integration. Within Direction D the dependency spine is:

1. Minkowski metric helper (`BE-115`) — needed by everything.
2. Four-vector value object (`BE-116`) — needed by transforms and worldlines.
3. Lorentz transforms (`BE-117`) — needed by twin-paradox and EM frame checks.
4. Proper-time worldline + four-velocity/four-momentum (`BE-118`) — the
   dynamical core reused by every relativistic system.
5. Free-particle and twin-paradox examples (`BE-119`, `BE-120`) — first
   exports, first `system_kind="relativistic-worldline"`.
6. Relativistic dynamics under four-force, hyperbolic motion, potential
   (`BE-121..BE-123`) and its verification wiring (`BE-124`).
7. Electrodynamics: Faraday tensor, four-potential, covariant Lorentz force,
   then cyclotron / E×B / general charged-particle systems and Maxwell
   diagnostics (`BE-125..BE-131`).
8. Thin field-density layer (`BE-132..BE-134`).

## 4. Phases

The phases mirror the task-queue grouping and are gated: a phase's systems
depend on the prior phase's primitives.

- **Phase 1 — Special-relativity primitives** (`engine/relativity/`):
  `BE-115` Minkowski metric, `BE-116` four-vector, `BE-117` Lorentz
  transforms, `BE-118` proper-time worldline, `BE-119` free-particle export,
  `BE-120` twin paradox.
- **Phase 2 — Relativistic particle dynamics**: `BE-121` four-force dynamics +
  mass-shell, `BE-122` uniform proper acceleration, `BE-123` particle in a
  potential, `BE-124` mass-shell/four-momentum verification export.
- **Phase 3 — Covariant classical electrodynamics**
  (`engine/electrodynamics/`): `BE-125` Faraday tensor + invariants, `BE-126`
  four-potential + gauge, `BE-127` covariant Lorentz force, `BE-128`
  relativistic cyclotron, `BE-129` E×B drift, `BE-130` general relativistic
  charged particle, `BE-131` Maxwell source diagnostics + EM obligations.
- **Phase 4 — Thin field-theoretic abstractions** (`engine/fieldtheory/`;
  symbolic + sampled only, **no PDE solver**): `BE-132` Lagrangian
  field-density + Euler–Lagrange, `BE-133` symbolic stress-energy + measured
  conservation residual, `BE-134` scalar field-density example + export.
- **Phase 5 — Quantum exploratory** (`BE-135`): **DEFERRED / RESEARCH-GATED —
  DO NOT START.** See §9.

## 5. Module structure

New backend packages (no new third-party dependencies; SymPy/NumPy/SciPy
suffice):

```
engine/relativity/
  __init__.py
  minkowski.py        # BE-115: signature convention + Lorentzian metric helper
  four_vectors.py     # BE-116: FourVector value object
  lorentz.py          # BE-117: boosts, rotations, velocity addition
  worldline.py        # BE-118 (+ BE-121 extend): proper-time worldline,
                      #          four-velocity/-momentum, four-force dynamics

engine/electrodynamics/
  __init__.py
  field_tensor.py     # BE-125: F_mu_nu and its invariants
  four_potential.py   # BE-126: A_mu, F = dA, gauge transform
  lorentz_force.py    # BE-127: covariant Lorentz force as a FirstOrderSystem

engine/fieldtheory/
  density.py          # BE-132: L(phi, d_mu phi, x) + symbolic Euler-Lagrange
                      # BE-133 extends: symbolic T_mu_nu + measured residual
```

`systems/` gains thin, symbolic definitions only (`relativistic_free_particle`,
`twin_paradox`, `uniform_proper_acceleration`,
`relativistic_particle_in_potential`, `relativistic_cyclotron`,
`crossed_eb_drift`, `relativistic_charged_particle`, `scalar_field_density`),
each with a generator and an entry in `scripts/example_specs.py`.

## 6. Example systems and exports

| Task | System | `system_kind` | Headline measured invariants |
|------|--------|---------------|------------------------------|
| BE-119 | relativistic free particle | `relativistic-worldline` | invariant interval |
| BE-120 | twin paradox | `relativistic-worldline` | proper-time totals |
| BE-122 | uniform proper acceleration | `relativistic-worldline` | four-velocity norm² (`-c^2`) |
| BE-123 | relativistic particle in a potential | `relativistic-worldline` | energy-type invariant, mass-shell |
| BE-128 | relativistic cyclotron | `covariant-em` | `p_z`, EM invariants |
| BE-129 | crossed E×B drift | `covariant-em` | drift velocity vs `E×B/B^2` |
| BE-130 | general relativistic charged particle | `covariant-em` | mass-shell, four-velocity norm², EM invariants |
| BE-134 | scalar field-density | `field-density` | sampled `d_mu T^mu_nu` residual |

All exports are deterministic and regenerable; generated data stays uncommitted
under `data/generated/` and `viewer/public/data/*.json`.

## 7. Tests

Each task lands focused tests under `tests/` (e.g. `tests/test_minkowski.py`,
`tests/test_four_vectors.py`, `tests/test_lorentz.py`,
`tests/test_worldline.py`, ...). The discipline:

- Symbolic identities are checked symbolically (e.g. `Lambda^T eta Lambda ==
  eta`, four-velocity norm² `= -c^2`, `F` antisymmetric, `dF = 0`, gauge
  invariance of `F`).
- Numerical invariants are checked as **measured** residuals through
  `invariant_residuals(...)` and asserted to integrator tolerance — never
  asserted as exact theorems.
- Closed-form comparisons (hyperbolic worldline, twin proper-time difference,
  `E×B/B^2` drift, gyrofrequency `qB/(gamma m)`) are checked within tolerance.
- Non-relativistic limits are checked against the existing Newtonian systems
  (`charged_particle.py`, etc.).
- Manifests round-trip for every new `system_kind`.

`pytest -q` stays green at every task boundary.

## 8. Verification-export implications

Relativistic and EM systems participate in the existing verification pipeline
**without claiming proof**:

- Physical preconditions (mass-shell `p^mu p_mu + m^2 c^2 = 0`, sub-luminal,
  gauge condition, exterior domain) are `AssumptionSpec`s with the appropriate
  `role`.
- Conservation/constraint claims (four-momentum conservation, mass-shell, EM
  invariants) are `ObligationSpec`s, always `rigor="external-required"`, with
  **measured** statuses computed from rollouts — never self-discharged, never
  rendered as proved or certified.
- Measured Maxwell source-constraint residuals (`div B = 0`, `div E =
  rho/eps0`) reuse the `engine/fields/diagnostics.py` measured checks.

This keeps the rigor-ladder distinction intact: symbolic identity vs measured
numerical evidence vs externally required obligation vs certified/proved.

## 9. Risks and non-goals

- **No PDE solver / no QFT.** Phase 4 is symbolic structure plus sampling only.
  Phase 5 (`BE-135`) is a research placeholder and **must not be started**
  until Phases 1–3 land and a concrete verification use-case justifies it, with
  an explicit go-ahead recorded here.
- **Signature-convention drift.** A single global signature convention
  (`(-,+,+,+)`) is defined once in `engine/relativity/minkowski.py` and reused;
  every four-vector norm and interval references it.
- **Overstated rigor.** Sampled diagnostics are always labeled `measured`;
  nothing in this direction may read as proved, safe, or certified.
- **Boundary erosion.** No physics is re-derived in the viewer; all new
  capability arrives as documented manifest/export schema and renderer hints.
- **Domain coupling.** This direction stays decoupled from the verification/CPS
  track (no shared modules, no cross-links, no drone-specific coupling).

## 10. Checklist (near-term, actionable)

Phase 1:
- [x] BE-114 — land this roadmap.
- [x] BE-115 — Minkowski metric helper (`engine/relativity/minkowski.py`).
- [x] BE-116 — four-vector value object (`engine/relativity/four_vectors.py`).
- [x] BE-117 — Lorentz transformations (`engine/relativity/lorentz.py`).
- [x] BE-118 — proper-time worldline with four-velocity/four-momentum (`engine/relativity/worldline.py`).
- [x] BE-119 — relativistic free-particle system + export.
- [x] BE-120 — twin-paradox proper-time comparison example.

Phase 2:
- [x] BE-121 — relativistic particle under an external four-force.
- [ ] BE-122 — uniform-proper-acceleration (hyperbolic motion) system.
- [ ] BE-123 — relativistic particle in a static potential.
- [ ] BE-124 — four-momentum/mass-shell verification export.

Phase 3:
- [ ] BE-125 — Faraday field tensor + invariants.
- [ ] BE-126 — four-potential + gauge transform.
- [ ] BE-127 — covariant Lorentz force as a first-order system.
- [ ] BE-128 — relativistic cyclotron (uniform B).
- [ ] BE-129 — crossed-field E×B drift.
- [ ] BE-130 — general relativistic charged-particle system.
- [ ] BE-131 — Maxwell source-constraint diagnostics + EM-invariant obligations.

Phase 4:
- [ ] BE-132 — Lagrangian field-density + symbolic Euler–Lagrange.
- [ ] BE-133 — symbolic stress-energy + measured conservation residual.
- [ ] BE-134 — scalar field-density example + export.

Deferred / research-gated (DO NOT START):
- [ ] BE-135 — finite-dimensional Hilbert / spin-precession toy. Promoted to a
  real task only with an explicit go-ahead and a stated justification recorded
  in this roadmap.
