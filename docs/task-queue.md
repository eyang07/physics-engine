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
  `variable_speed_wavefront` produced byte-identical JSON outputs.

## Ready

No fully specced Codex handoff is currently queued.

## Next Itinerary Candidate

- **Backend:** diagnostics for wave/ray examples (travel time, caustic
  proximity, wavefront envelope metadata) or the GR metric helper on top of
  `InverseMetricMedium.from_metric`.
- **Frontend:** manifest-driven diagnostics panel for exported backend
  diagnostics. Start with Lorenz and Hénon-Heiles Lyapunov metadata plus
  Hénon-Heiles Poincare-section metadata, without recomputing dynamics in
  TypeScript.
