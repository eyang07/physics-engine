# Two-Agent Workflow (Claude + Codex)

This document is the **shared source of truth** for how the two AI agents work on
`physics-engine` without conflicting edits, duplicated responsibilities, or
unreviewed scope changes. It is referenced by `CLAUDE.md` and `AGENTS.md`; if
those files and this one ever disagree on process, this file wins for *process*
and the role files win for *responsibilities*.

> **Claude defines and protects the conceptual structure. Codex executes
> concrete repository changes against that structure.** Claude thinks broadly;
> Codex acts narrowly.

---

## Roles (no overlap)

| | Claude Code | Codex |
|---|---|---|
| **Owns** | Architecture, research/design reasoning, specs, invariants, proof/review criteria, conceptual review | Implementation, tests/builds, small diffs, CI fixes, commits/PR-ready changes |
| **Produces** | Task specs, invariants, explanations, review verdicts, doc/plan updates | Diffs, passing tests, cleaned TODOs, regenerated data, PR-ready branches |
| **Must not** | Write large speculative implementations; merge unreviewed scope changes | Redesign abstractions, change the manifest schema, or expand scope on its own |

Detailed responsibilities live in `CLAUDE.md` and `AGENTS.md`. Neither agent may
overclaim, fabricate test results, introduce scope drift, or silently change
project goals.

---

## Branch / Worktree Layout

| Worktree path | Branch | Used by | Purpose |
|---|---|---|---|
| `physics-engine/` (main repo) | base branch (`main`) | **neither agent edits here** | Source of truth; merge target only |
| `../project-claude` | `claude/planning` | Claude Code | Planning, specs, invariants, reviews, doc/plan edits |
| `../project-codex` | `codex/task-1` (and successors) | Codex | One scoped implementation task at a time |

Rules:

- **Never edit the base branch directly.** It only receives reviewed merges.
- **One branch and one worktree per task.** Two agents must never edit the same
  branch/worktree at the same time.
- Claude's *planning and review* work happens on `claude/planning`.
- Codex's *implementation* work happens on task branches named by intent:
  `codex/task-1`, `codex/fix-build`, `codex/docs-cleanup`, etc.
- Each new Codex task gets its own branch/worktree; do not pile unrelated tasks
  onto an existing task branch.

### Creating a new Codex task worktree

```sh
# from the main repo, branch fresh off the up-to-date base branch
git -C /path/to/physics-engine fetch origin
git -C /path/to/physics-engine worktree add -b codex/<task-name> ../project-codex-<task-name> origin/main
```

### Removing a worktree after merge

```sh
git -C /path/to/physics-engine worktree remove ../project-codex-<task-name>
git -C /path/to/physics-engine branch -d codex/<task-name>   # after the branch is merged
```

Use `git worktree list` to confirm the current layout at any time.

---

## The Loop

```text
1. Claude (on claude/planning): writes a Task Spec (see template) and commits it.
2. Handoff: the Task Spec is given to Codex.
3. Codex (on a codex/<task> worktree): implements exactly that spec, runs
   verification, prepares a PR-ready branch, and reports commands + results.
4. Claude (reviewing the diff): checks against the spec's invariants and the
   review checklist; returns APPROVE or CHANGES REQUESTED with specifics.
5. Merge: only after Claude approves and verification is green (see merge
   discipline). Base branch is the merge target.
6. Cleanup: remove the task worktree/branch; start the next task fresh.
```

If a task turns out to need a design decision mid-flight, Codex stops and hands
it back to Claude rather than redesigning.

---

## Claude → Codex Handoff Format

Claude hands off a **self-contained Task Spec** (see `docs/task-template.md`).
A valid handoff includes all of:

1. **Goal** — 1–2 sentences and which plan doc it advances (`VISION`/`BACKEND`/`FRONTEND`/`dynamics`).
2. **Branch** — the `codex/<task>` branch to use.
3. **Files to touch** — concrete paths.
4. **Invariants / specification** — what must remain true, with the exact
   symbolic and numerical checks and tolerances that define correctness.
