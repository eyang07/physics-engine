# CODEX.md

Guidance for Codex agents working in this repo.

This is a learning-oriented analytical mechanics project. The code should make
the mathematics concrete and inspectable before it tries to be fast or general.

## Current Direction

- Python owns the mathematical engine.
- TypeScript owns the browser visualization layer.
- Generated data is the boundary between them.
- Lagrangian systems live on `TQ` with coordinates `(q, qdot)`.
- Hamiltonian systems live on `T*Q` with coordinates `(q, p)`.
- The Legendre transform bridges regular Lagrangian systems to Hamiltonian
  systems.
- The Hamiltonian geometry layer includes Poisson brackets, canonical
  symplectic matrices, Hamiltonian vector fields, Liouville divergence checks,
  and canonical-transformation checks.

## Current Structure

- `engine/mechanics/` — symbolic mechanics, coordinate charts, bundle charts,
  Lagrangian systems, Hamiltonian systems, transforms, constraints, and
  symmetries.
  - `poisson.py` and `symplectic.py` contain the canonical Hamiltonian geometry
    helpers.
- `engine/numerics/` — numerical integration helpers.
- `engine/export/` — generated trajectory/export formats.
- `systems/` — concise mathematical descriptions of physical examples.
- `scripts/` — generation scripts that export simulation data.
- `viewer/` — TypeScript/Vite frontend for visualizations.

## Working Principles

- Keep the math explicit. Prefer definitions and equations that are easy to
  inspect over clever abstractions.
- Keep examples small and verifiable. Add conservation checks or known-equation
  checks when introducing a new system.
- Do not blur system definitions with visualization choices. A system is the
  physical example; a visualization is a way of looking at that system.
- Generated data should remain disposable and reproducible from scripts.

## Frontend TODO

The frontend now separates physical systems from visualization modes.

Current model:

- The selected **system** is `Simple Pendulum`.
- The selected **visualization** is one of:
  - physical-space motion
  - phase-space portrait
  - Hamiltonian flow
  - energy surface

The same structure should apply to all examples: the system is the physical
example, and the visualization is a mathematical or graphical lens on that
example.

Longer-term frontend direction:

- Let the user select from many physics examples. Current examples include the
  simple pendulum, geodesics on a sphere, and a charged particle in a uniform
  magnetic field.
- Add more examples such as harmonic oscillator, central-force motion,
  relativistic geodesics, and fluid flows.
- Let the user tune physical parameters and initial conditions.
- Let the user choose visualization modes such as physical motion, phase space,
  Hamiltonian flow, conserved quantities, vector fields, and energy surfaces.
- Keep labels mathematically precise, using LaTeX where appropriate.

## Next Milestones

1. Add parameter controls for each system.
   - Pendulum: `length`, `gravity`, `theta0`, `theta_dot0`.
   - Sphere geodesic: `radius`, `theta0`, `phi0`, `theta_dot0`, `phi_dot0`.
   - Charged particle: `mass`, `charge`, `B_z`, initial position, initial
     velocity.
2. Add a Python generation API:
   `generate_example(system_id, parameters) -> Trajectory`.
3. Add a shared example manifest so Python and TypeScript agree on available
   systems, parameters, generated data, and visualization modes.
4. Split frontend renderers by responsibility:
   `pendulum2d`, `hamiltonianSurface`, `sphereGeodesic`, `chargedParticle`.
5. After the interface supports parameters, add a more ambitious example:
   central-force or Kepler motion as a bridge toward relativistic geodesics.

## Verification

Useful commands:

```sh
pytest -q
cd viewer && npm run build
cd viewer && npm run test:visual
```

The visual tests expect a Vite dev server running at `http://127.0.0.1:5173/`.
