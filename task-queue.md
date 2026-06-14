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

1. **FE-005: Label and legend the Verification stage violation markers**
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

2. **FE-006: Show selected verification counts in the stage header**
   - Goal: Echo the active problem's obligation/candidate/region counts in the
     Verification stage so the focused problem's scope is visible without
     scanning back to the catalog.
   - Scope: `viewer/src/verificationPanel.ts` or the stage header in
     `viewer/index.html`/`viewer/src/main.ts`, `viewer/src/styles.css`, and
     visual coverage in `viewer/tests/visual.spec.ts`.
   - Acceptance: The header reflects the selected problem's counts, updates when
     the selection changes, stays consistent with the catalog badges, and visual
     tests assert the header counts for at least two problems.

## Backend Queue

1. **BE-019: Validate verification certificate baseline links**
   - Goal: Reject viewer verification certificate metadata whose comparison
     baselines refer to missing obligations or regions.
   - Scope: `engine/export/verification_contract.py` and
     `tests/test_inspection_adapter.py`.
   - Acceptance: Problem payload validation catches missing baseline obligation
     links, missing baseline region links, malformed baseline comparison records,
     and focused verification export tests pass.

2. **BE-020: Document viewer verification export contract checks**
   - Goal: Make the backend-owned viewer verification export validations
     discoverable for future generator changes.
   - Scope: `docs/verification-ir.md`, `docs/BACKEND.md`, and
     `engine/export/verification_contract.py` docstrings if needed.
   - Acceptance: Docs name the index, problem-payload, trajectory, and
     round-trip validation layers; they state that these are contract checks and
     not proof or certification; focused verification export tests pass.
