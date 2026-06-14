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

1. **FE-003: Mark measured violation samples on the Verification stage**
   - Goal: When a `proofStatuses` entry reports `measured-violated` with a
     worst sampled point that maps to the active projection, show that point on
     the stage alongside the trajectory.
   - Scope: `viewer/src/data/verification.ts`, `viewer/src/verificationStage.ts`,
     safety-region rendering helpers, and focused visual coverage.
   - Acceptance: Violations are visually distinguished from safe/unsafe region
     boundaries, absent or unmappable samples do not render misleading markers,
     and visual tests cover at least the no-marker and marker paths.

2. **FE-004: Surface verification problem selection in the catalog**
   - Goal: Make the Verification catalog show which problem is active and how
     many obligations/candidates each carries so the read-only workbench is
     navigable without opening every problem.
   - Scope: `viewer/src/main.ts` (catalog rendering), `viewer/index.html`/styles
     for the catalog item layout, and visual coverage in
     `viewer/tests/visual.spec.ts`.
   - Acceptance: Each catalog item shows its obligation/candidate counts from the
     index summary, the active item is visually marked and stays in sync when the
     selection changes, and visual tests assert the active-item marker and the
     count badges for at least two problems.

## Backend Queue

1. **BE-013: Validate viewer verification index shape**
   - Goal: Add backend-side validation for `scripts.generate_verification_problems`
     index entries so the viewer catalog can rely on stable problem summaries.
   - Scope: `scripts/generate_verification_problems.py`,
     `engine/export/verification_contract.py` or a nearby helper, and
     `tests/test_inspection_adapter.py`.
   - Acceptance: Validation rejects missing ids, duplicate ids, non-verification
     data paths, and malformed count summaries; generator tests cover valid and
     invalid index payloads; focused verification export tests pass.

2. **BE-014: Add verification trajectory payload validation**
   - Goal: Validate the embedded verification trajectory payloads written for
     the viewer so time, state names, states, series, and certificate metadata
     stay synchronized.
   - Scope: `scripts/generate_verification_problems.py`,
     `engine/export/verification_contract.py`, and
     `tests/test_inspection_adapter.py`.
   - Acceptance: Validation rejects mismatched time/state lengths, series whose
     lengths differ from time, missing certificate series references, and empty
     state names; generator tests cover valid and invalid payloads.
