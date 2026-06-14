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

1. **FE-001: Finish the self-contained Verification stage**
   - Goal: Complete the Verification-domain stage that animates the exported
     verification trajectory with region geometry and candidate-certificate
     lanes, independent of the Systems gallery.
   - Scope: `viewer/index.html`, `viewer/src/main.ts`,
     `viewer/src/verificationStage.ts`, `viewer/src/certificateLanes.ts`,
     `viewer/src/data/verification.ts`, and related styling.
   - Acceptance: Switching to Verification loads the selected problem's own
     `trajectory`, overlays exported `regionGeometry`, draws certificate lanes
     from exported series, never evaluates symbolic expressions in TypeScript,
     and `cd viewer && npm run build` passes.

2. **FE-002: Add visual coverage for the Verification stage**
   - Goal: Cover the new Verification stage and certificate lanes in Playwright
     so layout, canvas rendering, and empty-trajectory fallback do not regress.
   - Scope: `viewer/tests` or the existing visual-test harness, plus targeted
     viewer fixtures/helpers if needed.
   - Acceptance: Visual tests exercise the default verification problem, verify
     the stage canvas is nonblank, cover a no-trajectory or unavailable-data
     state without misleading overlays, and `cd viewer && npm run test:visual`
     passes with the dev server running.

3. **FE-003: Mark measured violation samples on the Verification stage**
   - Goal: When a `proofStatuses` entry reports `measured-violated` with a
     worst sampled point that maps to the active projection, show that point on
     the stage alongside the trajectory.
   - Scope: `viewer/src/data/verification.ts`, `viewer/src/verificationStage.ts`,
     safety-region rendering helpers, and focused visual coverage.
   - Acceptance: Violations are visually distinguished from safe/unsafe region
     boundaries, absent or unmappable samples do not render misleading markers,
     and visual tests cover at least the no-marker and marker paths.

## Backend Queue

1. **BE-010: Add inspection index CLI smoke coverage**
   - Goal: Keep the backend inspection export CLI discoverable by checking its
     default and custom-output behavior without writing committed generated
     artifacts.
   - Scope: `tests/test_inspection_adapter.py`,
     `scripts/export_verification_problems.py`, and documentation only if CLI
     behavior changes.
   - Acceptance: Tests exercise the CLI entry point with a temporary output
     directory, assert the printed artifact/index paths are deterministic, and
     confirm no generated artifacts are expected in the repository tree.

2. **BE-011: Add verification artifact index schema validation**
   - Goal: Validate the inspection artifact index shape independently from the
     export script so downstream backend tools can rely on a narrow discovery
     contract.
   - Scope: `engine/verification/` or `engine/export/` validation helpers,
     `tests/test_inspection_adapter.py`, and docs if validation behavior is
     documented.
   - Acceptance: A reusable validator rejects missing schema versions, duplicate
     problem ids, missing artifact paths, and unknown artifact kinds; focused
     inspection tests cover valid and invalid indexes.
