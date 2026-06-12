# Codex Task Queue

Self-contained implementation specs handed from Claude (planning) to Codex
(execution). Use a focused branch only when isolation/review is useful; small
human-directed work may stay on the current branch. Codex: treat the
**Definition of done** as proportional to the change, respect **Forbidden files**
literally, and report every command run with its real pass/fail outcome. If
reality contradicts the spec in a way that blocks a small safe implementation,
stop and report rather than redesigning. See `docs/agent-workflow.md` for the
handoff / review / merge protocol.

## Completed

- **Task 1 — Invariant-residual tracking for conserved quantities** — merged.
  Reviewed green (`pytest -q` 166 passed). See `docs/BACKEND.md` Completed
  Missions / Itinerary #1.

- **Task 2 — Finite-time Lyapunov diagnostic for the Hénon-Heiles system** —
  merged. Reviewed green (`pytest -q` 167 passed, `cd viewer && npm run build`
  passed). The generated Hénon-Heiles trajectory now mirrors Lorenz's FTLE
  metadata and series shape while keeping invariant residuals scoped to `H`.

- **Parameter-sweep manifest slice for Lorenz** — implemented on
  `codex/parameter-sweep-manifest`. Reviewed green (`pytest -q` 178 passed,
  `cd viewer && npm run build` passed). The manifest now supports option-1
  system-attached `variants`, and Lorenz exports deterministic rho-family
  variant trajectories alongside the default trajectory.

- **Generalized parameterized media helpers** — implemented directly by Claude
  on `main` at the human's request (no Codex handoff). New
  `engine.dynamics.media` module with `ScalarSpeedMedium`,
  `RefractiveIndexMedium`, `InverseMetricMedium` (+ `from_metric`), and a
  reusable `gaussian_lens_speed` profile; the variable-speed wavefront system
  delegates to it. Verified: `pytest -q` 186 passed; regenerating
  `variable_speed_wavefront` produced byte-identical JSON outputs (verified by
  `cmp` against a regeneration from the pre-refactor commit; note generated
  data is gitignored, so `git diff` alone is not a valid check).

- **Wave/ray diagnostics** — implemented directly by Claude on `main` at the
  human's request. New `engine.dynamics.ray_diagnostics` module: travel time
  (eikonal phase `int xi . dq` with residual vs the exact `degree * p0 * s`
  model), caustic proximity (adjacent-ray spreading factors), and wavefront
  envelope records, exported as an additive `rayDiagnostics` metadata block by
  the wavefront generator. Verified: `pytest -q` 193 passed; regenerated JSON
  is identical to the previous output apart from the added `rayDiagnostics`
  key (checked by structural comparison).

- **GR metric helper (backend-only)** — implemented directly by Claude on
  `main` at the human's request. `engine.dynamics.metric.MetricGeometry`:
  Christoffel symbols, metric-compatibility residual, geodesic
  `FirstOrderSystem`, cogeodesic `InverseMetricMedium`, plus
  `two_sphere_metric` and `schwarzschild_equatorial_metric` reference
  constructors. Verified: `pytest -q` 204 passed; symbolic checks against
  textbook Christoffels, the sphere-geodesic Lagrangian route, and the
  Legendre transform; Schwarzschild circular-orbit radius and Killing charges
  conserved to 1e-12. No manifest/gallery changes.

- **Controlled-dynamics layer (backend-only)** — designed and implemented
  directly by Claude on `main` at the human's request; design spec in
  `docs/controlled-dynamics.md`. `engine.dynamics.controlled`:
  `ControlledFirstOrderSystem`, `Box` admissible sets (violations measured,
  never silently clipped), closed-loop reduction to `FirstOrderSystem`, and
  deterministic `rollout`; anchor system `systems/controlled_pendulum.py`
  (not in the gallery). Verified: `pytest -q` 213 passed; closed-loop
  reduction, control Jacobian, undamped energy conservation, and the
  gravity-compensation equilibrium family proven symbolically; PD upright
  stabilization and bound-violation reporting measured. Discrete analogue
  deferred.

- **Safety / certificate metadata (backend-only)** — designed and implemented
  directly by Claude on `main` at the human's request, then status-doc cleanup
  completed by Codex; design spec in `docs/safety-certificates.md`.
  `engine.dynamics.safety`: sublevel safe/unsafe sets, measured trajectory
  safety reports, candidate barrier and Lyapunov functions, symbolic Lie
  derivatives, proof-obligation records, and deterministic sampled checks
  labeled `rigor="measured"`. Verified: `pytest -q` 222 passed, with
  `tests/test_safety_certificates.py` covering margins, Lie derivatives,
  candidate obligations, counterexamples, rollout safety reports, deterministic
  grids, and validation errors. This is not real certification; synthesis,
  proof discharge, validated numerics, IR serialization, manifest export, and
  viewer surfaces are deferred.

## Ready

No fully specced Codex handoff is currently queued.

## Next Itinerary Candidate

- **Backend:** define verification-problem IR v0 (`docs/VISION.md` §11
  priority 3): serialize safety proof obligations as backend-agnostic
  inspection artifacts, with no local proof-discharge claim.
- **Frontend:** manifest-driven diagnostics panel for exported backend
  diagnostics. Start with Lorenz and Hénon-Heiles Lyapunov metadata plus
  Hénon-Heiles Poincare-section metadata, without recomputing dynamics in
  TypeScript.
