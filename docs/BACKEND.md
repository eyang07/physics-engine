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
    `rigor="external-required"`. Viewer-facing exports now include a
    top-level manifest `system` cross-reference and measured `regionGeometry`
    scalar-field grids plus boundary polylines for safe/unsafe/initial/domain
    regions.
  - The first viewer-renderable verification pair is
    `upright-pendulum-safety` linked to manifest system `pendulum`; the
    geometry export maps IR variable `omega` to manifest state axis
    `theta_dot` on the `phase` projection.
  - Adapter capability declarations and target-specific obligation
    classification for future verification backends; the inspection stub
    advertises no discharge capability and records required target support in
    diagnostics.
  - Controlled-discrete Lyapunov/barrier verification exports that derive
    obligations on the closed-loop map while preserving the original
    open-loop controlled dynamics, admissible input bounds, and symbolic
    feedback law metadata.
  - Stub inspection adapter (`engine/verification/inspection_adapter.py`) that
    consumes the IR and writes canonical problem JSON, a human-readable
    inspection report, and a machine-readable inspection outcome JSON with
    typed diagnostics. It records no proof results.

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

Backend-only examples include controlled pendulum safety/certificate candidates
and metric-geometry reference systems.

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

Latest known result: `273 passed`.

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
`data/generated/`):

```sh
python -m scripts.export_verification_problems
```

Generated outputs under `data/generated/` and `viewer/public/data/*.json` are
ignored and should not be committed.

## Next Work

1. Continue hardening backend verification foundations: richer target-specific
   adapter checks and robustness tests before adding more case-study breadth.
2. Extend parameter variants beyond Lorenz once the viewer has clear behavior
   for backend-generated variants.
3. Keep backend-only geodesic exploration outside the gallery until the viewer
   can render the geometry honestly.
