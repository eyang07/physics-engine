# Codex Task Queue

Self-contained implementation specs handed from Claude (planning) to Codex
(execution). Each task is scoped for one focused branch. Codex: treat the
**Definition of done** as the contract, respect **Forbidden files** literally,
and report every command run with its real pass/fail outcome. If reality
contradicts the spec (a named symbol / path / field is wrong, or an invariant
cannot hold), stop and report rather than redesigning. See
`docs/agent-workflow.md` for the handoff / review / merge protocol.

## Completed

- **Task 1 — Invariant-residual tracking for conserved quantities** — merged.
  Reviewed green (`pytest -q` 166 passed). See `docs/BACKEND.md` Completed
  Missions / Itinerary #1.

- **Task 2 — Finite-time Lyapunov diagnostic for the Hénon-Heiles system** —
  merged. Reviewed green (`pytest -q` 167 passed, `cd viewer && npm run build`
  passed). The generated Hénon-Heiles trajectory now mirrors Lorenz's FTLE
  metadata and series shape while keeping invariant residuals scoped to `H`.

## Ready

No fully specced Codex handoff is currently queued.

## Next Itinerary Candidate

- **Backend:** parameter-sweep manifests for selected systems. Start with Lorenz
  or Hénon-Heiles and export deterministic precomputed variants before adding
  arbitrary browser-side regeneration.
- **Frontend:** manifest-driven diagnostics panel for exported backend
  diagnostics. Start with Lorenz and Hénon-Heiles Lyapunov metadata plus
  Hénon-Heiles Poincare-section metadata, without recomputing dynamics in
  TypeScript.
