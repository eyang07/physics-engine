# Project Vision

## 1. Project Thesis

This project is a **theory-first mechanics workbench**. It starts from analytical
mechanics and dynamical systems as the source of mathematical truth, and treats
that structure — Lagrangians, Hamiltonians, constraints, potentials, symmetries,
conserved quantities, controls, safe sets, and certificate candidates — as the
thing that drives simulation, visualization, and eventual verification artifacts.

Numerical integration is a **derived tool** for exploration and rendering, not
the conceptual foundation. We simulate because it helps us see and probe
structure; the structure comes first.

Refined identity:

> A theory-first mechanics engine that transforms analytical structure into
> visual simulations, certificate candidates, and backend-agnostic proof
> obligations for mechanics-based cyber-physical systems.

The engine **proposes and organizes**; external verifiers, checkers, and provers
**dispose**. Its comparative advantage is upstream of any prover: structure-aware
model generation, certificate-candidate generation, proof-obligation generation,
and visualization of proof-relevant geometry.

## 2. What the Project Is / Is Not

**It is:**

- a structure-aware engine for analytical mechanics and dynamical systems;
- a generator of *models*, *certificate candidates*, and *proof obligations* for
  mechanics-based systems;
- a generator of self-contained **verification packages** — model, assumptions,
  safe/unsafe sets, candidates, obligations, measured diagnostics, and
  visualization data bundled together — that an external tool can consume;
- a mathematical viewer for trajectories, phase-space structure, diagnostics, and
  (eventually) safe/unsafe geometry and certificate status;
- a backend-agnostic front end that can export verification problems to external
  tools through adapters.

**It is not:**

- a generic physics engine or game engine;
- a generic robotics simulator;
- a generic cyber-physical-systems (CPS) verification front end for arbitrary
  systems;
- an arbitrary "theorem-to-animation" tool;
- a theorem prover, and not a competitor to mature verification tools.

The project does not try to verify everything. It deliberately specializes in
systems whose behavior and safety are governed by *mechanics*.

## 3. Theory-First Mechanics Philosophy

Mechanics is treated as a source of mathematical structure, not just a source of
animations. The objects that matter are conserved quantities, symmetries,
Hamiltonian and Lagrangian structure, constraints, potentials, invariant sets,
phase-space geometry, controlled vector fields, admissible controls, safe sets,
and candidate certificates.

Design principles:

- Prefer structure over spectacle.
- Prefer reproducibility over arbitrary interactivity.
- Prefer diagnostics and certificates over more demos.
- Prefer mathematical generality over one-off hacks.
- Keep advanced geometry honest: do not visualize what the engine cannot yet
  represent faithfully.
- Never present a numerical simulation as a proof.

## 4. Core Pipeline

The conceptual spine of the engine:

```text
analytical mechanics
-> structured controlled dynamical system
-> simulation and visualization
-> certificate candidates
-> proof obligations
-> verification package (one self-contained bundle of all of the above)
-> optional backend adapters for verification / certification
```

Each stage is a deliberate artifact, not a side effect. The first three stages
exist today for several example systems. Continuous controlled dynamics,
certificate candidates, proof obligations, a backend-agnostic
verification-problem IR, and a stub inspection adapter that writes problems out
for external inspection also exist in backend form, and the first linked pair
(`pendulum` ↔ `upright-pendulum-safety`) now surfaces its safe/unsafe geometry,
candidate-certificate values, and a measured proof-status view in the viewer.

The **verification package** is the new connective artifact: a single,
re-readable bundle that gathers a flagship system's model, assumptions, sets,
candidates, obligations, measured diagnostics, and visualization data so the same
artifact feeds both the viewer and any external backend. Real external
verification backends and actual proof discharge remain roadmap items — the
engine produces the package; it does not discharge it.

## 5. Target Domain: Mechanics-Based CPS and Robotics

The engine targets **mechanics-based dynamical systems, robotics, and physical
CPS** — especially systems where safety depends on motion, forces, constraints,
energy, reachability, stability, collision avoidance, actuator bounds, or
controller admissibility.

It deliberately **deprioritizes** non-physical verification: pure software
protocols, generic distributed systems, network logic, database consistency, and
other tasks whose state is not a physical configuration governed by mechanics.
These may be expressible in some backend the engine targets, but they are out of
scope for the engine's own modeling and certificate-generation layer.

