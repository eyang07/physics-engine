# Codex Task Queue

Self-contained implementation specs handed from Claude (planning) to Codex
(execution). Each task is scoped for one focused branch. Codex: treat the
**Invariants / specification** section as the contract, respect **Forbidden
files** literally, and report every command run with its real pass/fail outcome.
If reality contradicts the spec (a named symbol / path / field is wrong, or an
invariant cannot hold), stop and report rather than redesigning. See
`docs/agent-workflow.md` for the handoff/review/merge protocol.

---

## TASK 1 — Invariant-residual tracking for conserved quantities

- **Owner:** Codex
- **Branch:** `codex/task-1`
- **Status:** `[ ]` ready for Codex.

### Goal

Advance `docs/BACKEND.md` Itinerary #1 / "Next Best Three Items" #1: expose
numerical conservation error as a first-class diagnostic. For every mechanics
example that already exports conserved-quantity series (energy `H`, momenta
`p_*`, angular momentum `ell`, …), compute residual summaries — how far each
"conserved" quantity drifts along the integrated trajectory — and attach them to
the trajectory metadata so the viewer can later display numerical error
honestly. This automatically covers energy drift for all Hamiltonian/Lagrangian
examples.

This is a **metadata addition**, consistent with the existing
`metadata["lyapunov"]` (`scripts/generate_lorenz_attractor.py:126`),
`metadata["poincareSections"]`, and `metadata["rendererHints"]` precedents. It is
**not** a change to the core Trajectory/manifest schema (`time` / `state_names` /
`states` / `series`), and therefore needs no schema escalation.

### Exact scope

1. **Add a reusable helper** to `engine/dynamics/diagnostics.py`:
   - A frozen dataclass `InvariantResidual` with fields:
     `name: str`, `reference: float`, `max_abs: float`, `rms: float`,
     `max_relative: float | None`, `scale: float`.
   - A function
     `invariant_residuals(series: Mapping[str, Sequence[float]], *, reference: str = "initial") -> dict[str, InvariantResidual]`.
   - Export both from `engine/dynamics/__init__.py` (`__all__` + imports), matching
     the existing `LyapunovResult` / `PoincareSection` pattern, and add them to the
     module `__all__` in `engine/dynamics/diagnostics.py`.

2. **Wire it into the shared generation path** in `scripts/generation.py`:
   - In `generate_lagrangian_trajectory`, after `series = spec.series(...)` is
     computed, if `series` is non-empty, compute residuals and merge a JSON-ready
     list into the returned trajectory's `metadata` under the key
     `"invariantResiduals"`. If `series` is empty (non-mechanics systems such as
     Lorenz, whose `conserved=()`), do nothing — no key added.
   - Merge, do not overwrite: preserve any `metadata` passed in by the caller.

3. **Fix generators that rebuild metadata from scratch** so the new key survives:
   - `scripts/generate_henon_heiles.py` constructs a fresh `metadata={...}` dict in
     `Trajectory.from_arrays(...)` and would drop `invariantResiduals`. Update it to
     start from `dict(trajectory.metadata or {})` and add its extra keys (mirroring
     `scripts/generate_kepler_problem.py:95`, which already does
     `metadata = dict(trajectory.metadata or {})`).
   - **Audit every `scripts/generate_*.py`** for the same rebuild-from-scratch
     pattern and apply the same preserve-then-extend fix where found. Generators
     that pass `series=trajectory.series` and return the helper's trajectory
     directly already preserve metadata.

4. **Regenerate data**: run `python -m scripts.generate_all_examples` and commit the
   regenerated `data/generated/*.json` and `viewer/public/data/*.json` in the same
   commit as the code.

5. **Tests** (see Invariants/specification).

### JSON shape of the new metadata key

For each conserved series, emit one record. Example for the pendulum
(`conserved=("H",)`):

```json
"invariantResiduals": [
  {
    "name": "H",
    "series": "H",
    "reference": -9.62,
    "referenceKind": "initial",
    "maxAbs": 3.1e-6,
    "rms": 1.4e-6,
    "maxRelative": 3.2e-7,
    "scale": 9.62
  }
]
```