5. **Step sequence** — small, independently verifiable steps in order.
6. **Test obligations** — exactly which tests to add or update.
7. **Verification commands** — which commands must pass (from the list below).
8. **Out of scope** — what Codex must not touch (e.g. "no manifest schema
   change", "no viewer physics", "no new gallery examples").

A handoff missing invariants or out-of-scope bounds is not ready; Codex should
ask for them rather than guessing.

---

## Codex Execution Checklist

- [ ] Confirmed the task is in-scope for the named branch and plan doc.
- [ ] Working in the correct `codex/<task>` worktree, branched off an up-to-date
      base; **not** on `main` or `claude/planning`.
- [ ] Read target files and the nearest existing example before editing.
- [ ] Made the smallest change that satisfies the spec; matched existing style.
- [ ] Stayed within the spec's "Files to touch" and "Out of scope".
- [ ] Added/updated the tests named in "Test obligations".
- [ ] Ran `pytest -q` (and recorded the result).
- [ ] If backend output changed: ran `python -m scripts.generate_all_examples`
      to confirm deterministic regeneration. (Generated data is **gitignored** —
      see "Generated data" below; do not try to commit it.)
- [ ] If the viewer changed: ran `cd viewer && npm run build`, and
      `npm run test:visual` when visuals changed.
- [ ] Did not disable/skip tests or edit expected values to force green.
- [ ] Reported exactly what changed and every command run, with real pass/fail.

---

## Claude Review Checklist

When reviewing a Codex diff (read-only; Claude does not rewrite the
implementation):

- [ ] Diff matches the spec's Goal and stays within "Files to touch" / scope.
- [ ] Every invariant in the spec is actually enforced by a test or argument.
- [ ] Mathematical correctness: EOM / Jacobian / divergence / conserved
      quantities / symplectic structure are right (symbolic identities simplify
      to zero; numerical residuals within stated tolerance).
- [ ] Python↔TS boundary intact: no physics derived in the viewer; no schema
      change unless the spec authorized it.
- [ ] Reusable logic lives in `engine/`; `scripts/` generators stayed thin.
- [ ] Claims are honest and labeled (proven / measured / expected / conjectured);
      no overclaiming; reported command results are plausible and were actually
      run.
- [ ] Docs/itinerary updates are accurate; no `[x]` on unverified work.
- [ ] Verdict: **APPROVE** or **CHANGES REQUESTED** with specific, actionable
      items.

---

## Merge Discipline

- Merges target the **base branch** only; agents never commit there directly.
- A branch may merge only when: Claude has **APPROVED** the diff **and** full
  verification is green for the parts touched (see Definition of Done).
- Rebase/update the task branch onto the latest base before merging; resolve
  conflicts on the task branch, never by editing `main` ad hoc.
- One task = one branch = one logically coherent merge. Do not bundle unrelated
  changes.
- Commit/push only when asked. Prefer small, verifiable commits with messages
  that state what changed and why.
- After merge, delete the task branch and remove its worktree.

---

## Definition of Done

A task is done only when **all** hold:

1. The change satisfies the spec / invariants it was given.
2. New behavior has tests: symbolic checks for derivations (RHS, Jacobian,
   divergence, energy, Noether charges) and/or trajectory checks (state schema,
   JSON export shape, invariant flatness, domain behavior).
3. `pytest -q` passes — and it was actually run.
4. If backend output changed: `python -m scripts.generate_all_examples` runs
   cleanly and reproduces deterministic output. (The output is gitignored, so
   "done" means *regenerates cleanly*, not *committed*.)
5. If the viewer was touched: `cd viewer && npm run build` is clean, and
   `cd viewer && npm run test:visual` passes when visuals changed.
6. Docs/itineraries updated if a plan item was completed (only `[ ]` → `[x]` for
   verified work).
7. Claude has reviewed and approved the diff.
8. The report lists exactly what changed and every command run with real
   pass/fail.

---

## Unclear Tasks

- **Implementation-level ambiguity** (clear intent, fuzzy detail): Codex picks
  the smallest, most conservative interpretation and records the assumption in
  its report.
- **Design-level ambiguity** (architecture, manifest schema, project scope, or
  an open question in `docs/BACKEND.md`): **stop and route to Claude / the
  human.** Codex does not invent physics, tolerances, reference values, or scope.
- Claude resolves design ambiguity by presenting the trade-off and a
  recommendation, then updating the spec — not by handing back an open menu.

---

## Failing Tests

- Never disable, skip, `xfail`, or loosen a test to force a suite green unless
  that is explicitly the task (and then record why and the removal condition).
- If a failing test encodes a mathematical invariant (energy, Noether charge,
  divergence, symplectic structure, deterministic output), assume the **code** is
  wrong, not the test, until proven otherwise.
- If a fix would require changing an abstraction, the manifest schema, or
  expected numerical values, **stop** and escalate to Claude — do not silently
  edit expected values.
- Report failures honestly with the actual output. A truthful "still failing"
  beats a fabricated green.

---

## Generated Data (repo-specific)

`data/generated/` and `viewer/public/data/*.json` are **gitignored** (see
`.gitignore`). They are regenerated locally from code + recorded parameters via
`python -m scripts.generate_all_examples`. Therefore:

- Regenerating is a **verification step** (does output reproduce deterministically?),
  not a commit step.
- Reproducibility lives in the *generators and specs*, which are tracked. If a
  change alters generated output, the fix belongs in the tracked code, not in a
  committed data blob.

---

## Verification Commands (discovered in the repo)

```sh
# Python tests — config in pyproject.toml (testpaths=tests, pythonpath=.)
pytest -q

# Regenerate all trajectories + manifest (deterministic; output is gitignored)
python -m scripts.generate_all_examples

# Viewer: install (first time), then build = type-check + bundle
cd viewer && npm install
cd viewer && npm run build        # tsc && vite build

# Viewer dev server (visual tests expect http://127.0.0.1:5173/)
cd viewer && npm run dev

# Viewer visual regression (Playwright; needs the dev server running)
cd viewer && npm run test:visual
```

**Unknowns (not invented):**

- No Python linter/formatter is configured in `pyproject.toml` (no black/ruff/
  flake8 settings). Match existing style; do not introduce or run one unless
  asked.
- No standalone JS/TS linter config (e.g. ESLint) is present; `tsc` (via
  `npm run build`) is the type-check gate.
- No CI workflow is committed in-repo (no `.github/workflows`), so "CI fixes"
  means keeping the local verification commands above green unless a CI config
  is later added.
