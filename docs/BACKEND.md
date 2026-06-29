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
  - Rigid-body orientation helpers: SO(3) matrices, unit quaternions, ZYX Euler
    angles, and body-frame / space-frame angular-velocity conversions.
  - Inertia tensor value object with principal-axis decomposition and standard
    shape constructors.
  - Euler rigid-body equations in the body frame with constant/callable torque
    inputs and measured rotational-energy / angular-momentum diagnostics.
  - Free asymmetric-top example with measured intermediate-axis instability,
    angular-momentum sphere, kinetic-energy ellipsoid, and sampled polhode
    geometry exported from Python.
  - Heavy symmetric top (gyroscope) in Euler angles with cyclic precession and
    spin: conserved energy and two angular momenta (`p_phi`, `p_psi`), the
    nutation-angle effective potential, and measured precession/nutation motion.
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
  - Metric geometry helpers for fixed-background geodesics, including symbolic
    Christoffel, Riemann, Ricci, and scalar-curvature calculations.
  - Surface-of-revolution geodesic systems (sphere, torus, paraboloid, cone,
    hyperboloid) generated from reusable metric geometry, with measured
    invariant residuals for rollout diagnostics.
  - Parallel transport on sampled metric curves, with 2D holonomy-angle support;
    surface-geodesic exports include a measured transported-frame payload along
    the generated curve.
  - Measured geodesic-deviation diagnostics compare nearby sampled geodesics
    with metric separation/focusing series; these are rollout diagnostics, not
    Jacobi-field proofs.
  - Curvature exports for geometry examples: surface-of-revolution payloads
    include deterministic Gaussian-curvature scalar fields and measured
    Gauss-Bonnet quadrature diagnostics; Schwarzschild payloads include
    deterministic Ricci and Kretschmann scalar fields, plus a Flamm-paraboloid
    embedding mesh for the exterior `r > r_s` (`z = 2 sqrt(r_s (r - r_s))`) and a
    Kretschmann scalar field aligned to that mesh for coloring the funnel.
  - `MetricGeometry.kretschmann_scalar()` returns the symbolic curvature
    invariant `R_abcd R^abcd`; with the full Schwarzschild metric
    (`schwarzschild_metric`, the Ricci-flat 3+1 background) it equals the vacuum
    value `12 r_s^2 / r^6` that the exported Schwarzschild curvature field is
    validated against.
  - Effective-potential orbit helpers for Kepler and fixed-background
    Schwarzschild regimes: Python computes potential samples, analytic turning
    points, and qualitative orbit classification for renderer consumption.
  - Schwarzschild geodesic generator for equatorial timelike and null geodesics,
    exporting measured conserved-energy/angular-momentum residuals, perihelion
    precession and a measured geodesic-deviation (tidal separation) diagnostic
    for the bound timelike preset, photon-sphere/light-bending diagnostics for
    the null preset, and the GR effective potential. The geodesic-deviation block
    integrates a nearby equatorial geodesic and records the metric separation
    along the orbit (`rigor="measured"`), reusing the same
    `MetricGeometry.geodesic_deviation_diagnostic` the wormhole preset uses.
  - Ellis wormhole geodesic generator for a fixed equatorial background,
    exporting an embedding mesh, embedded geodesic curve, a deterministic
    scalar-curvature field over the same throat grid (`R = -2a^2/(a^2+l^2)^2`,
    extremal at the throat `l = 0`), a radial effective potential
    (`V_eff^2 = epsilon + L^2/(l^2+a^2)`) with the throat barrier, analytic
    turning points, and a qualitative traversing/reflected classification,
    measured invariant residuals, and measured throat-traversal diagnostics; it
    does not solve dynamical gravity. Two presets ship as manifest variants: the
    default radial traversal (`L = 0`, clears the throat) and an angular preset
    (`phi_dot0 != 0`, `L != 0`) whose energy sits below the centrifugal barrier
    so it reflects at the analytic turning point and never crosses the throat —
    the measured throat-traversal diagnostic reports `crossesThroat=false`.
  - Coordinate-domain guards for fixed curved backgrounds: each system declares
    its chart's validity domain and the generators reject presets that leave it.
    The Schwarzschild generator rejects geodesics that touch or cross the event
    horizon `r = r_s` (where the exterior coordinates are singular); the wormhole
    generator rejects a non-positive throat radius. Both attach a
    `coordinate-domain` descriptor to the trajectory metadata.
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
  - Optional backend-owned geometry metadata in manifest entries and trajectory
    metadata for renderer-specific structures such as rigid-body polhodes.
  - Surface-geodesic export schema: manifest entries can declare
    `geometry.kind="surface-geodesic"` with `rendererHint="surface-geodesic"`
    and sources for `surfaceMesh`, embedded `geodesic`, and `curvature`
    channels. The trajectory payload carries those under
    `metadata.surfaceGeometry`; mesh and curvature samples are deterministic
    symbolic evaluations, while rollout invariant residuals remain
    `rigor="measured"`.
    `geometry.parallelTransport.source` points to
    `metadata.parallelTransport`, a measured sampled frame transport along the
    exported curve.
    Closed surface payloads also carry `curvatureDiagnostics.gaussBonnet` with
    `rigor="measured"`; it is a quadrature diagnostic, not a proof.
  - Optional rigid-body orientation channel: a trajectory carries a per-sample
    unit-quaternion series (`(w, x, y, z)`, sign-aligned for continuity) and the
    body-frame triad in space coordinates under `trajectory.orientation`, and the
    manifest entry declares it with a `rigid-body` renderer hint. The free
    asymmetric top integrates attitude coupled to Euler's equations; the heavy
    symmetric top derives it from its Euler angles.
  - Field export schema (`engine/export/field_export.py`): deterministic
    `scalar-field` grids (axes + exact sampled values), `vector-field` grids
    (per-node components + magnitude), and `field-lines` polyline payloads, each
    carrying its renderer hint. Manifest entries can declare their `fields`
    channels (name/kind/rendererHint/source). Sampled values are exact
    evaluations of the symbolic field (`evaluation: symbolic-exact`), not measured
    evidence.
  - Effective-potential manifest entries may declare `plotSource`,
    `turningPointsSource`, and `classificationSource` when a generator exports
    the corresponding backend-owned payload. The Kepler example uses this for
    radial turning points and bound/unbound/critical classification.
  - Wormhole manifest entries may declare `geometry.kind="wormhole-geodesic"`
    with sources for an embedding mesh, embedded geodesic, a `scalar-field`
    `curvature` channel, and measured throat-traversal / geodesic-deviation
    diagnostics under `metadata.wormholeGeometry` / `metadata.diagnostics`. The
    curvature samples are deterministic symbolic evaluations and the entry also
    exposes the field through a top-level `fields` declaration
    (`scalarCurvature`, sourced from `metadata.wormholeGeometry.curvature`). The
    same entry also carries an `effective-potential` lens whose `plotSource`
    (`metadata.potentialPlots[name=wormhole_radial]`) and `classificationSource`
    (`metadata.orbitClassification`) expose the radial throat barrier, turning
    points, and a qualitative traversing/reflected class.
  - Schwarzschild manifest entries may declare
    `geometry.kind="schwarzschild-geodesic"` with sources for a Flamm-paraboloid
    embedding mesh (`surface-mesh`), the geodesic lifted onto that funnel
    (`embedded-polyline`), and a `scalar-field` `curvature` channel under
    `metadata.schwarzschildGeometry`. The mesh and Kretschmann curvature samples
    are deterministic symbolic evaluations sharing one `(r, phi)` grid; the mesh
    stays strictly outside the horizon (`r > r_s`). The 1D radial Ricci /
    Kretschmann profiles under `metadata.curvatureScalars` remain available as
    top-level `fields`. The bound timelike entry also declares
    `geometry.diagnostics.geodesicDeviation`
    (`metadata.diagnostics.geodesicDeviation`): a measured tidal-separation series
    against a nearby equatorial geodesic.
  - Fixed-background manifest entries may declare a `domain` channel
    (`kind="coordinate-domain"`, `source="trajectory.metadata.domain"`). The
    trajectory payload carries the matching `metadata.domain` descriptor: the
    chart name, coordinate list, the validity constraints (e.g. Schwarzschild
    `r > r_s`, wormhole throat radius `> 0`), and the relevant reference radii.
    It documents the fixed-background assumptions; it is not a dynamical
    solution.
  - Static-field manifest entries (`systemKind: "static-field"`): systems whose
    payload is a time-independent field export, not a Lagrangian or first-order
    flow, intentionally omit `physics`, `derivation`, and `dynamics`. They expose
    backend-owned field channels through `fields` plus an optional `fieldModel`
    source summary. The electromagnetic field example uses this path for an
    electric-dipole scalar potential, electric/magnetic vector grids, and
    integrated field-line payloads.
  - Field-evolution manifest entries (`systemKind: "field-evolution"`): analytic
    continuum examples whose primary payload is a sampled field over space and
    time. They intentionally omit particle-dynamics derivations and instead
    declare renderer-owned channels such as `scalar-field-series` with
    `rendererHint: "scalar-field"`. The vibrating-string example exports fixed-end
    normal-mode displacement and a d'Alembert traveling Gaussian packet, plus
    measured energy residual metadata. The membrane example exports rectangular
    sine-mode surfaces, circular Bessel-mode drum surfaces, and animated modal
    superpositions with finite masks for points outside the circular domain. The
    dispersive wave-packet example exports analytic amplitude/intensity fields
    under a quadratic dispersion relation, with measured phase/group velocity and
    envelope-spreading diagnostics.
  - Relativistic-worldline manifest entries
    (`systemKind: "relativistic-worldline"`): proper-time worldlines whose
    trajectory payload carries backend-computed spacetime points, four-velocity
    samples, renderer hints for a Minkowski spacetime diagram, and measured
    invariant residuals such as `proper_interval_rate`. These are sampled
    diagnostics, not proof or certification.
  - Field-line / streamline integration (`engine/fields/field_lines.py`): integral
    curves of a vector field's direction (`dx/ds = V/|V|`, unit arc length) via the
    shared RK4 step, with deterministic segment seeding, optional forward+backward
    tracing, and clean termination on the domain box, stagnation points, or listed
    singularities. Produces the polylines the `field-lines` export carries.
  - Variable-speed wavefront exports now include backend-computed
    `wavefront-surface` samples carrying ray-bundle points with measured eikonal
    travel time, plus a `scalar-field-series` intensity proxy derived from
    adjacent-ray spreading. Intensity is measured ray-bundle evidence, not a
    solved wave equation.
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
    reachability handoff artifact counts and worst measured margins separately
    from worst certified enclosure margins. These are catalog fields only;
    certified-numeric remains a sound enclosure under stated assumptions, and a
    reachability handoff is only a non-discharging external-backend input, not
    proof or safety certification.
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
- Geodesic on a surface of revolution
- Charged particle in a uniform magnetic field
- Uniform gravitational field
- Ideal spring
- Coupled oscillators
- Kepler problem
- Schwarzschild geodesic
- Ellis wormhole geodesic
- Bead on a rotating hoop
- Double pendulum
- N-body gravity
- Lorenz attractor
- Hénon-Heiles system
- Electromagnetic static field
- Vibrating string
- Membrane modes
- Dispersive wave packet
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

Latest known result: `777 passed`.

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

The staged relativity/electrodynamics/fields direction is specified in
[`BACKEND_PHYSICS_ROADMAP.md`](../BACKEND_PHYSICS_ROADMAP.md) at the repo root.

1. Continue hardening backend verification foundations: richer target-specific
   adapter checks and robustness tests before adding more case-study breadth.
2. Factor shared parameter-variant generation helpers if more systems add
   backend-generated parameter families.
3. Keep future geometry exports explicit about which payloads are symbolic
   samples, measured rollout diagnostics, or renderer hints.