## 6. Verification and Certification Philosophy

The engine generates *candidates* and *obligations*; it does not, by itself,
certify or prove. A central rule:

> The engine must never present a numerical simulation as a proof. Simulations
> explain and explore; certificates and proofs justify, and only under stated
> assumptions.

Concretely:

- A trajectory that "stays safe" in simulation is **evidence**, not a guarantee.
- A computed residual within tolerance is a **measurement**, not a theorem.
- A barrier/Lyapunov *candidate* is a proposal until a checker or prover accepts
  it under explicit assumptions.

The engine's job is to make the distinction between these states legible, and to
package the artifact a verifier would need.

## 7. Rigor Ladder

Every claim the engine emits should be tagged with one of four rigor levels, and
these must never be conflated:

1. **Measured / simulation-supported.** Behavior observed in one or more
   numerical runs (e.g. invariant residual within tolerance, trajectory avoided
   the unsafe set on this run). Exploratory evidence only.
2. **Certified numerical bounds.** Rigorous enclosures from validated numerics
   (e.g. interval / Taylor-model reachability), valid under stated assumptions.
3. **Reachability / SOS / barrier / Lyapunov-certified.** A certificate accepted
   by a sound method (e.g. an SOS-verified barrier or Lyapunov function, a
   reachability over-approximation), under stated assumptions.
4. **Deductively proved.** A theorem established in a theorem prover or proof
   calculus for hybrid/continuous dynamics.

The engine today operates at **level 1** for behavior and diagnostics, and has a
narrow **level 2** lane for selected certified-numeric interval enclosures over
recorded assumption boxes. Those enclosures are sound numerical bounds under the
stated model assumptions, not safety proofs. Levels 3–4 are reached only by
routing exported artifacts to appropriate external backends; the engine's own
contribution at those levels is to *generate the problem*, not to discharge it.

## 8. Core Abstractions

The conceptual schema the engine is organized around:

- configuration / state / phase space;
- Lagrangian and Hamiltonian systems;
- constraints and potentials;
- vector fields and flows;
- controlled dynamics `x' = f(x, u, d; θ)` (continuous) or
  `x_{k+1} = F(x_k, u_k, d_k; θ)` (discrete);
- admissible controls and disturbances;
- safe / unsafe sets;
- obstacles and geometric constraints;
- invariants;
- conserved quantities;
- Lyapunov and barrier *candidates*;
- proof obligations;
- a verification-problem intermediate representation (IR);
- visualization metadata.

**Status note (honesty):** today the engine implements configuration/state/phase
space, Lagrangian/Hamiltonian systems, constraints, potentials, vector fields and
flows, conserved quantities, invariant *diagnostics*, and — as of the
controlled-dynamics layer (`docs/controlled-dynamics.md`) — continuous controlled
dynamics `dx/dt = f(t, x, u, d; θ)` with box-shaped admissible control and
disturbance sets, closed-loop reduction, and deterministic rollouts
(backend-only). It also implements backend-only safe/unsafe sublevel sets,
candidate Lyapunov/barrier functions, proof obligations, measured sampled
checks, selected exact-rational certified-numeric interval enclosures for the
Tier-1 drone geofence family, Tier-3 disturbed geofence-axis obligations, and
selected sqrt-bearing keep-out constrained domains, and verification-problem IR v3
(continuous and discrete dynamics, control/disturbance channels, explicit
assumptions, candidate certificates, plus self-contained viewer-facing
verification exports: measured `regionGeometry` grids and boundary polylines,
controlled trajectories, time-aligned candidate-certificate series, sampled
`proofStatuses`, and package summaries that keep measured-only and
certified-numeric evidence tiers distinct while cataloging non-discharging
reachability handoff counts, plus a certified-status coverage validator that
audits the recorded level-2 enclosure metadata without discharging obligations,
and non-discharging reachability handoff artifacts for external
validated-numerics backends with package-read validation). The
discrete-time analogue
`x_{k+1} = F(k, x_k, u_k, d_k; θ)` now exists backend-only
(`engine/dynamics/discrete.py`, spec in `docs/discrete-dynamics.md`) with
closed-loop reduction, deterministic rollouts, and Euler discretization of
autonomous continuous systems. The backend exports self-contained controlled
pendulum and controlled spring verification case studies; frontend safety
surfaces still need to generalize fully across those exported problems. It does
**not** yet implement real certificate synthesis, proof discharge, broad
validated numerics, or any safety certification.

