# Project Vision

This project is not merely a mechanics visualization repo. Its long-term goal is
to become a structure-aware dynamical systems laboratory: a system that starts
from symbolic mechanics, derives equations of motion, simulates flows, exposes
invariants and geometric structure, and eventually produces artifacts useful for
analysis, verification, and AI-assisted mathematical reasoning.

The viewer is the interface, the central
contribution is the pipeline:

```text
mathematical system
-> symbolic formulation
-> equations of motion
-> numerical flow
-> invariants and diagnostics
-> qualitative structure
-> parameter families
-> verification or proof targets
```

A useful slogan:

> A proof-oriented analytical mechanics engine: simulation first, structure
> always, verification eventually.

## Research Identity

The project sits at the intersection of analytical mechanics, dynamical systems,
formal verification, and AI-assisted mathematics.

Mechanics should be treated as a source of mathematical structure, not just a
source of animations. Important objects include conserved quantities,
symmetries, Hamiltonian flows, Lyapunov functions, control barrier functions,
invariant sets, phase-space geometry, and proof obligations.

The project should not become a generic physics engine. Its comparative
advantage is symbolic mechanics, mathematical diagnostics, reproducible
simulation, and eventual verification/proof orientation.

## Current Foundation

The repo already has a strong foundation:

- symbolic mechanics backend;
- Hamiltonian and Lagrangian system support;
- first-order dynamics;
- numerical integration;
- JSON export and manifest generation;
- multiple example systems;
- Vite/TypeScript frontend;
- Three.js and canvas rendering lenses;
- playback controls, structure panels, invariant displays;
- renderer-hint-based camera framing.

This is enough to move beyond demo-gallery development. Future work should
deepen the project as a dynamical systems and mathematical-structure tool.

## North Star

The long-term workflow should be:

1. Define a mathematical system.
2. Derive or encode its equations of motion.
3. Simulate trajectories reproducibly.
4. Detect, compute, or display mathematical structure.
5. Run diagnostics for stability, chaos, invariants, and qualitative behavior.
6. Explore parameter families.
7. Export artifacts for analysis, verification, or theorem proving.

The project should eventually produce research objects such as:

- Poincare sections;
- Lyapunov diagnostics;
- invariant residuals;
- energy drift measurements;
- phase portraits;
- bifurcation data;
- parameter sweeps;
- candidate Lyapunov functions;
- candidate control barrier functions;
- proof-obligation stubs;
- formal verification targets;
- datasets of dynamical systems with known structure.

## Short-Term Theme: v0.2 Diagnostics and Phase-Space Structure

The next development phase should make the engine more research-grade. The
system should not merely render trajectories; it should help users study the
qualitative structure of a dynamical system.

Priority features:

1. [x] Implement Poincare-section export for Hénon-Heiles.
2. [x] Add finite-time Lyapunov diagnostics for Lorenz.
3. [x] Extend Lyapunov diagnostics to Hénon-Heiles or another Hamiltonian
   chaotic system.
4. [x] Add invariant-residual tracking for known conserved quantities.
5. [ ] Add parameter sweep manifests.
6. [x] Add numerical regression tests for invariant drift and deterministic
   outputs.
7. [x] Add visual regression coverage for camera reset and frontend framing.
8. [x] Generalize the ray-bundle export helper.
9. [ ] Improve phase-space lens support.
10. [ ] Add a control/barrier-function example.

Microlocal or GR examples should wait until the frontend can honestly represent
the geometry they require: phase space, cotangent bundles, covectors, ray
bundles, null geodesics, caustics, wavefronts, or lensing maps.

## Why These Priorities Matter

Poincare sections move the project from trajectory visualization to qualitative
dynamics. Hénon-Heiles is the right initial target because it connects
Hamiltonian mechanics, conserved energy, chaos, and phase-space structure.

Lyapunov diagnostics turn the engine into a stability and chaos workbench. They
also create bridges to control theory, reinforcement learning dynamics, and
energy landscapes.

Invariant residuals make the engine self-checking. For Hamiltonian systems, the
engine should track energy drift. For systems with known conserved quantities,
it should report residuals over time. This turns visual output into scientific
output.

Parameter sweeps should favor reproducible, precomputed variants before
arbitrary browser-side regeneration. This keeps the system deterministic,
testable, cacheable, and scientifically interpretable.

Ray-bundle export matters for wavefronts, optics, geometric mechanics, and
eventual microlocal examples, but it should be generalized as a geometric data
model, not as a one-off rendering feature.

## Gallery Direction

The gallery should eventually be organized around mathematical phenomena, not
just example names:

- Integrable Hamiltonian systems: oscillator, pendulum, Kepler, central-force
  systems.
- Chaotic and nonlinear systems: Lorenz, Hénon-Heiles, double pendulum,
  restricted three-body problem, kicked rotor, standard map.
- Constrained mechanics: bead on wire, spherical pendulum, rolling constraints,
  particles on surfaces.
- Wave, ray, and geometric optics systems: wavefronts, ray bundles, Hamiltonian
  optics, caustics.
- Control and safety systems: Lyapunov-stable systems, control barrier
  functions, safe-set invariance examples.
