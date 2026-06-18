# Backend Status

The backend is the Python source of truth for mathematical structure,
simulation, diagnostics, generated data, safety metadata, and verification
artifacts.

## Current Capabilities

- Analytical mechanics:
  - Lagrangian and Hamiltonian systems.
  - Euler-Lagrange equations, Legendre transforms, energy, Noether charges,
    Poisson brackets, symplectic utilities, constraints, and coordinate
    transforms.
- General dynamics:
  - First-order systems `dx/dt = f(t, x; params)`.
  - Symbolic Jacobians, divergence, fixed points, linearization, and numerical
    RHS generation.
  - Adaptive and fixed-step integration, plus symplectic integration
    (symplectic Euler, Störmer-Verlet) for separable Hamiltonians with a
    symbolic separability check (spec in `docs/symplectic-integrators.md`).
- Controlled dynamics:
  - Continuous controlled systems `dx/dt = f(t, x, u, d; params)`.
  - Discrete-time controlled systems `x_{k+1} = F(k, x_k, u_k, d_k; params)`
    (spec in `docs/discrete-dynamics.md`), including forward-Euler
    discretization of autonomous continuous systems.
  - Box-shaped admissible control/disturbance sets.
  - Closed-loop reduction to `FirstOrderSystem` / `DiscreteSystem`.
  - Deterministic rollouts with measured bound violations, never silent
    clipping.
- Geometry and rays:
  - Cotangent Hamiltonian systems.
  - Ray-bundle integration/export.
  - Parameterized scalar-speed, refractive-index, and inverse-metric media.
  - Metric geometry helpers for fixed-background geodesics.
- Diagnostics:
  - Invariant residuals.
  - Poincare sections.
  - Finite-time Lyapunov exponent estimates.
  - Ray travel time, caustic proximity, and wavefront envelope metadata.
- Export:
  - Deterministic trajectory JSON.
  - Manifest registry with parameters, state schema, projections, conserved
    quantities, effective potentials, renderer hints, diagnostics, lenses, and
    precomputed variants.
- Safety and verification:
  - Safe/unsafe sublevel sets and measured trajectory safety reports.
  - Event-based unsafe-set entry detection
    (`SafetySpecification.event_entry_report`, spec in
    `docs/event-detection.md`): entry times located by integrator
    root-finding on the unsafe margin, sharp to integration tolerance rather
    than snapped to a sample grid, built on the reusable
    `integrate_with_events` primitive. Still measured, not validated numerics.
  - Candidate Lyapunov and barrier functions.
  - Continuous and discrete Lyapunov/barrier proof obligations:
    `dV/dt <= 0`, `dB/dt <= 0`, and one-step analogues
    `V(F(k, x)) - V(k, x) <= 0`, `B(F(k, x)) - B(k, x) <= 0`.
  - Candidate generation (`engine/dynamics/candidates.py`, spec in
    `docs/candidate-generation.md`): quadratic Lyapunov candidates from a
    Hurwitz linearization via the Lyapunov equation, sublevel barrier
    candidates from Lyapunov candidates, and measured grid-infimum level
    suggestions.
  - Proof-obligation records and deterministic sampled checks labeled
    `rigor="measured"`.
  - Backend-agnostic verification-problem IR v3 in `engine.verification`
    (spec in `docs/verification-ir.md`): continuous and discrete dynamics,
    control/disturbance channels, explicit assumptions, first-class candidate
    certificates locked to `status="candidate"`, and obligations labeled
    `rigor="external-required"`. Viewer-facing verification exports are
    self-contained and include measured `regionGeometry` scalar-field grids plus
    boundary polylines for safe/unsafe/initial/domain regions.
  - Certified-numeric enclosure statuses for selected Tier-1 drone geofence
    obligations, all still `externalStatus="external-required"`: exact-rational
    interval enclosures close initial containment, guard-partitioned
    forward-invariance / velocity-bound boxes, and a conservative coast-core box
    for the inner-set one-step obligation. Any box whose enclosure does not
    close remains measured-only / external-required, never promoted to a false
    safety verdict.
  - Certified-numeric set-valued enclosures for the horizontal and vertical
    Tier-3 disturbed geofence-axis packages: exact-rational boxes include the
    disturbance parameter (`w1` or `w3`) and close the robust forward-invariance
    and robust velocity-bound obligations over the recorded wind box. Sqrt-bearing
    obstacle/planar robust avoidance remains measured-only until the sqrt
    enclosure path handles it.
  - Certified-numeric sqrt enclosures for the nominal obstacle keep-out and
    geofence∩obstacle packages over a recorded guard-band-interior box
    intersected with the standoff `domainConstraints`. The unconstrained
    rectangle is too loose and includes points outside the standoff predicate;
    the certified-numeric claim is only over the constrained domain. The sqrt
    argument is enclosed exactly, sqrt endpoints use the verified
    outward-rounded mpmath path, and the distance-barrier upper endpoint is
    tightened by the recorded standoff lower bound. Points outside the
    constraint remain measured-only / external-required.
  - Enclosure statuses can record additional domain constraints alongside their
    rectangular box. Constrained certified-numeric producers state claims over
    `box ∩ constraints` explicitly and must still derive sound endpoints through
    the trusted fail-closed evaluator before any status is emitted.
  - The generated cross-package verification summary reports the evidence tier
    per obligation: `certified-numeric` (level 2 enclosure), `measured-only`
    (level 1 sampled evidence), or `external-required` only. It also reports
    worst measured margins separately from worst certified enclosure margins.
    These are catalog fields only; certified-numeric remains a sound enclosure
    under stated assumptions, not proof or safety certification.
  - Cross-package certified-status coverage validation audits published
    `certified-numeric` statuses against their referenced obligations, recorded
    verdict/enclosure margins, soundness assumptions, and (where directly
    re-derivable) the trusted fail-closed evaluator enclosure. Refined
    partitioned, constrained-domain, and set-valued disturbance statuses must
    record the assumptions that justify their tighter enclosure. The report
    catalogs which obligations close at level 2; it does not discharge them.
  - Verification packages can include a non-discharging reachability handoff
    component. The component writes a deterministic `reachability/` directory
    with one JSON artifact per exported one-step enclosure obligation plus an
    index. Each artifact carries the discrete dynamics, recorded exact-rational
    box/domain constraints, and obligation for an external validated-numerics
    backend, with `discharges=false` and `externalStatus="external-required"`.
    Package reads validate these handoff artifacts against the IR and their
    referenced enclosure statuses, rejecting drift or any artifact that claims
    discharge.
  - Viewer-renderable verification examples now include
    `upright-pendulum-safety` and `controlled-spring-regulator-safety`, each
    with its own controlled trajectory, region geometry, candidate-certificate
    series, and sampled `proofStatuses`.
  - Viewer verification generation validates each problem's internal
    region-geometry projection/state-axis mappings, embedded trajectory payload,
    internal problem-payload links, certificate comparison baselines, and
    index-to-problem-file summary counts before writing JSON. These are
    export-contract checks only: they keep renderer data coherent but do not
    prove, certify, or discharge any obligation.
  - Measured certificate diagnostics for the viewer
    (`engine/verification/measured.py`), all `rigor="measured"`: each exported
    controlled trajectory carries time-aligned candidate value (`B(x(t))`) and
    flow-derivative (`dB/dt` from the verification dynamics) `series`, joined
    back to the problem through `certificateSeries`
    (`problemId`, `candidateId`, `obligationIds`, comparison baselines). The
    verification problem exports sampled region-grid `proofStatuses`, one per
    obligation surface, each with a machine-readable status
    (`measured-holds` / `measured-violated` / `external-required`), evaluation
    source, sample count, and worst sampled value/point. These are sampled
    evidence only and keep `externalStatus="external-required"` distinct from
    the sampled status — never a proof or certificate.
  - Adapter capability declarations and target-specific obligation
    classification for future verification backends, including machine-readable
    support checks for target family, dynamics kind, candidate kind, and
    obligation shape features. The inspection stub advertises no discharge
    capability and records required external support in diagnostics.
  - SOS-polynomial structural requirement diagnostics for future certificate
    adapters. These check polynomial compatibility only; they do not attempt or
    record proof discharge.
  - Controlled-discrete Lyapunov/barrier verification exports that derive
    obligations on the closed-loop map while preserving the original
    open-loop controlled dynamics, admissible input bounds, and symbolic
    feedback law metadata. The backend inspection artifact script includes a
    controlled-discrete Lyapunov fixture so this path is covered outside
    unit-only IR tests.
  - Stub inspection adapter (`engine/verification/inspection_adapter.py`) that
    consumes the IR and writes canonical problem JSON, a human-readable
    inspection report, and a machine-readable inspection outcome JSON with
    typed diagnostics. The export script also writes a deterministic inspection
    artifact index for backend-only discovery. It records no proof results.