- `series` echoes the key into `trajectory.series` so the viewer can plot the full
  per-sample residual by subtracting `reference` from the existing series (pure
  subtraction — not physics — so this respects the Python=truth / TS=render
  boundary and avoids duplicating the full series in metadata).
- `referenceKind` records the reference convention (`"initial"`).
- `maxRelative` is `null` when the reference is near zero (see spec below).

### Allowed files

- `engine/dynamics/diagnostics.py` — add dataclass + function + `__all__`.
- `engine/dynamics/__init__.py` — re-export.
- `scripts/generation.py` — wire residuals into `generate_lagrangian_trajectory`.
- `scripts/generate_henon_heiles.py` — preserve helper metadata (plus any other
  generator the audit flags; confirm `scripts/generate_kepler_problem.py` already
  preserves it).
- `tests/test_invariant_residuals.py` — new helper unit tests.
- An existing trajectory test (e.g. `tests/test_more_examples.py` or
  `tests/test_new_examples.py`) — add an assertion that the exported metadata
  carries the key with the right shape.
- `data/generated/*.json`, `viewer/public/data/*.json` — regenerated outputs only.
- `docs/BACKEND.md` — flip Itinerary #1 / Next-Best #1 to `[x]` and add a
  "Completed Missions" line **only after** verification passes.

### Forbidden files

- The core Trajectory/manifest schema: `engine/export/trajectory.py` field set /
  `to_dict()` top-level keys, and `engine/export/manifest.py`. You add a metadata
  *key*; you do not change the contract.
- `spec.series(...)` semantics or the `Conserved` declarations in
  `scripts/example_specs.py`.
- Any viewer TypeScript (`viewer/src/**`). Frontend consumption of this diagnostic
  is a separate FRONTEND task; do not add it here.
- No new gallery examples, no new lens kinds, no renderer-hint changes.
- Do not reformat, re-sort imports, or rename across files.

### Invariants / specification / proof obligations

Let a series be `v[0..n-1]`, reference `r = v[0]` (since `reference="initial"`;
the conserved value is the one set by the initial conditions). Define
`d[i] = v[i] - r`. Then:

- `reference = r`.
- `max_abs = max_i |d[i]|`  → real, finite, `>= 0`.
- `rms = sqrt(mean_i d[i]^2)` → real, finite, `>= 0`, and `rms <= max_abs`.
- `scale = max(|r|, max_i |v[i]|, eps)` with a small `eps` (e.g. `1e-12`).
- `max_relative = max_abs / scale` **unless** `|r| < eps` (a genuinely near-zero
  invariant, e.g. angular momentum `ell` initialized to 0), in which case
  `max_relative = None` and only the absolute measures are meaningful.

Tests must encode these proof obligations:

1. **Exact-conservation sanity**: a constant series `[c, c, c, …]` yields
   `max_abs == 0.0`, `rms == 0.0`, `max_relative == 0.0` (or `None` if `c == 0`).
2. **Closed-form residual**: for `v = [1.0, 1.0, 1.0 + δ]` the helper returns
   `max_abs == δ`, `reference == 1.0`, `rms == sqrt(δ^2 / 3)`,
   `max_relative == δ / 1.0` (within float tolerance).
3. **Near-zero guard**: a series with `r ≈ 0` returns `max_relative is None` and a
   finite, non-negative `max_abs`.
4. **Determinism**: identical input → bitwise-identical float outputs.
5. **Validation**: empty or single-sample series raises `ValueError` with a clear
   message; a `reference` outside the supported set raises `ValueError`.
6. **Real-trajectory presence/shape**: a generated mechanics example (e.g. pendulum
   or ideal spring) exports `metadata["invariantResiduals"]` as a non-empty list;
   each record has the keys above; `series` matches a key in the exported `series`;
   energy `maxRelative` is finite and below a generous sanity ceiling (assert
   `< 1e-1`). **The ceiling must be confirmed by an actual run** — if the measured
   drift is far smaller you may tighten it, but do not invent a tolerance you did
   not observe. Report the measured value.

Do **not** present the RK4 energy residual as "energy is conserved": it is a
*measured* numerical drift, not a proof. Keep that distinction in any docstring or
doc note.

### Commands to run

(From the repo's verification set — see `docs/agent-workflow.md`. Do not invent
others.)

