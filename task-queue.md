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

1. **FE-018: Show honest empty states across the Verification surfaces**
   - Goal: Make absence legible rather than silent — when a problem exports no
     certificate series (or no proof statuses), show an explicit honest
     placeholder instead of an empty panel, so a reader can tell "no measured
     evidence" apart from a rendering gap (VISION §6 legibility/honesty).
   - Scope: `viewer/src/certificateLanes.ts` and/or `viewer/src/verificationStage.ts`
     (placeholder when no lanes), `viewer/src/verificationPanel.ts` (placeholder
     when a section is empty), `viewer/src/styles.css`, and visual coverage in
     `viewer/tests/visual.spec.ts`.
   - Acceptance: A problem with no certificate series shows an explicit "no
     measured certificate series" note, the populated case is unchanged, the copy
     never implies a result, and visual tests cover the empty/populated paths.
     Frontend-only — no new exported fields.

## Backend Queue

_No backend tasks queued (pending discussion)._