The backend does not synthesize, prove, or certify safety. Real external
verification backends, proof discharge, validated numerics, and viewer safety
surfaces remain future work.

## Registered Viewer Examples

- Simple pendulum
- Geodesic on a sphere
- Charged particle in a uniform magnetic field
- Uniform gravitational field
- Ideal spring
- Kepler problem
- Bead on a rotating hoop
- Lorenz attractor
- Hénon-Heiles system
- Variable-speed wavefront propagation

Backend-only examples include controlled pendulum and controlled spring
safety/certificate candidates and metric-geometry reference systems.

## Scope

- In: engine abstractions, symbolic system definitions, generator helpers,
  manifest/export contracts, diagnostics, safety metadata, verification IR,
  backend tests, and renderer-hint production.
- Out: TypeScript rendering behavior, UI controls, layout, and Playwright-only
  visual polish. Those belong in `docs/FRONTEND.md`.

## Verification

Current backend baseline:

```sh
pytest -q
```

Latest known result: `357 passed`.

Use focused tests while iterating:

```sh
pytest tests/test_controlled_dynamics.py tests/test_discrete_dynamics.py -q
pytest tests/test_safety_certificates.py tests/test_verification_ir.py -q
pytest tests/test_event_detection.py -q
pytest tests/test_candidate_generation.py tests/test_inspection_adapter.py -q
pytest tests/test_symplectic_integrators.py -q
```

Regenerate data when backend output changes:

```sh
python -m scripts.generate_all_examples
```

Export verification-problem inspection artifacts (backend-only, ignored under
`data/generated/`). This writes per-problem JSON/Markdown/outcome artifacts and
`inspection-artifacts.index.json`:

```sh
python -m scripts.export_verification_problems
```

Generated outputs under `data/generated/` and `viewer/public/data/*.json` are
ignored and should not be committed.

## Next Work

1. Continue hardening backend verification foundations: richer target-specific
   adapter checks and robustness tests before adding more case-study breadth.
2. Factor shared parameter-variant generation helpers if more systems add
   backend-generated parameter families.
3. Keep backend-only geodesic exploration outside the gallery until the viewer
   can render the geometry honestly.
