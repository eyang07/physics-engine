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

---

### Task 2: Finite-time Lyapunov diagnostic for the Hénon–Heiles system

Owner: Codex
Branch: codex/task-2
Status: Ready

Goal:
Add a finite-time largest-Lyapunov-exponent diagnostic to the existing
Hénon–Heiles generated trajectory, reusing the existing
`engine.dynamics.finite_time_lyapunov` and the Lagrangian's first-order form. The
generated `henon_heiles.json` should carry a `diagnostics.lyapunov` metadata
block and `ftle` / `lyapunov_local_growth` series, exactly mirroring the Lorenz
example's shape, so the viewer can consume both with one code path. This advances
the CLAUDE.md design responsibility "finite-time Lyapunov diagnostics (Lorenz,
then a Hamiltonian chaotic system)."

Context:
- The diagnostic already exists and is exercised only on Lorenz today:
  `engine/dynamics/diagnostics.py:finite_time_lyapunov`, wired in
  `scripts/generate_lorenz_attractor.py:94` and surfaced as
  `metadata["diagnostics"]["lyapunov"]` (fields: `kind`, `method`, `series`,
  `localGrowthSeries`, `initialTangent`, `finalTangent`, `finalEstimate`,
  `sampleCount`, `timeWindow`) plus `series["ftle"]` and
  `series["lyapunov_local_growth"]`. Mirror that shape verbatim.
- `finite_time_lyapunov(system, time, states, ...)` requires a
  `FirstOrderSystem` whose `jacobian()` has **no unresolved free symbols** beyond
  `time` and the state symbols. The Hénon–Heiles `LagrangianSystem` already
  provides the bridge: `LagrangianSystem.first_order_expressions()`
  (`engine/mechanics/lagrangian.py:98`) returns `[q̇, q̈(q, q̇, t)]` in the order
  `(*system.q, *system.qdot)` — which is exactly the trajectory's exported
  column order `["x", "y", "x_dot", "y_dot"]`.
- Because `systems/henon_heiles.py:build_system` is called with concrete numeric
  parameters (`mass=1.0, stiffness=1.0, coupling=1.0`) in the generator, the
  resulting Lagrangian has no symbolic parameters, so the constructed
  `FirstOrderSystem` Jacobian resolves fully with **no `substitutions`** needed.
- The trajectory exports only the 4 intrinsic columns (no `state_transform`), so
  `trajectory.states` already has shape `(N, 4)` matching the 4 state symbols.
- **Series-ordering invariant (do not break Task 1):**
  `generate_lagrangian_trajectory` computes `invariantResiduals` from the series
  it builds (only the conserved quantity `H`) *before* the generator adds the
  Lyapunov series. Add `ftle` / `lyapunov_local_growth` to `series` only in the
  generator's final `Trajectory.from_arrays(...)`, so residuals stay limited to
  conserved quantities and never get computed for the Lyapunov series.

Allowed files:
- `scripts/generate_henon_heiles.py` — build the `FirstOrderSystem`, call
  `finite_time_lyapunov`, add `metadata["diagnostics"]["lyapunov"]`, and merge the
  two new series into the existing series dict.
