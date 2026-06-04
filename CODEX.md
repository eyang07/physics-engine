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

## Next Milestones

1. Promote Noether's theorem to a first-class engine concept.
   - Specs should declare infinitesimal symmetry generators, not hand-written
     momentum expressions.
   - The engine should derive Noether charges from the generator via
     `sum p_i W_i` for vertical symmetries, with time-translation support for
     energy.
   - Tests should check both the variational-symmetry residual and the derived
     conserved quantity.
2. Add a derivation layer to the manifest.
   - Export structured symbolic steps, not only final formulas: Lagrangian,
     generalized momenta, Euler-Lagrange equations, Legendre transform,
     Hamiltonian, symmetry generator, and conserved quantity.
   - Keep this data generated from Python so the viewer teaches the
     mathematics without re-deriving physics.
3. Build the lens registry.
   - Treat physical systems and visualization lenses as separate concepts.
   - Lenses should be composable views such as configuration-space motion,
     phase plane, Hamiltonian vector field, energy level set, conserved
     quantity stillness, and effective potential.
   - Kepler/radial motion should use this to show orbit plane, radial phase
     portrait, effective potential, and angular momentum.

## Verification

Useful commands:

```sh
pytest -q
cd viewer && npm run build
cd viewer && npm run test:visual
```

The visual tests expect a Vite dev server running at `http://127.0.0.1:5173/`.
