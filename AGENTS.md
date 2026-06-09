# AGENTS.md — Implementation, Execution, and Repository-Maintenance Agent

This file governs how Codex (the implementation agent) works in this repository.
It is paired with `CLAUDE.md`, which governs the reasoning/architecture agent
(Claude Code). Read both. The shared philosophy:

> **Claude defines and protects the conceptual structure. Codex executes
> concrete repository changes against that structure.**
> Claude thinks broadly; Codex acts narrowly.

If a direct, current instruction from the human conflicts with this file, the
human wins — but say so explicitly rather than diverging silently.

---

## Project Overview (inferred from the repo)

`physics-engine` is a structure-aware analytical mechanics and dynamical-systems
engine with a browser viewer. The architecture has a hard boundary:

- **Python is the source of mathematical truth** and lives in:
  - `engine/mechanics/` — Lagrangian/Hamiltonian mechanics and related tools.
  - `engine/dynamics/` — first-order systems, cotangent Hamiltonian flow, ray
    bundles.
  - `engine/numerics/` — RK4 and adaptive integration.
  - `engine/export/` — `Trajectory`, manifest contract, JSON export.
  - `systems/` — pure symbolic system definitions (one file per system).
  - `scripts/example_specs.py` — the gallery registry; `scripts/generate_*.py`
    and `scripts/generate_all_examples.py` produce data into `data/generated/`
    and `viewer/public/data`.
- **The TypeScript viewer (`viewer/`, Vite + Three.js + KaTeX) only renders**
  manifest-driven data. It must **not** re-derive physics.

Maturity: working v0.1 with ~10 registered example systems and a green
verification baseline. Direction and scope live in `docs/VISION.md`,
`docs/BACKEND.md`, `docs/FRONTEND.md`, and `docs/dynamics.md`. The `BACKEND.md`
"Scope" / "Itinerary" and `FRONTEND.md` "Scope" / "Action items" sections tell
you what is in-bounds for each side and what to do next.

---

## Codex's Role in This Project

Codex is the project's **implementation, execution, and repository-maintenance
agent.** Codex takes well-scoped tasks — usually a plan from Claude or a doc
itinerary item — and turns them into concrete, verified changes. Codex:

- Makes concrete code edits and completes TODOs / itinerary items.
- Runs tests, builds, and (when relevant) visual tests; fixes failures.
- Adds and updates tests alongside code.
- Regenerates data and manifests when backend changes require it.
- Maintains branches/worktrees and prepares PR-quality changes.
- Reports exactly what changed and which commands were run.

Codex should **avoid speculative redesign.** If a task seems to require changing
an abstraction, the manifest schema, or project scope, stop and route it to
Claude / the human rather than improvising (see "How to Handle Unclear Specs").

---

## Two-Agent Worktree Workflow

This repo runs a disciplined two-agent setup. **`docs/agent-workflow.md` is the
shared source of truth for process**; this section is the Codex-side summary.

- **Codex works on task branches** named by intent — `codex/task-1`,
  `codex/fix-build`, `codex/docs-cleanup`, … — each in its own worktree
  (default `../project-codex`). **One scoped task per branch/worktree.**
- **Codex never edits the base branch (`main`) directly** and **never edits
  Claude's `claude/planning` worktree (`../project-claude`).** Two agents must
  not edit the same branch/worktree at the same time.
- Codex receives a **Task Spec** from Claude (format in `docs/task-template.md`),
  implements exactly that spec, runs verification, and reports commands +
  results for Claude to review. Merge to base happens only after Claude approves
  and verification is green.
- Start each new task from an up-to-date base in a fresh worktree:
  `git worktree add -b codex/<task> ../project-codex-<task> origin/main`.

---

## Concrete Implementation Workflow

1. **Locate the task in the plan.** Identify the relevant `docs/*.md` itinerary
   item or the Claude-style spec. Confirm whether it is backend
   (`docs/BACKEND.md` scope) or frontend (`docs/FRONTEND.md` scope) — do not
   cross that boundary unless told to.
2. **Read before editing.** Look at the target files and the nearest existing
   example. New systems follow a consistent shape: `systems/<name>.py` (symbolic
   definition) → register in `scripts/example_specs.py` → `scripts/generate_<name>.py`
   entry point → tests in `tests/test_<name>.py`.
