# CLAUDE.md

Guidance for working in this repo. This is a learning project: code exists to
make the mathematics concrete, so favor readable, well-commented
implementations over clever or fast ones.

## Working principles

- Math first. When implementing something, mirror the math (state the
  definition or equation in a comment, then implement it).
- Keep pieces small and inspectable. Prefer pure functions over hidden state.
- It's fine to leave things unfinished or marked as TODO; this repo grows with
  the learning, not on a fixed plan.

## Rough shape of the code (subject to change)

A plausible starting skeleton — not a commitment:

- `core/` — basic math primitives (vectors, linear algebra helpers, numerical
  integrators such as Euler / RK4 / symplectic integrators).
- `mechanics/` — Lagrangian and Hamiltonian setups: defining a system from its
  Lagrangian/Hamiltonian and deriving the equations of motion.
- `examples/` — small worked systems (pendulum, two-body, harmonic
  oscillator) used to check the math against known behavior.
- `viz/` — later: plotting and animation (phase portraits, vector fields).

## Language

Not yet decided. Start with whatever expresses the math clearly; revisit if
performance ever becomes the bottleneck.

## Conventions

- Document the physics/math intent alongside the code.
- Add an example or sanity check (e.g. energy/quantity conservation) when
  adding a new system or integrator.
