# Task Queue

This file is the shared implementation queue for coding agents working in this
repository. Tasks are ranked in the order they should be attempted, with the
most immediately implementable task first in each section.

## Agent Workflow

- Pick exactly one task from either the frontend or backend queue.
- Before editing, verify that the task still matches the current repository
  state and does not duplicate uncommitted work.
- Keep the Python-to-TypeScript boundary intact: Python computes and exports;
  TypeScript renders generated data.
- When the task is complete, remove it from this queue in the same change.
- If either queue has fewer than two tasks after removal, add coherent next
  tasks for that side before finishing. Keep new tasks ordered by
  implementation readiness.
- Do not add tasks for generated data under `data/generated/` or
  `viewer/public/data/*.json`.

## Task Format

Each task should use this structure:

```md
1. **TASK-ID: Short imperative title**
   - Goal: One sentence describing the outcome.
   - Scope: Main files or modules expected to change.
   - Acceptance: Concrete checks, tests, or visible behavior that prove the task
     is done.
```

## Frontend Queue

_Frontend feature work is paused except for small maintenance while the backend
is hardened (per maintainer, VISION §11.1). The next substantial frontend task is
rendering the complete flagship **verification package** in the Verification view
(dynamics, sets, candidates, obligations, measured diagnostics) with a clear
package download/inspection path, respecting the rigor ladder. Don't invent UI
against unstable package data; don't add other frontend tasks for now._

## Backend Queue

_Direction (VISION §11): stop expanding the IR in the abstract. The whole queue
now drives **one flagship controlled system end-to-end** — backend model →
verification package → (later) frontend. The package contract exists (BE-039) and
the case studies carry per-obligation assumptions (BE-034). The flagship model has
arrived (`DRONE_MODEL_SPEC.md`): a **guard-band feedback-controlled, geofenced
point-mass drone**, whose canonical model is a **discrete** exact zero-order-hold
map with a per-axis piecewise (Piecewise) controller and a **box / forward-
invariance barrier** certificate — not Lyapunov (there is no equilibrium). BE-040
is done (`systems/drone_point_mass.py`: the Tier-1 discrete plant, guard-band law,
and a safe rollout). Route **Tier-1 geofence (P1) + velocity bound (P2)** first;
Tier-2 obstacle (P4) and Tier-3 disturbance come later. Keep generated data
uncommitted. Never label anything proved/certified — the engine proposes; external
backends dispose._

1. **BE-041: Drone geofence safe set, guard-band closed loop, and barrier candidate**
   - Goal: Build the Tier-1 drone verification problem from the discrete plant:
     the geofence safe box `S` (and the inner set / guard band), the guard-band
     closed loop (`closed_loop`), and the box-barrier candidate
     `B_geofence(q) = max(...)` plus the per-axis velocity-bound candidate — all
     candidate / external-required only, never certified. Project the 6-D state to
     the `(q1, v1)` phase plane for region geometry (spec M).
   - Scope: `systems/drone_point_mass.py` (sublevel-set / barrier helpers if
     needed), `engine/verification/` discrete-barrier builder usage,
     `scripts/export_verification_problems.py` (a `drone_geofence_problem`), and
     `tests/`. Confirm `Max`/`Piecewise` flow through region geometry and sampling.
   - Acceptance: the drone problem exports geofence safe/inner regions with
     rendering geometry on `(q1, v1)`, the admissible control box, and a labeled
     barrier candidate; rigor stays candidate; the export contract validates;
     focused tests pass.

2. **BE-036: Export measured safety-margin diagnostics per obligation**
   - Goal: Enrich the measured evidence with a per-obligation worst margin to the
     boundary (and a time-to-first-violation when violated) so the package's
     measured-diagnostics component shows how close a run gets, all still labeled
     measured. (The drone's `(q1, v1)` guard-band approach is the natural margin
     example.)
   - Scope: `engine/verification/measured.py` (compute margin / violation time),
     `engine/export/verification_contract.py` (validate the new fields), and
     `tests/test_inspection_adapter.py`.
   - Acceptance: `proofStatuses` carry a numeric worst margin (and a violation
     time when `measured-violated`), validation accepts well-formed values and
     rejects bad shapes, generated examples validate, and focused tests pass.

3. **BE-042: Drone proof obligations and measured rollout diagnostics**
   - Goal: Generate the drone's explicit Tier-1 obligations as *obligations* (not
     discharged): controller admissibility, P1 one-step geofence invariance
     (`q in S => q+ in S`), and P2 one-step velocity invariance (spec K 1–3), and
     collect measured diagnostics — worst margins and violation times (reusing
     BE-036) — from the deterministic guard-band rollout.
   - Scope: the discrete-barrier builders in `engine/verification/`,
     `engine/verification/measured.py`,
     `scripts/export_verification_problems.py`, and `tests/`.
   - Acceptance: obligations export as `external-required`, measured
     `proofStatuses` carry margins/violation times, nothing is labeled proved, the
     export contract validates, and focused tests pass.

4. **BE-043: Assemble and export the flagship drone verification package**
   - Goal: Route the drone end-to-end into one BE-039 verification package —
     manifest, dynamics, assumptions (spec G: `speedBound`, `velBound`, `dtSmall`,
     `driftBound`), safe set, candidate, obligations, measured traces/diagnostics,
     and `(q1, v1)` visualization — completing the VISION §13 milestone on the
     backend side.
   - Scope: `scripts/export_verification_problems.py` and
     `scripts/generate_verification_problems.py`, and `tests/`.
   - Acceptance: generation publishes a complete, contract-valid drone package
     that re-reads in Python and contains every milestone component; nothing
     claims proof/certification; generated data stays uncommitted; focused tests
     pass.

5. **BE-044: Backend adapter stubs in the verification package**
   - Goal: Include optional adapter-stub descriptors in the package describing how
     external backend *categories* (reachability, SOS/certificate synthesis,
     deductive prover) would consume each obligation — descriptors of target and
     required shape only, no discharge, preserving the tool-agnostic posture.
   - Scope: `engine/verification/` (adapter-stub descriptors alongside the
     existing capability/target-requirement modules), the package writer in
     `engine/export/verification_package.py`, and `tests/`.
   - Acceptance: the drone package lists adapter stubs naming a target backend
     category and the obligation shape it would need, all honestly
     non-discharging; the export contract validates; focused tests pass.