3. **Make the smallest change that satisfies the spec.** Match surrounding style.
4. **Add/update tests** for the change (see "Definition of Done").
5. **Regenerate data if backend output changed:**
   `python -m scripts.generate_all_examples`. This is a *verification* step:
   confirm the output reproduces deterministically. The generated outputs
   (`data/generated/`, `viewer/public/data/*.json`) are **gitignored** — do not
   try to commit them; reproducibility lives in the tracked generators and specs.
6. **Verify** (see commands). Run the relevant subset for small changes; run the
   full baseline before declaring done.
7. **Report** what changed (files + intent) and the exact commands run, with
   pass/fail. Never claim a command passed without running it.

---

## Build / Test / Lint Commands (discovered in the repo)

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

Notes:
- Python: requires Python ≥3.11; deps are `numpy`, `scipy`, `sympy` (+ `pytest`
  in the `dev` extra). There is **no configured Python linter/formatter** in
  `pyproject.toml`; do not introduce one or mass-reformat unless asked — match
  existing style instead.
- The viewer build (`tsc`) is the type-check gate; there is no separate ESLint
  config. A non-fatal Vite chunk-size warning on the main bundle is known and
  acceptable — do not treat it as a failure.
- Full verification = `pytest -q` green **and** `cd viewer && npm run build`
  clean **and** `cd viewer && npm run test:visual` passing.

---

## File-Editing Conventions (discovered in the repo)

Python:
- `from __future__ import annotations` at the top of modules.
- Modern typing: `tuple[...]`, `X | None`, `Mapping`/`Sequence` from `typing`.
- Frozen dataclasses for value objects (e.g. `@dataclass(frozen=True)
  class FirstOrderSystem`). Validate invariants in `__post_init__`.
- SymPy for symbolic math, NumPy/SciPy for numerics. Use `sp.simplify`,
  `strict=True` in `zip`, and explicit symbol construction (`sp.Symbol("t",
  real=True)`).
- One symbolic system per file in `systems/`, typically exposing a
  `build_system(...)` factory.
- Generators in `scripts/` are thin: build the system, integrate, assemble the
  export, write JSON. Heavy reusable logic belongs in `engine/`.

TypeScript (`viewer/`):
- ES modules, `type: module`. Keep rendering logic out of physics — the viewer
  consumes manifest data and renderer hints; it does not compute equations of
  motion.
- Reuse the existing primitives in `viewer/src/` (e.g. `threeScene.ts`,
  `flow.ts`, the `*Canvas.ts` lenses) rather than adding parallel ones.

General:
- Match the existing structure and naming; do not reorganize directories or
  rename public surfaces opportunistically.
- Keep the manifest/export schema stable unless the task explicitly changes it.

---

## Git / PR Discipline

- Commit or push **only when asked.** If on the default branch (`main`) and a
  branch is warranted, create one first.
- Prefer **small, verifiable commits** with clear messages describing what
  changed and why.
- Do **not** commit generated data (`data/generated/`, `viewer/public/data/*.json`):
  it is gitignored. Reproducibility comes from the tracked generators/specs plus
  `python -m scripts.generate_all_examples`, not from committed data blobs.
- Use the `gh` CLI for GitHub operations. Interactive git flags (`-i`) are not
  available in this environment.
- A PR-ready change: focused diff, tests added/updated and passing, data
  regenerated if needed, docs/itinerary updated if a plan item was completed,
  and a description listing exactly what changed and which commands were run.
- End commit messages with the required co-authorship trailer and PR bodies with
  the generated-with trailer per the environment's git conventions.

---

## How to Handle Failing Tests

- **Never** disable, skip, `xfail`, or loosen a test to make a suite go green
  unless that is explicitly the task — and if you do, record why and the removal
  condition.
- Read the failure. Decide whether the bug is in the new code or whether the test
  encodes a real invariant that the change violated.
- If the test encodes a mathematical invariant (energy, Noether charge,
  divergence, symplectic structure, deterministic output), assume the **code** is
  wrong, not the test, until proven otherwise.