A specific distinction to preserve: the existing **finite-time Lyapunov exponent**
diagnostic (`engine/dynamics/diagnostics.py`) measures sensitive dependence /
chaos. It is **not** a Lyapunov *function* (a stability certificate). These are
different objects and the codebase and docs should keep them named distinctly.

## 9. Architecture: Python Backend, TypeScript Frontend, Schema Boundary

The Python ↔ TypeScript boundary is load-bearing and stays intact.

**Python is the mathematical backend.** It owns mechanics, symbolic computation,
equation derivation, numerical integration, diagnostics, and — going forward —
controlled dynamics, certificate candidates, and IR export.

- `engine/mechanics/` — Lagrangian/Hamiltonian mechanics, Euler–Lagrange,
  Legendre transforms, Noether charges, Poisson brackets, symplectic utilities,
  constraints, coordinate transforms.
- `engine/dynamics/` — first-order systems (symbolic Jacobian, divergence, fixed
  points, linearization), controlled systems, cotangent Hamiltonian flow, ray
  bundles, parameterized media models (scalar wave speed, refractive index,
  inverse metric), metric geometry for fixed-background geodesics
  (backend-only), safety/certificate candidates, and diagnostics (Poincaré
  sections, finite-time Lyapunov exponents, invariant residuals, ray travel
  time / caustic proximity / wavefront envelopes).
- `engine/verification/` — backend-agnostic verification-problem IR and adapters.
- `engine/numerics/` — fixed-step RK4, adaptive integration, and symplectic
  integrators (symplectic Euler, Störmer–Verlet) for separable Hamiltonians.
- `engine/export/` — `Trajectory`, the manifest contract, and JSON export.
- `systems/` — pure symbolic system definitions (one file per system).
- `scripts/` — generators and the `example_specs.py` registry; deterministic,
  regenerable outputs.

**TypeScript is the visualization frontend.** It consumes generated data and
renders: interactive animations, phase portraits, plots, structure/invariant
panels, diagnostics panels, and — going forward — safe/unsafe-set display,
rollout playback, and certificate/proof-status panels. It must not re-derive
physics or become responsible for deep mechanics.

**The boundary is a structured schema/manifest.** All new capability crosses the
boundary as explicit, documented schema, not as logic duplicated in the viewer.

## 10. Verification-Problem IR

The near-term architectural priority is a **backend-agnostic verification-problem
intermediate representation (IR)**. It is the stable foundation of the verification
direction; no specific external tool is. The IR should encode:

- variables and parameters;
- dynamics (continuous or discrete, controlled);
- controls;
- disturbances / uncertainty;
- domain assumptions;
- safe / unsafe sets;
- candidate certificates (barrier, Lyapunov, invariant);
- proof obligations;
- visualization hooks;
- export targets / adapters.

The IR is the analogue, for the verification layer, of what the manifest/export
contract is for the visualization layer. Backend adapters (to whatever external
verification or certification tools are appropriate) target the IR; the IR does
not depend on them. This keeps the project tool-agnostic: external tools may
appear as *future adapters* or as *examples of backend categories*
(reachability, SOS/certificate synthesis, deductive provers), never as the
foundation.

**Maturity note (direction correction).** The IR is now mature enough that
further refinement must be **case-study-driven**, not abstract. The IR exists to
carry a concrete flagship system end-to-end (§11); new fields and schema versions
should be motivated by a real package that needs them, not added speculatively.
Depth on one routed system now outranks breadth of IR surface area.

## 11. Near-Term Roadmap

**Foundations now exist (done).** Continuous and discrete controlled dynamics,
safe/unsafe sets, candidate Lyapunov/barrier generators, proof obligations, the
backend-agnostic verification-problem IR (v3, with `to_dict`/`from_dict`
round-trip), the stub inspection adapter, and two self-contained viewer case
studies are all implemented backend-only. (See `engine/dynamics/controlled.py`,
`discrete.py`, `safety.py`, `candidates.py`, and `engine/verification/`.)

