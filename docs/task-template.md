# Task Spec Template (Claude → Codex)

Copy this block per task. Claude fills it out on `claude/planning`; Codex
executes it on the current branch for small direct work, or on a named
`codex/<task>` branch when isolation/review is useful. See
`docs/agent-workflow.md` for the surrounding process.

```markdown
## Task: <short imperative title>

**Branch:** current branch | codex/<task-name if isolation/review is useful>
**Advances:** <docs/VISION.md | docs/BACKEND.md | docs/FRONTEND.md | docs/dynamics.md> — <which item>
**Status:** draft | ready-for-codex | in-progress | in-review | done

### Goal
<1–2 sentences: what changes and why.>

### Files to touch
- <path> — <what changes>
- <path> — <what changes>

### Invariants / specification
<What must remain true. Be concrete and checkable.>
- Symbolic: <identity that must simplify to 0, e.g. divergence + (sigma+beta+1) == 0>
- Numerical: <residual + tolerance, e.g. energy drift |ΔE/E| < 1e-6 over the run>
- Contract: <e.g. manifest schema unchanged; export keys X, Y, Z preserved>

### Step sequence
1. <small, independently verifiable step>
2. <...>

### Test obligations
- <Only tests worth adding/updating for meaningful behavior, math invariants, export contracts, or regressions.>
- <Use "none" for low-risk wiring, docs, copy, or obvious one-line fixes.>

### Verification commands (choose the smallest useful set)
- [ ] targeted pytest path/test name             # if backend behavior changed
- [ ] pytest -q                                  # broad backend/shared changes only
- [ ] specific generator                         # if one system's output changed
- [ ] python -m scripts.generate_all_examples    # shared output/export changes only
- [ ] cd viewer && npm run build                 # TypeScript/bundling changes
- [ ] cd viewer && npm run test:visual           # visual rendering/layout changes

### Out of scope
- <e.g. do not change the manifest/export schema>
- <e.g. no viewer physics; the viewer only renders>
- <e.g. no new gallery examples; backend-only prototype>

### Codex report (filled in on completion)
- Files changed: <...>
- Commands run + results: <...>
- Assumptions made: <...>
- Open questions for Claude: <...>

### Claude review (filled in at review)
- Verdict: APPROVE | CHANGES REQUESTED
- Notes: <specific, actionable>
```
