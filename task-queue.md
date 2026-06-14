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

1. **FE-010: Jump from a candidate's obligation link to its obligation card**
   - Goal: Let the obligation ids listed on a candidate-certificate card scroll
     the doc to the matching obligation card so the candidate→obligation link is
     navigable, reusing the section-anchor pattern from FE-008.
   - Scope: `viewer/src/verificationPanel.ts` (give each obligation card a stable
     id, make candidate obligation links scroll/emphasize the target),
     `viewer/src/styles.css` for the target emphasis, and visual coverage in
     `viewer/tests/visual.spec.ts`.
   - Acceptance: Activating a candidate's obligation link brings the matching
     obligation card into view and briefly emphasizes it, links whose obligation
     id is missing from the obligations list stay inert, and visual tests cover
     the navigate/emphasis behavior.

2. **FE-011: Jump from a measured-status card to its obligation card**
   - Goal: Let each measured-status card link to the obligation it sampled so the
     measured evidence is navigable back to the obligation it bears on, reusing
     the obligation-card ids introduced in FE-010.
   - Scope: `viewer/src/verificationPanel.ts` (make the measured-status card's
     obligation name scroll/emphasize the matching obligation card),
     `viewer/src/styles.css`, and visual coverage in `viewer/tests/visual.spec.ts`.
   - Acceptance: Activating a measured-status card's obligation link brings the
     matching obligation card into view and emphasizes it, status rows whose
     obligation id has no obligation card stay inert, and visual tests cover the
     navigate behavior.

## Backend Queue

1. **BE-030: Add verification certificate-series problem-id guard**
   - Goal: Ensure embedded certificate metadata cannot silently point at a
     different verification problem.
   - Scope: `engine/export/verification_contract.py` and
     `tests/test_inspection_adapter.py`.
   - Acceptance: Problem payload validation rejects certificate-series
     `problemId` values that differ from the containing problem id, rejects empty
     `problemId`, accepts generated viewer examples, and focused verification
     export tests pass.

2. **BE-031: Add verification certificate-series label guard**
   - Goal: Keep each certificate-series carrying a human-readable lane label so
     the viewer never renders an unlabeled certificate lane.
   - Scope: `engine/export/verification_contract.py` and
     `tests/test_inspection_adapter.py`.
   - Acceptance: Problem payload validation rejects empty or non-string
     certificate-series `label`, accepts the generated viewer examples, and
     focused verification export tests pass.