- Geometric mechanics systems: rigid body, magnetic flow, geodesic flow,
  systems on manifolds.

## Medium-Term Milestones

The medium-term goal is to turn the engine into a structure-extraction platform.
Diagnostic modules should include:

- conserved quantity checking;
- energy drift measurement;
- symplectic integrator comparison;
- equilibrium detection and linearization;
- phase portrait generation;
- Poincare section generation;
- finite-time Lyapunov exponent estimation;
- bifurcation diagram generation;
- invariant set approximation;
- candidate Lyapunov function evaluation;
- candidate control barrier function evaluation.

The guiding question should be:

> What mathematical object would a researcher inspect before attempting a proof?

The engine should produce that object.

## Long-Term Research Directions

### Hamiltonian Chaos Workbench

Build a suite of Hamiltonian systems with diagnostics for chaos and phase-space
structure: Hénon-Heiles, double pendulum, Kepler perturbations, restricted
three-body problem, kicked rotor, and standard map.

Core outputs should include energy surfaces, Poincare sections, Lyapunov
exponents, symplectic integration comparisons, and parameter-dependent
transition diagrams.

### Lyapunov and Control-Barrier Certificate Sandbox

Use the engine to test candidate Lyapunov functions and control barrier
functions. Outputs should include certificate residuals, safe-set visualization,
invariant-region approximations, counterexample trajectories, and controller
comparisons.

### Formal Verification and Proof-Obligation Generation

Eventually, the engine should export statements consumable by Lean, SMT solvers,
or other verification tools. Examples include energy conservation, set
invariance, Lyapunov decrease, barrier safety, input bounds, and numerical
counterexamples when evidence suggests failure.

### AI-Assisted Mathematical Reasoning Dataset

The engine can generate structured families of dynamical systems with known
properties: conserved quantities, equilibria, stability regimes, invariant
regions, candidate certificates, and symbolic proof obligations.

### Learned Dynamics and Energy Landscapes

The same infrastructure can later study learned vector fields, neural ODEs,
score flows, energy-based models, and diffusion-inspired dynamics using
diagnostics for energy decay, landscape roughness, stability, invariant
violation, and Lyapunov behavior.

## Data and Export Strategy

Keep JSON for now, but do not assume JSON will remain sufficient for all future
outputs.

Short term:

- use JSON for metadata, manifests, system definitions, diagnostics, and small
  trajectory outputs;
- keep schemas explicit and documented;
- prioritize stable conceptual organization over premature optimization.

Medium term:

- preserve JSON as the manifest layer;
- move large numerical arrays to compact formats when necessary;
- consider `.npz`, Arrow, Zarr, HDF5-like formats, or another
  columnar/chunked representation for large sweeps and long trajectories.

The conceptual schema should separate system metadata, parameters, coordinates,
equations, trajectories, invariants, diagnostics, events, sections, render
hints, camera hints, and frontend lens metadata.

## Frontend Direction

The frontend should remain a mathematical viewer, not just a rendering layer. It
should help users answer:

- What is the system?
- What are the coordinates?
- What quantities are conserved?
- What diagnostics were computed?
- What parameter regime is being viewed?
- What qualitative behavior is visible?
- What numerical errors or residuals are present?

Important frontend concepts include trajectory lenses, phase-space lenses,
invariant panels, diagnostic panels, section viewers, parameter-family
selectors, residual plots, camera metadata, and system-structure panels.

## Backend Direction

The backend should remain the source of mathematical truth. Priorities include
symbolic system definitions, equation derivation, numerical integration, event
detection, section extraction, diagnostic computation, invariant checking,
parameter sweep generation, manifest generation, reproducible exports, and
regression tests.

The backend should not become an ad hoc simulation script collection. It should
remain modular, typed where reasonable, tested, and organized around reusable
abstractions.

## Design Principles

- Prefer structure over spectacle.
- Prefer reproducibility over arbitrary interactivity.
- Prefer diagnostics over more examples.
- Prefer mathematical generality over one-off hacks.
- Prefer proof-oriented artifacts.
- Keep advanced geometry honest.

## What Not To Prioritize

- More visual demos without new mathematical structure.
- Browser-side parameter tweaking before reproducible sweep support exists.
- Advanced examples whose geometry cannot yet be represented honestly.
- One-off scripts that bypass the manifest/export architecture.
- Frontend polish that does not improve mathematical inspection.

## Definition of Success

The project succeeds if users can define a dynamical system, derive or inspect
its equations, simulate it reproducibly, visualize trajectories and phase-space
objects, inspect invariants and residuals, compute qualitative diagnostics,
explore parameter families, export data for analysis, and eventually export
statements for verification or proof.

The project should be judged by whether it helps users understand and certify
dynamical structure, not by how many visual demos it contains.

## Final Vision Statement

This project is a structure-aware analytical mechanics engine. It uses symbolic
mechanics, simulation, visualization, and diagnostics to expose the qualitative
behavior of dynamical systems. Its long-term purpose is to connect mechanics
with formal verification and AI-assisted mathematical reasoning, turning
simulations into mathematical artifacts and eventually into proof-oriented
workflows.
