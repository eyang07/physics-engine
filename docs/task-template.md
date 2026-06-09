# Task Spec Template (Claude → Codex)

Copy this block per task. Claude fills it out on `claude/planning`; Codex
executes it on the named `codex/<task>` branch. See `docs/agent-workflow.md` for
the surrounding process. A spec missing invariants or out-of-scope bounds is not
ready to hand off.

```markdown
## Task: <short imperative title>

**Branch:** codex/<task-name>
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
- tests/test_<name>.py — <symbolic checks: RHS / Jacobian / divergence / energy / Noether>
- tests/test_<name>.py — <trajectory checks: state schema / JSON export shape / invariant flatness / domain behavior>

### Verification commands (must pass)
- [ ] pytest -q
- [ ] python -m scripts.generate_all_examples   # if backend output changed (output is gitignored)
- [ ] cd viewer && npm run build                # if viewer changed
- [ ] cd viewer && npm run test:visual          # if visuals changed

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