**The realignment.** The verification IR is mature enough. The next milestone is
*not* more abstract IR or schema expansion, and *not* an in-engine prover — it is
**one flagship controlled system, routed all the way through**: backend model →
verification package → frontend visualization. Depth on one system now outranks
breadth.

### 11.1 Build a robust backend first

Frontend feature work is paused except for small maintenance; the next
substantial frontend task is rendering the complete flagship verification
package. The point is not to invent UI against unstable backend/package data —
backend robustness comes first. Backend robustness — assumptions, safe/unsafe
geometry, measured diagnostics, deterministic and re-readable export, and
validation — is the priority, so that routing the flagship system is mostly
composition rather than invention.

### 11.2 Verification package export (new connective artifact)

Define a **verification package**: a single, deterministic, re-readable bundle
(directory or archive) for one system, containing —

- a package **manifest** (ids, schema version, provenance, contents index);
- the **dynamics** (continuous or discrete, controlled);
- **assumptions** (state/parameter bounds, timestep if discrete, admissible
  controls, disturbances);
- **safe / unsafe sets** and their rendering geometry;
- **candidate certificates** (barrier / Lyapunov / invariant), candidate-only;
- explicit **proof obligations**;
- **measured traces / diagnostics** from simulated rollouts (rigor level 1);
- **visualization data** (trajectories, region grids, certificate series);
- optional **backend adapter stubs** describing how an external tool would
  consume the package.

The package is the IR plus everything a viewer or an external backend needs, in
one place. It is built from the existing IR and export contracts — it unifies the
viewer-facing export and the backend-only inspection artifacts into one bundle —
and it is re-readable in Python. It claims nothing beyond the rigor of each part:
measured stays measured, candidates stay candidates, obligations stay
external-required.

### 11.3 Systems and Verification share artifacts

The Systems and Verification *views* stay visually and product-separated, but
they are **not semantically disconnected**: where appropriate they consume the
same generated package/model artifacts. The project's thesis is precisely the
bridge from mechanics structure to a verification package, so the two surfaces
should draw on shared, deterministic artifacts rather than parallel data paths.

### 11.4 Frontend renders the package (after the backend lands)

Once the flagship package exports and validates, the Verification view renders
*that package* — its dynamics, sets, candidates, obligations, and measured
diagnostics — and offers a clear package download / inspection path. Safe/unsafe
rendering, certificate values, and a proof-status panel must respect the rigor
ladder ("candidate" / "measured" / "external-required", never "proved").

**Explicitly deferred / dropped.** An in-engine symbolic decrease-condition
checker (attempting `V̇ ≤ 0`) is **removed from near-term work**. The engine
*generates* the decrease proof obligation; an external verifier *discharges* it.
Building even a small in-engine checker would blur the "propose vs. dispose"
philosophy, so it is postponed indefinitely, not scheduled. External verification
integrations likewise come only after the flagship package exists.

## 12. Long-Term Roadmap

- A library of controlled mechanical systems with safe sets and candidate
  certificates.
- Multiple backend adapter *categories* (reachability, certificate synthesis,
  deductive proof) targeting the IR, chosen pragmatically and kept optional.
- Certified-numeric and certificate-level results (rigor levels 2–3) for selected
  systems, with the assumptions made explicit.
- A growing set of proof-obligation artifacts that an external prover could
  discharge, with selected deductive proofs (rigor level 4) as aspirational
  capstones rather than routine output.
- Theory-grounded reinforcement-learning environments as a downstream extension
  (see §13), not a core deliverable.
- Possible support for **user-created systems** through a *restricted, structured
  model schema* — templates and controlled schemas first, never arbitrary
  executable frontend code, and only later (if ever) more free-form systems.
- Data/transport: keep JSON as the manifest/IR layer; move large numerical arrays
  (long trajectories, big sweeps, reachable sets) to a compact columnar/chunked
  format (`.npz`, Arrow, Zarr, or similar) only when JSON becomes a real
  bottleneck.

## 13. Case Studies