```sh
git branch --show-current          # must print codex/task-1 before editing
git status                         # confirm a known starting tree

pytest -q                          # full Python suite must pass (report the count)
python -m scripts.generate_all_examples
git status --porcelain data/generated viewer/public/data   # confirm regenerated outputs
cd viewer && npm run build         # type-check gate; no viewer code changed, must stay clean
```

- No Python linter/formatter is configured — match surrounding style; do not
  mass-reformat.
- `cd viewer && npm run test:visual` is **not** required (no visual change), but
  `npm run build` must stay clean.
- The known non-fatal Vite chunk-size warning is acceptable.

### Definition of done

1. `invariant_residuals` + `InvariantResidual` exist in
   `engine/dynamics/diagnostics.py`, are exported from `engine/dynamics/__init__.py`,
   and satisfy the specification above.
2. `generate_lagrangian_trajectory` attaches `metadata["invariantResiduals"]` for
   every mechanics example with a non-empty conserved-series set; non-mechanics
   examples are unaffected.
3. All generators that rebuild metadata preserve the key (henon_heiles fixed; audit
   done).
4. `pytest -q` passes — and you ran it (report the count).
5. `python -m scripts.generate_all_examples` was run; regenerated data is committed
   with the code, and the only diffs in `data/generated` / `viewer/public/data` are
   the added `invariantResiduals` blocks (plus any deterministic re-serialization).
6. `cd viewer && npm run build` is clean.
7. `docs/BACKEND.md` Itinerary #1 / Next-Best #1 flipped to `[x]` with a Completed
   Missions line — only because the above actually passed.
8. The report lists exactly what changed and every command with its real outcome,
   including the measured energy `maxRelative` for at least one example.

### Failure / reporting rules

- **A failing test that encodes a mathematical invariant** (energy, Noether charge,
  divergence, determinism) means the **code** is wrong until proven otherwise — do
  not loosen, skip, or `xfail` the test to go green.
- **Henon-Heiles drops the key**: its `Trajectory.from_arrays(..., metadata={...})`
  rebuilds metadata from scratch. If you skip step 3 its JSON will lack
  `invariantResiduals` while pendulum/spring/kepler have it — the trajectory test
  should catch this. Audit *all* generators.
- **Non-mechanics no-op**: Lorenz / variable-speed wavefront have empty or no
  conserved series. The helper must be a clean no-op (no key, no crash), not a
  `KeyError` or an empty list on everything.
- **Near-zero relative blowup**: invariants initialized to 0 (e.g. `ell`) must not
  produce `inf`/`NaN`; use the `scale` + near-zero guard and emit `null`.
- **Unexpected large data diff**: if regeneration rewrites unrelated fields or
  reorders existing keys, stop and investigate — the diff should be additive.
- If a named symbol/path/field in this spec does not match the repo, or an invariant
  cannot hold, **stop and report back** to Claude rather than redesigning.
- Report honestly: changed files grouped by intent, every command with its real
  pass/fail outcome, the measured energy `maxRelative`, and any deviation from this
  spec with its reason. Never claim a green run you did not produce.

### Review checklist (for Claude's conceptual review of the diff)

- [ ] Helper lives in `engine/` (reusable); generators stay thin — no residual math
      duplicated in `scripts/`.
- [ ] `max_abs`, `rms`, `scale` are real, finite, `>= 0`; `rms <= max_abs`; no
      `NaN`/`inf` reaches JSON; near-zero invariants yield `maxRelative: null`.
- [ ] Metadata addition only — core Trajectory/manifest schema untouched; the
      Python=truth / TS=render boundary preserved (viewer reconstructs the residual
      series by subtraction, not by recomputing physics).
- [ ] All mechanics examples carry the key; non-mechanics examples don't; no
      generator silently drops it.
- [ ] Data regenerated deterministically; the `data/generated` diff is additive.
- [ ] Tests encode the closed-form residual, the exact-conservation case, the
      near-zero guard, validation errors, determinism, and real-trajectory presence.
- [ ] Claim hygiene: residuals described as *measured numerical drift*, never as a
      proof of conservation. `docs/BACKEND.md` items flipped only post-verification.
