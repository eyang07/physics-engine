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
verification package → (later) frontend. The package contract now exists
(BE-039, done: `engine/export/verification_package.py`), proven on the existing
pendulum/spring problems; tasks 1–2 enrich what the package carries; tasks 3–7
build the flagship drone point-mass (cart-pole/pendulum fallback) and route it
through a complete package. Keep generated data uncommitted. Never label anything
proved/certified — the engine proposes; external backends dispose._

1. **BE-034: Attach stated domain assumptions to the exported case studies**
   - Goal: Give each obligation the domain assumptions its candidate
     construction actually relies on (e.g. validity near the Hurwitz / upright
     equilibrium, control within actuator bounds), in the BE-039
     package-compatible format, so VISION §6's "valid only under stated
     assumptions" is concrete instead of empty — and so the verification package
     has real assumptions to carry.
   - Scope: `scripts/export_verification_problems.py` (define `AssumptionSpec`s
     and link them via obligation `assumption_ids`), the relevant
     `verification_problem_from_*` builders in `engine/verification/` if they need
     to thread assumptions, and `tests/`.
   - Acceptance: the pendulum and spring viewer problems export non-empty
     assumptions, each obligation references the assumptions it depends on, the
     package and export contract still validate, and focused tests pass.

2. **BE-036: Export measured safety-margin diagnostics per obligation**
   - Goal: Enrich the measured evidence with a per-obligation worst margin to the
     boundary (and a time-to-first-violation when violated) so the package's
     measured-diagnostics component shows how close a run gets, all still labeled
     measured.
   - Scope: `engine/verification/measured.py` (compute margin / violation time),
     `engine/export/verification_contract.py` (validate the new fields), and
     `tests/test_inspection_adapter.py`.
   - Acceptance: `proofStatuses` carry a numeric worst margin (and a violation
     time when `measured-violated`), validation accepts well-formed values and
     rejects bad shapes, generated examples validate, and focused tests pass.

3. **BE-040: Flagship drone point-mass controlled dynamics**
   - Goal: Introduce the committed flagship as a thin symbolic point-mass drone
     (translational position+velocity state, thrust/acceleration controls with
     bounds, optional disturbance) reduced to controlled continuous dynamics via
     the existing dynamics layer. Fallback per VISION §13: if the drone proves too
     large to land soon, a controlled pendulum/cart-pole stands in under the same
     milestone.
   - Scope: `systems/drone_point_mass.py` (thin symbolic definition), controlled
     reduction via `engine/dynamics/controlled.py`, and `tests/`.
   - Acceptance: the drone exports a controlled field `x' = f(x, u, d; θ)` with
     box control bounds and a deterministic closed-loop rollout under a
     stabilizing feedback law; focused tests pass.

4. **BE-041: Drone safe/unsafe sets, admissible controls, and candidate**
   - Goal: Give the flagship its safety structure — a geofence/buffer safe set
     (and an obstacle/unsafe set), admissible-control bounds, and a candidate
     Lyapunov/barrier — all candidate / external-required only, never certified.
   - Scope: `systems/drone_point_mass.py`, `engine/dynamics/safety.py` and
     `engine/dynamics/candidates.py` usage,
     `scripts/export_verification_problems.py`, and `tests/`.
   - Acceptance: the drone problem carries safe/unsafe sublevel sets with
     rendering geometry, admissible controls, and a labeled candidate; rigor stays
     candidate; the export contract validates; focused tests pass.

5. **BE-042: Drone proof obligations and measured rollout diagnostics**
   - Goal: Generate the drone's explicit proof obligations (safe-set
     invariance / barrier non-increase / Lyapunov decrease as *obligations*, not
     discharged) and collect measured diagnostics — worst margins and violation
     times (reusing BE-036) — from deterministic rollouts.
   - Scope: the `verification_problem_from_*` builders in
     `engine/verification/`, `engine/verification/measured.py`,
     `scripts/export_verification_problems.py`, and `tests/`.
   - Acceptance: obligations export as `external-required`, measured
     `proofStatuses` carry margins/violation times, nothing is labeled proved, the
     export contract validates, and focused tests pass.

6. **BE-043: Assemble and export the flagship drone verification package**
   - Goal: Route the drone end-to-end into one BE-039 verification package —
     manifest, dynamics, assumptions, safe/unsafe sets, candidates, obligations,
     measured traces/diagnostics, and visualization data — completing the VISION
     §13 milestone on the backend side.
   - Scope: `scripts/export_verification_problems.py` and
     `scripts/generate_verification_problems.py`, and `tests/`.
   - Acceptance: generation publishes a complete, contract-valid drone package
     that re-reads in Python and contains every milestone component; nothing
     claims proof/certification; generated data stays uncommitted; focused tests
     pass.

7. **BE-044: Backend adapter stubs in the verification package**
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
