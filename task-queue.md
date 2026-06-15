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

1. **FE-011: Jump from a measured-status card to its obligation card**
   - Goal: Let each measured-status card link to the obligation it sampled so the
     measured evidence is navigable back to the obligation it bears on, reusing
     the obligation-card ids and jump pattern already in `verificationPanel.ts`.
   - Scope: `viewer/src/verificationPanel.ts` (make the measured-status card's
     obligation name scroll/emphasize the matching obligation card),
     `viewer/src/styles.css`, and visual coverage in `viewer/tests/visual.spec.ts`.
   - Acceptance: Activating a measured-status card's obligation link brings the
     matching obligation card into view and emphasizes it, status rows whose
     obligation id has no obligation card stay inert, and visual tests cover the
     navigate behavior.

2. **FE-012: Show each obligation's stated assumptions on its card**
   - Goal: Make "valid only under stated assumptions" (VISION §6) legible by
     rendering, on each obligation card, the assumptions it depends on via the
     already-exported `assumptionIds`, with a jump to the matching assumption.
   - Scope: `viewer/src/verificationPanel.ts` (render an obligation card's
     `assumptionIds` and link them to the assumptions section, reusing the
     card-anchor pattern), `viewer/src/styles.css`, and visual coverage in
     `viewer/tests/visual.spec.ts`.
   - Acceptance: An obligation with `assumptionIds` lists them and each one
     navigates to its assumption; an obligation with none shows no broken chrome;
     ids with no matching assumption stay inert; visual tests cover the
     present/absent and navigate paths. Frontend-only — no new exported fields.

3. **FE-013: Add a per-obligation status ledger to the Verification doc**
   - Goal: Give the problem an at-a-glance, honestly labeled safety picture: one
     compact ledger row per obligation showing its measured outcome
     (holds/violated/not sampled), rigor badge, and standing `external-required`
     status, so the rigor ladder (VISION §7) is legible without scanning cards.
   - Scope: `viewer/src/verificationPanel.ts` (derive the ledger from
     `obligations` + `proofStatuses`, placed near the header), each row links to
     its obligation card (reuse the existing obligation-card anchors),
     `viewer/src/styles.css`, and
     visual coverage in `viewer/tests/visual.spec.ts`.
   - Acceptance: Every obligation appears once with its measured outcome and a
     never-"proved" status, obligations with no sampled status read as "not
     sampled", a row navigates to its card, and visual tests assert the ledger
     contents. Frontend-only — no new exported fields.

4. **FE-014: Surface the rigor ladder and the problem's current level**
   - Goal: Make the four-level rigor ladder (VISION §7) explicit in the
     Verification domain and mark where the current problem sits (level 1 —
     measured evidence with `external-required` obligations) so "measured" can
     never be read as "proved".
   - Scope: `viewer/src/verificationPanel.ts` (a rigor-ladder legend that derives
     the current level from the problem's statuses/obligation rigor),
     `viewer/src/styles.css`, and visual coverage in
     `viewer/tests/visual.spec.ts`.
   - Acceptance: The ladder lists all four levels with the current one marked at
     level 1 for the exported case studies, the copy never implies proof or
     certification, and visual tests assert the marked level and labels.
     Frontend-only — derives level from already-exported rigor fields.

5. **FE-015: Tie measured evidence to the obligation it bears on**
   - Goal: Let selecting an obligation (from its card or the FE-013 ledger)
     highlight the certificate lane(s) and comparison baseline that bear on it —
     via `certificateSeries[].obligationIds` and `comparisonBaselines` — so a user
     sees which measured signal supports which obligation (VISION §6 legibility).
   - Scope: `viewer/src/certificateLanes.ts` and `viewer/src/verificationPanel.ts`
     (obligation selection → lane/baseline emphasis), `viewer/src/styles.css`, and
     visual coverage in `viewer/tests/visual.spec.ts`.
   - Acceptance: Selecting an obligation emphasizes only the lanes/baselines that
     reference it, selection clears when the problem changes, obligations with no
     referencing lane stay interaction-free, and visual tests cover the
     emphasis/clear behavior. Frontend-only — uses already-exported links.

6. **FE-016: Download the selected verification problem as a backend-agnostic
   artifact**
   - Goal: Realize the Definition of Success "export a backend-agnostic
     verification problem that an external tool can attempt to discharge" by
     offering, in the Verification domain, a control to download/copy the
     canonical IR artifact for the selected problem.
   - Scope: `viewer/src/verificationPanel.ts` or `viewer/src/main.ts` (fetch and
     download/copy the published IR artifact), `viewer/src/styles.css`, and visual
     coverage in `viewer/tests/visual.spec.ts`.
   - Acceptance: The control downloads the backend-agnostic IR JSON (not the
     viewer-shaped payload) for the active problem, is absent/inert when no IR
     artifact is published, and visual tests cover the affordance. **Depends on
     BE-032** publishing the IR artifact and a path to it in the viewer export.

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

3. **BE-032: Publish the backend-agnostic verification-problem IR for the viewer**
   - Goal: Support FE-016 by making each problem's canonical backend-agnostic IR
     artifact (the inspection adapter's problem JSON, distinct from the
     viewer-shaped payload) reachable by the viewer, so the frontend can offer it
     for routing to an external backend.
   - Scope: `scripts/generate_verification_problems.py` (also write the IR
     artifact under the viewer data dir), `engine/export/verification_contract.py`
     (record/validate an `irPath` or equivalent in the index/payload), and
     `tests/test_inspection_adapter.py`.
   - Acceptance: Generation publishes a backend-agnostic IR JSON per problem
     alongside the viewer payload, the export contract validates its presence and
     basename like the existing data-path checks, the published IR round-trips
     through the IR loader, and focused verification export tests pass. Keep the
     IR artifact out of committed generated data per repository policy.