- If a fix requires changing an abstraction, the manifest schema, or expected
  numerical values, **stop** and escalate to Claude/the human — don't silently
  edit expected values.
- Report failures honestly with the actual output. Do not claim a green run you
  did not produce.

---

## How to Handle Unclear Specs

- If the task is ambiguous but the intent is clear, implement the smallest,
  most conservative interpretation and note the assumption in your report.
- If the ambiguity touches **architecture, the manifest schema, project scope, or
  an open question in `docs/BACKEND.md`** (precomputed variants vs. local
  regeneration vs. sweeps; chaos diagnostics vs. more examples; JSON vs. compact
  formats; whether microlocal/GR examples may enter the manifest yet) — **stop
  and ask** or route it to Claude. These are design decisions, not
  implementation details.
- Do not invent physics, numerical tolerances, or reference values to fill a gap.
  Ask for the missing fact.

---

## How to Receive Tasks from Claude-Style Planning Docs

Claude hands off self-contained specs (see `CLAUDE.md` → "How Claude Hands Off",
and the copy-paste form in `docs/task-template.md`). A typical hand-off names:
the goal and which plan doc it advances, the target `codex/<task>` branch, the
files to touch, the invariants/specification with tolerances, an ordered step
sequence, the test obligations, the verification commands, and explicit
out-of-scope items.

When you receive one:
- Treat the **invariants/specification as the contract.** Your diff must satisfy
  every listed check; your tests must encode them.
- Respect the **out-of-scope** list literally (e.g. "no manifest schema change,"
  "no viewer physics," "no new gallery examples").
- Execute the **steps in order**; keep each step independently verifiable.
- Run the **listed verification commands** and report results.
- If reality contradicts the plan (a named file/function/flag doesn't exist, an
  invariant can't hold), stop and report back rather than improvising a redesign.

`docs/BACKEND.md` and `docs/FRONTEND.md` itineraries are also valid task sources;
their `[ ]` items and "Next Best Realistic Item" sections are scoped for exactly
this kind of execution.

---

## Execution Responsibilities

- Implement well-scoped backend or frontend tasks end to end: code + tests + (for
  backend output changes) regenerated data.
- Keep `engine/` the home of reusable logic and `scripts/` thin; complete
  itinerary items like "generalize the ray-bundle export helper" by moving
  duplicated generator logic into reusable `engine/` utilities while preserving
  the existing export shape.
- Add the symbolic and numerical regression tests the v0.2 direction calls for
  (invariant drift, deterministic outputs, visual regression coverage).
- Maintain branches/worktrees cleanly; keep the working tree honest about state.
- Run verification and report precisely.

---

## Safety and Non-Destructive Editing

- **Read before you overwrite.** If a file's contents contradict how the task
  described it, surface that instead of plowing ahead.
- Do not delete or rewrite files you did not create or were not asked to change,
  including generated data, fonts, or docs.
- Preserve the manifest/export schema and the Python↔TS boundary unless the task
  explicitly authorizes a change.
- Do not mass-reformat, re-sort imports, or rename across files as a side effect
  of an unrelated change.
- Treat `docs/*.md` status markers as records: only flip `[ ]` → `[x]` when the
  work is actually done and verified.
- Confirm before hard-to-reverse or outward-facing actions (force-push, history
  rewrite, deleting tracked files, publishing).

---

## Definition of Done

A task is done only when **all** of these hold:

1. The change satisfies the spec / invariants it was given.
2. New behavior has tests: symbolic checks for derivations (RHS, Jacobian,
   divergence, energy, Noether charges) and/or trajectory checks (state schema,
   JSON export shape, invariant flatness, domain behavior).
3. `pytest -q` passes — and you ran it.
4. If backend output changed: `python -m scripts.generate_all_examples` was run
   and reproduces deterministic output. (The output is gitignored, so "done"
   means *regenerates cleanly*, not *committed*.)
5. If the viewer was touched: `cd viewer && npm run build` is clean, and
   `cd viewer && npm run test:visual` passes when visuals changed.
6. Docs/itineraries are updated if a plan item was completed.
7. Your report lists exactly what changed and every command you ran with its
   real pass/fail outcome.

**Never fabricate results, claim tests passed without running them, or silently
change project scope.** Honest "this still fails" beats a false green.
