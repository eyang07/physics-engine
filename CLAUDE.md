# CLAUDE.md - Repository Instructions

Claude Code may plan, edit, test, and document code directly in this repository.
There is no special planner/executor split between Claude and Codex. Follow the
same engineering rules as any coding agent working here.

## Project Overview

`physics-engine` is a theory-first analytical mechanics and dynamical-systems
engine with a browser viewer.

- Python is the source of mathematical truth.
- TypeScript renders generated data and must not re-derive physics.
- Generated trajectories and manifests are deterministic and regenerable.
- Safety/certificate support is currently candidate metadata plus
  verification-problem IR, not proof or certification.

Important directories:

- `engine/mechanics/` - Lagrangian/Hamiltonian mechanics and symbolic structure.
- `engine/dynamics/` - first-order, controlled, ray/media/metric, diagnostics,
  and safety-candidate tools.
- `engine/verification/` - backend-agnostic verification-problem IR.
- `engine/numerics/` - integration.
- `engine/export/` - trajectory and manifest JSON contracts.
- `systems/` - pure symbolic system definitions.
- `scripts/` - registry and generators.
- `viewer/` - Vite/TypeScript viewer.
- `tests/` - backend and export regression tests.

## Working Principles

- Preserve the Python-to-TypeScript boundary: Python computes and exports;
  TypeScript renders.
- Prefer reusable backend abstractions over one-off generator logic.
- Keep manifest/export schema changes deliberate and documented.
- Never claim proof or certification from simulation or sampling.
- Distinguish symbolic identities, measured numerical evidence, externally
  required obligations, and certified/proved results.
- Match existing style; avoid unrelated refactors and mass formatting.
- Do not commit generated data under `data/generated/` or
  `viewer/public/data/*.json`.

## Common Commands

```sh
pytest -q
python -m scripts.generate_all_examples
cd viewer && npm run build
cd viewer && npm run dev
cd viewer && npm run test:visual
```

Use focused checks for small changes. Run broad backend/viewer checks when the
change touches shared contracts, generated output, or release-critical behavior.

## Editing Guidance

Python:

- Use `from __future__ import annotations`.
- Prefer modern typing (`tuple[...]`, `X | None`, `Mapping`, `Sequence`).
- Use frozen dataclasses for value objects and validate invariants in
  `__post_init__`.
- Use SymPy for symbolic math and NumPy/SciPy for numerics.
- Keep `systems/` definitions symbolic and thin.
- Keep reusable logic in `engine/`; keep `scripts/` as thin generation entry
  points.

TypeScript:

- Keep rendering logic in the viewer and physics logic out of it.
- Consume manifest/trajectory data directly.
- Reuse existing viewer primitives before adding parallel rendering paths.

Docs:

- Keep `README.md`, `docs/BACKEND.md`, `docs/FRONTEND.md`, and
  `docs/VISION.md` accurate when capabilities or direction change.
- Remove completed itinerary churn instead of preserving stale checklists.

## Verification Discipline

- Never fabricate test/build results.
- Do not skip, xfail, or loosen tests just to get green unless explicitly asked.
- If a mathematical invariant test fails, assume the code is wrong until proven
  otherwise.
- If a requested change requires a major abstraction or schema shift, make that
  decision explicit in docs and tests.
