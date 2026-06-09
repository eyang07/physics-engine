# Agent Workflow — Claude (planning) ⇄ Codex (execution)

This file defines how the two-agent workflow operates in this repository. It is
the procedural companion to `CLAUDE.md` (Claude's charter) and `AGENTS.md`
(Codex's charter). Shared philosophy:

> **Claude defines and protects the conceptual structure. Codex executes
> concrete repository changes against that structure.**
> Claude thinks broadly; Codex acts narrowly.

If a direct, current human instruction conflicts with this file, the human wins
— but say so explicitly rather than diverging silently.

---

## Worktrees and branches

Two long-lived git worktrees of the same repository, one per agent:

| Agent  | Worktree path        | Branch           | Purpose                                    |
| ------ | -------------------- | ---------------- | ------------------------------------------ |
| Claude | `../project-claude`  | `claude/planning`| Architecture, specs, reviews, docs         |
| Codex  | `../project-codex`   | `codex/task-1`   | Scoped implementation for the active task  |

- `main` is the integration branch; neither agent commits directly to it.
- Codex works one task per branch. The branch name tracks the active task
  (`codex/task-1`, then `codex/task-2`, …). A new task gets a fresh branch off
  the latest `main`.
- Claude's `claude/planning` branch holds planning docs (`docs/agent-workflow.md`,
  `docs/task-queue.md`) and doc/spec edits. These are merged to `main` so that
  Codex's worktree can see them — a task is not actionable until its spec exists
  on the branch Codex builds from.

---

## Roles

**Claude — reasoning, architecture, research/design, review.**
- Owns the conceptual structure: the Python = truth / TypeScript = render
  boundary, the manifest/export contract, the mechanics vs. first-order split.
- Produces self-contained task specs in `docs/task-queue.md`, with invariants,
  proof obligations, tolerances, and out-of-scope lists.
- Reviews Codex's diffs for mathematical correctness, conceptual coherence, and
  contract stability.
- Writes the small, **conceptually delicate** load-bearing code when a change
  hinges on getting an abstraction or an invariant exactly right — and says so
  explicitly when it does.
- Keeps `docs/*.md` honest; does not mark plan items `[x]` on say-so.

**Codex — scoped implementation, verification, repository maintenance.**
- Takes one spec from `docs/task-queue.md` (or a `docs/*.md` itinerary item) and
  turns it into a focused, verified diff.
- Adds/updates tests alongside code; runs tests, builds, and (when visuals
  change) visual tests; fixes failures and CI.
- Regenerates data/manifests when backend output changes, committing regenerated
  outputs with the code that produced them.
- Keeps diffs small and PR-ready; reports exactly what changed and which commands
  ran with real pass/fail.
- Does **not** redesign abstractions, change the manifest/export schema, or
  expand scope. If a task seems to require that, stop and route it back to Claude.

---

## Pre-edit checks (both agents, every session)

Before editing anything, confirm you are in the right worktree on the right
branch:

```sh
git branch --show-current      # Claude expects claude/planning; Codex expects codex/task-1
git status                     # confirm a clean/known starting tree before you start
```

If the branch is not what you expect, stop and fix the worktree before editing.
Do not start a task on the wrong branch.

---

## Handoff format (Claude → Codex)

Claude hands off by writing a task block in `docs/task-queue.md`. A complete
handoff contains, at minimum:

1. **Owner / Branch** — `Codex` / `codex/task-N`.
2. **Goal** — one or two sentences, and which `docs/*.md` item it advances.
3. **Allowed files** — concrete paths Codex may edit.
4. **Forbidden files** — paths and surfaces Codex must not touch (e.g. the
   manifest/export schema, viewer physics, other examples).
5. **Invariants / specification / proof obligations** — what must remain true,
   with the symbolic checks and numerical tolerances that define correctness.
6. **Commands to run** — from the repo's verification set (below); no invented
   commands.
7. **Definition of done** — the checklist that makes the task complete.
8. **Failure / reporting rules** — what to do when a check fails, and what to
   report.

Codex treats the invariants/specification as the contract and the forbidden list
literally. If reality contradicts the spec (a named symbol/path/field is wrong,
or an invariant cannot hold), Codex stops and reports rather than improvising.

---

## Review format (Codex → Claude)

When Codex reports a finished task, it states:

- **Changed files** — every path touched, grouped by intent.
- **Commands run** — each verification command with its **real** pass/fail
  outcome (e.g. test count, build clean/failed). Never a claimed-but-unrun green.
- **Measured numbers** — any residual/tolerance the spec asked to be confirmed by
  a real run, with the value observed.
- **Deviations / assumptions** — anything implemented differently from the spec,
  and why.
- **Open risks** — anything Claude should scrutinize.

Claude reviews against the task's **Review checklist** and the project invariants
in `CLAUDE.md`: mathematical correctness, the truth/render boundary, schema
stability, deterministic regeneration, and claim hygiene (measured ≠ proven,
expected ≠ verified). Claude either approves, or returns specific, checkable
change requests.

---

## Merge discipline

- One task → one branch → one focused PR. Keep diffs additive and reviewable.
- A branch is mergeable only when its **Definition of done** holds and Claude's
  review passes.
- Generated outputs (`data/generated/`, `viewer/public/data/`) are committed in
  the **same commit** as the code that produces them, so the repo stays
  reproducible.
- Commit or push only when asked. Do not commit to `main` directly; integrate via
  the task branch.
- Doc/spec branches (`claude/planning`) merge to `main` so Codex can see specs
  before starting; never start a Codex task whose spec is not yet on its branch.
- `docs/*.md` status markers (`[ ]` → `[x]`) flip only when the work exists and
  verification has actually passed — never on say-so.
- Prefer small, verifiable commits with messages describing what changed and why;
  use the `gh` CLI for GitHub operations.

---

## Verification commands (discovered in the repo; do not invent)

From `CLAUDE.md` and `AGENTS.md`:

```sh
# Python tests — config in pyproject.toml (testpaths=tests, pythonpath=.)
pytest -q

# Regenerate all trajectories + manifest into data/generated and viewer/public/data
python -m scripts.generate_all_examples

# Viewer: install (first time), then build = type-check + bundle
cd viewer && npm install
cd viewer && npm run build        # tsc && vite build

# Viewer dev server (visual tests expect http://127.0.0.1:5173/)
cd viewer && npm run dev

# Viewer visual regression (Playwright; needs the dev server running)
cd viewer && npm run test:visual
```

Notes (from the repo):
- There is **no configured Python linter/formatter**; match existing style, do
  not mass-reformat.
- `tsc` (via `npm run build`) is the viewer type-check gate; there is no separate
  ESLint config.
- A non-fatal Vite chunk-size warning on the main bundle is known and acceptable.

Full-project verification = `pytest -q` green **and** `cd viewer && npm run build`
clean **and** `cd viewer && npm run test:visual` passing (the last only required
when visuals change).

---

## Definition of done (workflow-level)

A task is done only when **all** hold:

1. The change satisfies the spec / invariants it was given.
2. New behavior has tests (symbolic checks for derivations and/or trajectory
   checks for exported shape and invariants).
3. `pytest -q` passes — and was actually run.
4. If backend output changed: `python -m scripts.generate_all_examples` was run
   and regenerated data is committed with the code.
5. If the viewer was touched: `cd viewer && npm run build` is clean, and
   `cd viewer && npm run test:visual` passes when visuals changed.
6. Docs/itineraries are updated only if a plan item was genuinely completed.
7. The report lists exactly what changed and every command run with its real
   pass/fail outcome.

Never fabricate results, claim a green run you did not produce, or silently
change project scope. Honest "this still fails" beats a false green.
