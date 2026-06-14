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

1. **FE-007: Focus a violation marker from its legend entry**
   - Goal: Let clicking a violation legend entry highlight its matching stage
     marker so a named violation can be located on the phase plane.
   - Scope: `viewer/src/verificationStage.ts` (legend interaction + marker
     emphasis draw), `viewer/src/styles.css` for the focused-entry chrome, and
     visual coverage in `viewer/tests/visual.spec.ts`.
   - Acceptance: Selecting a legend entry visibly emphasizes only its marker,
     selection clears when the problem changes or the marker set updates, the
     no-violation path stays interaction-free, and visual tests cover the
     focus/clear behavior.

2. **FE-008: Link header obligation count to the obligations section**
   - Goal: Let the header's obligation count scroll the problem doc to the
     obligations section so the scope summary is a way into the detail.
   - Scope: `viewer/src/verificationPanel.ts` (header count interaction +
     obligations section anchor), `viewer/src/styles.css`, and visual coverage
     in `viewer/tests/visual.spec.ts`.
   - Acceptance: Activating the obligation count moves the doc to the obligations
     section, the region/candidate counts behave consistently or stay inert by
     design, problems without obligations expose no broken affordance, and visual
     tests cover the scroll-into-view behavior.

1. **BE-029: Add verification certificate-series kind guard**
   - Goal: Keep viewer certificate lanes tied to known measured certificate
     series semantics.
   - Scope: `engine/export/verification_contract.py` and
     `tests/test_inspection_adapter.py`.
   - Acceptance: Problem payload validation rejects empty certificate-series
     `kind`, rejects unknown `kind` values, accepts `candidate-value` and
     `flow-derivative`, and focused verification export tests pass.

2. **BE-030: Add verification certificate-series problem-id guard**
   - Goal: Ensure embedded certificate metadata cannot silently point at a
     different verification problem.
   - Scope: `engine/export/verification_contract.py` and
     `tests/test_inspection_adapter.py`.
   - Acceptance: Problem payload validation rejects certificate-series
     `problemId` values that differ from the containing problem id, rejects empty
     `problemId`, accepts generated viewer examples, and focused verification
     export tests pass.
