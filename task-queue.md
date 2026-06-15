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

_Deferred — frontend work is paused pending product direction (per maintainer).
Do not add frontend tasks for now._

## Backend Queue

1. **BE-034: Attach stated domain assumptions to the exported case studies**
   - Goal: Give each obligation the domain assumptions its candidate
     construction actually relies on (e.g. validity near the Hurwitz / upright
     equilibrium, control within actuator bounds), so VISION §6's "valid only
     under stated assumptions" is concrete instead of empty.
   - Scope: `scripts/export_verification_problems.py` (define `AssumptionSpec`s
     and link them via obligation `assumption_ids`), the relevant
     `verification_problem_from_*` builders in `engine/verification/` if they need
     to thread assumptions, and `tests/`.
   - Acceptance: the pendulum and spring viewer problems export non-empty
     assumptions, each obligation references the assumptions it depends on, the
     export contract still validates, and focused tests pass.

2. **BE-035: Publish a discrete-time verification case study to the viewer**
   - Goal: Exercise the discrete IR path end-to-end by promoting the existing
     backend-only discrete example (`controlled_discrete_decay_problem`) into a
     viewer case study so the dashboard renders a discrete-time problem.
   - Scope: `scripts/export_verification_problems.py` (add a deterministic
     discrete `trajectory_factory` using `engine/dynamics/discrete` rollouts and
     include the problem in `viewer_verification_examples`),
     `scripts/generate_verification_problems.py` if needed, and `tests/`.
   - Acceptance: generation publishes the discrete problem (viewer payload + IR)
     with a self-contained trajectory and certificate series, the export contract
     validates it, and focused tests pass. Keep generated data uncommitted.

3. **BE-036: Export measured safety-margin diagnostics per obligation**
   - Goal: Enrich the measured evidence with a per-obligation worst margin to the
     boundary (and a time-to-first-violation when violated) so the honesty
     surface — and a future "margin over time" view — can show how close a run
     gets, all still labeled measured.
   - Scope: `engine/verification/measured.py` (compute margin / violation time),
     `engine/export/verification_contract.py` (validate the new fields), and
     `tests/test_inspection_adapter.py`.
   - Acceptance: `proofStatuses` carry a numeric worst margin (and a violation
     time when `measured-violated`), validation accepts well-formed values and
     rejects bad shapes, generated examples validate, and focused tests pass.

4. **BE-037: Add a third controlled case study (cart-pole)**
   - Goal: Grow the controlled case-study library (VISION §13) with a cart-pole:
     controlled dynamics, a safe set, a candidate Lyapunov/barrier, and proof
     obligations, exported to the viewer so the hero has richer content.
   - Scope: `systems/cart_pole.py` (thin symbolic definition), controlled
     reduction via `engine/dynamics`, candidate generation via
     `engine/dynamics/candidates.py`, `scripts/export_verification_problems.py`,
     and `tests/`.
   - Acceptance: a cart-pole verification problem exports with regions, a
     candidate, obligations, and a stabilizing controlled trajectory; the export
     contract validates it; and focused tests pass.

5. **BE-038: Symbolic Lyapunov/barrier decrease-condition checker (first
   discharge attempt)**
   - Goal: Take the first honest step on the "dispose" half of the pipeline — an
     in-engine adapter that *attempts* a candidate's decrease condition
     (e.g. `V̇ = ∇V · f ≤ 0` on the closed-loop field) symbolically and records
     the verdict with explicit assumptions. Strictly an attempt: it must never
     emit "proved"/"certified", only an honest holds/inconclusive diagnostic.
   - Scope: `engine/verification/` (a new checker/adapter plus an honest status
     alongside the existing `diagnostics.py` statuses), and `tests/`.
   - Acceptance: the checker reports holds/inconclusive for the case-study
     candidates under stated assumptions, the rigor labeling stays honest (no
     proof/certification claims), and tests cover the holds and inconclusive
     paths.
