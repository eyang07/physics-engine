# Dynamical Systems Notes

The dynamics layer complements the mechanics layer. Mechanics systems can still
be derived from Lagrangians or Hamiltonians, while `engine.dynamics` covers
general flows, controlled systems, ray/cotangent flows, metric geometry,
diagnostics, and safety/certificate candidates.

## Current Backend Shape

- `FirstOrderSystem` represents `dx/dt = f(t, x; params)` with symbolic RHS,
  Jacobian, divergence, fixed points, linearization, and numerical RHS support.
- `ControlledFirstOrderSystem` represents `dx/dt = f(t, x, u, d; params)` with
  control/disturbance symbols, admissible boxes, closed-loop reduction, and
  deterministic rollouts.
- Cotangent Hamiltonian systems support ray/geodesic-style flow.
- Parameterized media models cover scalar speed, refractive index, and inverse
  metric descriptions.
- Metric geometry helpers derive Christoffel symbols, geodesic equations, and
  cogeodesic media for fixed-background examples.
- Safety helpers represent safe/unsafe sets, candidate Lyapunov/barrier
  functions, proof obligations, and measured sampled checks.
- `engine.verification` serializes proof obligations into a backend-agnostic IR.

## Diagnostics

Implemented diagnostics include:

- Fixed points and symbolic/numeric Jacobians.
- Eigenvalues and stability information at equilibria.
- Divergence and volume contraction/expansion.
- Speed, radius, and distance-from-equilibrium series.
- Trajectory bounds and renderer-hint framing.
- Finite-time Lyapunov exponent estimates for Lorenz and Hénon-Heiles.
- Poincare sections for Hénon-Heiles.
- Invariant-residual tracking for conserved quantities.
- Parameter variants, currently used by the Lorenz rho family.
- Ray diagnostics: travel time, caustic proximity, and wavefront envelopes.

## Current Examples

- Lorenz attractor exercises general first-order dynamics, adaptive integration,
  dissipative-flow diagnostics, FTLE metadata, and attractor rendering.
- Hénon-Heiles exercises Hamiltonian chaos diagnostics, invariant residuals,
  FTLE metadata, and Poincare-section export.
- Variable-speed wavefront propagation exercises cotangent flow, ray bundles,
  parameterized media, and wavefront diagnostics.
- Controlled pendulum exercises controlled dynamics, closed-loop reduction,
  rollout reporting, safety metadata, and verification-problem IR export.

## Next Work

- Add a stub external-verification adapter for the IR.
- Add basin sampling or bifurcation-style diagnostics when a concrete example
  needs them.
- Extend parameter-family exports beyond Lorenz once frontend variant behavior
  is settled.
- Keep advanced geometry backend-only until the viewer can represent it
  honestly.
