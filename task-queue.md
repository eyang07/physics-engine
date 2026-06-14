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

1. **FE-004: Surface verification problem selection in the catalog**
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

2. **FE-005: Label and legend the Verification stage violation markers**
   - Goal: Give the measured-violation markers a stage legend and an on-hover or
     adjacent caption naming the obligation each violated point belongs to, so a
     red marker is self-explanatory rather than an unlabeled glyph.
   - Scope: `viewer/src/verificationStage.ts` (marker draw + legend),
     `viewer/src/styles.css` for any legend chrome, and visual coverage in
     `viewer/tests/visual.spec.ts`.
   - Acceptance: A legend entry appears only when at least one violation marker is
     drawn, each marker is associated with its obligation name without overlapping
     the trajectory readout, and visual tests cover both the no-violation (no
     legend) and violation (legend present) paths.

## Backend Queue

1. **BE-016: Add verification export round-trip contract coverage**
   - Goal: Ensure generated viewer verification indexes and problem files stay
     mutually consistent without committing regenerated artifacts.
   - Scope: `engine/export/verification_contract.py`,
     `scripts/generate_verification_problems.py`, and
     `tests/test_inspection_adapter.py`.
   - Acceptance: Temp-dir generation validates the index, every referenced
     problem file, each embedded trajectory, and each index summary count against
     the referenced problem payload; focused verification export tests pass.

2. **BE-017: Validate verification export problem payload links**
   - Goal: Reject viewer verification problem files whose internal references
     point at missing regions, obligations, candidates, or trajectory states.
   - Scope: `engine/export/verification_contract.py`,
     `scripts/generate_verification_problems.py`, and
     `tests/test_inspection_adapter.py`.
   - Acceptance: Problem payload validation catches missing proof-status
     obligation links, candidate obligation links, region-geometry region links,
     and trajectory state names not declared by the problem variables; generator
     tests cover valid and invalid payloads.