**Classical mechanics (existing foundation).** Pendulum, double pendulum,
geodesic on a sphere, charged particle in a magnetic field, uniform gravity,
ideal spring, coupled oscillators, Kepler problem, bead on a rotating hoop,
Lorenz attractor, Hénon–Heiles, N-body gravity, and a variable-speed wavefront.
These exercise symbolic mechanics, conserved quantities, normal-mode analysis,
Poincaré sections, finite-time Lyapunov
*exponents*, invariant
residuals, parameter-sweep manifest slices (Lorenz rho and ideal-spring
stiffness families), ray-bundle / cotangent-Hamiltonian export with
travel-time, caustic-proximity, and
wavefront-envelope diagnostics, reusable parameterized media models, and a
backend-only metric-geometry helper (2-sphere, equatorial Schwarzschild). They
remain valuable as the structural and diagnostic backbone.

**Flagship controlled system (the committed next milestone).** The next
milestone is to push **one** controlled system the whole way through the stack.
The **preferred target is a drone point-mass model** (it aligns with existing
drone-verification work); if that proves too large to land soon, fall back to a
**controlled pendulum or cart-pole** as a smaller canonical benchmark. Whichever
is chosen, the end-to-end milestone is the same and must include, in order:

1. define or derive the controlled dynamics;
2. define assumptions — state/parameter bounds, timestep if discrete, admissible
   controls, disturbances if present;
3. define safe / unsafe sets;
4. define candidate certificate metadata, **candidate / external-required only**;
5. generate explicit proof obligations;
6. simulate rollouts and collect measured diagnostics;
7. export a **verification package** bundle (manifest, dynamics, assumptions,
   safe/unsafe sets, candidates, obligations, measured traces/diagnostics,
   visualization data, and backend adapter stubs if appropriate);
8. render the same package in the frontend Verification view;
9. provide a clear package download / inspection path;
10. claim **no** proof or certification unless an external backend actually
    discharges it.

Depth on this one system is worth more than breadth across many. Schema/IR work
is justified only insofar as it serves this routed package.

**Drone (motivating flagship application).** A drone is a natural flagship
*application* of the engine, and the preferred target above — but the engine must
not become drone-specific. The drone is modeled as a point mass with the same
general abstractions as any other controlled mechanical system: geofence,
obstacles, buffer region, controller action, velocity bounds, admissible
controls, and safety invariants. (No drone model exists in this repository yet;
it is the committed target, not a current capability.)

**Reinforcement-learning extension (downstream).** The same mechanics model can
later be exposed through a Gymnasium-style API with reset / step / reward /
termination / constraint signals. The distinctive angle is **theory-grounded RL
environments with explicit safety structure** (safe sets, admissible controls,
invariants) — not a generic RL platform. This is an extension, not the core.

## 14. Non-Goals and Credibility Boundaries

**Non-goals:**

- Generic physics, robotics, or CPS tooling for arbitrary systems.
- Non-physical verification (software protocols, distributed-systems logic,
  network/database consistency).
- Reimplementing or competing with mature verification tools.
- Browser-side physics or arbitrary user-supplied executable systems.
- More visual demos that add no new mathematical structure.

**Credibility boundaries (what the engine must not claim):**

- It does **not** currently verify, certify, or prove any system. It currently
  *simulates*, *diagnoses*, *visualizes*, and exports proof-obligation problems
  for external discharge.
- A finite-time Lyapunov *exponent* is a chaos diagnostic, not a Lyapunov
  *function*; the engine has both concepts, but they live in different modules
  and serve different purposes.
- A "certificate" produced by the engine is a **candidate** until an external
  sound method accepts it, and then only **under stated assumptions**.
- Every emitted claim should carry its rigor level (§7), and "measured" must
  never be reported as "proved."

## Definition of Success

The project succeeds if a user can define a mechanics-based controlled dynamical
system, inspect its structure, simulate and visualize it reproducibly, see its
safe/unsafe geometry and invariants, obtain candidate certificates and explicit
proof obligations, and export a self-contained backend-agnostic **verification
package** that the viewer can render and an external tool can attempt to discharge
— with every claim honestly labeled by its level of rigor. The nearest concrete
form of success is one flagship controlled system (a drone point-mass, or a
cart-pole/pendulum fallback) routed end-to-end through that pipeline.

The project should be judged by whether it helps users understand, structure, and
eventually certify the safety of mechanics-based dynamical systems — not by how
many visual demos it contains.