- `tests/test_henon_heiles.py` — add assertions for the new diagnostic.
- `docs/BACKEND.md` — add a Completed Missions line **only after** verification
  passes (do not flip any other itinerary item; this is not Next-Best #2 or #3).

Forbidden files:
- `engine/**` — this is pure reuse; no new engine surface. Build the
  `FirstOrderSystem` inline in the generator (a few lines). If you believe a
  reusable `LagrangianSystem → FirstOrderSystem` bridge helper is warranted,
  **stop and report** — that is a Claude-owned abstraction decision, not part of
  this task.
- `engine/export/manifest.py`, `engine/export/trajectory.py` — no schema change;
  you are adding a metadata key and series entries, both established patterns.
- `scripts/generation.py`, `scripts/example_specs.py`, and every other
  `scripts/generate_*.py` — do not touch other systems.
- `viewer/**` — frontend consumption of this diagnostic is a separate task.
- No new gallery examples, no new lens kinds, no renderer-hint changes.
- Do not reformat, re-sort imports, or rename across files.

Steps:
1. In `scripts/generate_henon_heiles.py`, after the trajectory is integrated and
   `system = build_system(mass=..., stiffness=..., coupling=...)` exists, construct
   `FirstOrderSystem(state=(*system.q, *system.qdot),
   rhs=system.first_order_expressions(), parameters=(), time=system.time)` (import
   `FirstOrderSystem` from `engine.dynamics`).
2. Call `lyapunov = finite_time_lyapunov(first_order_system, trajectory.time,
   trajectory.states[:, :4])` (import `finite_time_lyapunov` from
   `engine.dynamics`). Do not pass a custom tangent; use the default.
3. Add a `diagnostics` dict to the rebuilt metadata containing a `lyapunov` block
   with the **same field names and values shape** as Lorenz
   (`scripts/generate_lorenz_attractor.py:125-136`): `kind:
   "finite-time-largest"`, `method: "sampled-variational-jacobian"`, `series:
   "ftle"`, `localGrowthSeries: "lyapunov_local_growth"`, `initialTangent`,
   `finalTangent`, `finalEstimate`, `sampleCount`, `timeWindow`.
4. In the generator's final `Trajectory.from_arrays(...)`, change
   `series=trajectory.series` to a merged dict:
   `series={**trajectory.series, "ftle": lyapunov.estimate.astype(float).tolist(),
   "lyapunov_local_growth": lyapunov.local_growth.astype(float).tolist()}`.
5. Regenerate the Hénon–Heiles data:
   `python -m scripts.generate_henon_heiles` (writes `data/generated/` and
   `viewer/public/data/`; both are gitignored — regeneration confirms determinism,
   there is nothing to commit).
6. Add tests (see Definition of done). The tests must assert presence, shape,
   finiteness, and determinism — **not** that the orbit is chaotic.

Commands to run:
- `git branch --show-current`   (must print `codex/task-2` before editing)
- `git status`
- `pytest -q`                   (full suite must pass; report the count)
- `python -m scripts.generate_henon_heiles`
- `python3 -c "import json,sys; d=json.load(open('data/generated/henon_heiles.json')); ly=d['metadata']['diagnostics']['lyapunov']; print('finalEstimate', ly['finalEstimate']); print('series keys', sorted(d['series'])); print('residual names', [r['name'] for r in d['metadata']['invariantResiduals']])"`
  (inspection: confirm the lyapunov block, the two new series keys, and that
  `invariantResiduals` still lists only conserved quantities — i.e. `['H']`)
- `cd viewer && npm run build`  (no viewer code changed; must stay clean)

Definition of done:
- `data/generated/henon_heiles.json` and `viewer/public/data/henon_heiles.json`
  contain `metadata.diagnostics.lyapunov` with the Lorenz field set, and
  `series.ftle` / `series.lyapunov_local_growth` of length equal to the trajectory
  sample count.
- `metadata.invariantResiduals` for Hénon–Heiles still contains exactly the
  conserved quantities (just `H`) — no residual record for `ftle` or
  `lyapunov_local_growth`.
- A new test in `tests/test_henon_heiles.py` asserts: the lyapunov metadata block
  exists with the documented keys; `ftle` and `lyapunov_local_growth` series exist
  and match the trajectory length; `finalEstimate` and the tangents are finite; the
  initial tangent is unit-norm; and running the generator twice yields identical
  `finalEstimate` (determinism). The test must **not** assert the FTLE is positive
  or that the system is chaotic.
- `pytest -q` passes — and you ran it (report the count).
- The generator was run and the inspection command shows the expected fields.
- `cd viewer && npm run build` is clean.
- `docs/BACKEND.md` has a Completed Missions line describing the addition; no other
  status markers changed.
- Your report lists exactly what changed, every command with its real pass/fail
  outcome, and the **measured** `finalEstimate` — described as a measured
  finite-time estimate, not as evidence of chaos.

Failure/reporting rules:
- If a command fails, report the exact command and failure.
- If the task requires files outside the allowed scope, stop and report the needed
  scope expansion (in particular: if you find the Jacobian has unresolved symbols,
  or you think an `engine/` bridge helper is needed, stop and route to Claude
  rather than editing `engine/`).
- If a failing test encodes a real invariant (determinism, series length, finite
  values), assume the code is wrong, not the test; do not loosen or skip it.
- Do not silently change architecture or project goals. This task adds a metadata
  diagnostic to one existing system; it does not introduce a new abstraction, a new
  example, or a schema change.
- Never claim a green run you did not produce. Honest "this still fails" beats a
  false green.

Claude review checklist:
- [ ] `FirstOrderSystem` is built from `system.first_order_expressions()` with
      state `(*system.q, *system.qdot)`; its `jacobian()` has no unresolved symbols
      at the numeric parameters (no `substitutions` hack needed).
- [ ] States passed to `finite_time_lyapunov` are the 4 intrinsic columns in the
      same order as `system.state` / the exported `state_names`.
- [ ] `metadata.diagnostics.lyapunov` mirrors the Lorenz field set; the two series
      reuse the Lorenz key names (`ftle`, `lyapunov_local_growth`) so the viewer can
      use one code path.
- [ ] `invariantResiduals` is uncontaminated — only conserved quantities (`H`),
      because the Lyapunov series are merged after the helper runs.
- [ ] Series lengths equal the trajectory sample count; values finite.
- [ ] Claim hygiene: the diagnostic is reported as a *measured finite-time
      estimate*; no assertion or doc text claims the orbit is chaotic.
- [ ] Scope: only `scripts/generate_henon_heiles.py`, `tests/test_henon_heiles.py`,
      and a `docs/BACKEND.md` Completed Missions line changed; `engine/**` and other
      generators untouched.
