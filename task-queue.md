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

_Frontend feature work is paused except for small maintenance while the backend
is hardened (per maintainer, VISION §11.1). The next substantial frontend task is
rendering the complete flagship **verification package** in the Verification view
(dynamics, sets, candidates, obligations, measured diagnostics) with a clear
package download/inspection path, respecting the rigor ladder. Don't invent UI
against unstable package data; don't add other frontend tasks for now._

## Backend Queue

_Direction (VISION §11): stop expanding the IR in the abstract. The whole queue
now drives **one flagship controlled system end-to-end** — backend model →
verification package → (later) frontend. The package contract exists (BE-039) and
the case studies carry per-obligation assumptions (BE-034). The flagship model has
arrived (`DRONE_MODEL_SPEC.md`): a **guard-band feedback-controlled, geofenced
point-mass drone**, whose canonical model is a **discrete** exact zero-order-hold
map with a per-axis piecewise (Piecewise) controller and a **box / forward-
invariance barrier** certificate — not Lyapunov (there is no equilibrium). BE-040
is done (`systems/drone_point_mass.py`: the Tier-1 discrete plant, guard-band law,
and a safe rollout). Route **Tier-1 geofence (P1) + velocity bound (P2)** first;
Tier-2 obstacle (P4) and Tier-3 disturbance come later. Keep generated data
uncommitted. Never label anything proved/certified — the engine proposes; external
backends dispose._

BE-041 is done: the Tier-1 **drone geofence problem** (`drone_geofence_problem`,
the decoupled `(q1, v1)` horizontal axis) is published to the viewer with the
geofence safe/inner regions, `(q1, v1)` geometry, the box-barrier candidate, the
honest forward-invariance + initial-containment obligations (the box barrier's
non-increase condition is false, so it is not used), and a discrete
candidate-value certificate series (`measured.py` now supports discrete dynamics).

BE-036 is done: region-grid `proofStatuses` now carry a numeric signed worst
`margin` to the obligation boundary (nonnegative when the sampled check holds,
negative when violated), the IR round-trips it, and the export contract validates
the optional `worst` record (value/point/time/margin), rejecting malformed shapes.

BE-042 is done: the drone now exports measured `proofStatuses` for both
obligations. `sampled_region_proof_statuses` gained an opt-in
`restrict_to_assumption_regions` flag that samples each obligation only where its
plane-expressible domain assumptions hold; the drone uses it so forward-invariance
is measured inside `speedBound` (where one guard-band step holds the geofence,
margin >= 0) instead of over all velocities (where it overshoots). Both statuses
carry BE-036 margins at rigor `measured`; pendulum/spring sampling is unchanged.
The optional P2 / admissibility obligations were left out (not needed for the
ledger) and remain available for BE-043 if the package wants them.

1. **BE-043: Assemble and export the flagship drone verification package**
   - Goal: Route the drone end-to-end into one BE-039 verification package —
     manifest, dynamics, assumptions (spec G: `speedBound`, `velBound`, `dtSmall`,
     `driftBound`), safe set, candidate, obligations, measured traces/diagnostics,
     and `(q1, v1)` visualization — completing the VISION §13 milestone on the
     backend side.
   - Scope: `scripts/export_verification_problems.py` and
     `scripts/generate_verification_problems.py`, and `tests/`.
   - Acceptance: generation publishes a complete, contract-valid drone package
     that re-reads in Python and contains every milestone component; nothing
     claims proof/certification; generated data stays uncommitted; focused tests
     pass.

2. **BE-044: Backend adapter stubs in the verification package**
   - Goal: Include optional adapter-stub descriptors in the package describing how
     external backend *categories* (reachability, SOS/certificate synthesis,
     deductive prover) would consume each obligation — descriptors of target and
     required shape only, no discharge, preserving the tool-agnostic posture.
   - Scope: `engine/verification/` (adapter-stub descriptors alongside the
     existing capability/target-requirement modules), the package writer in
     `engine/export/verification_package.py`, and `tests/`.
   - Acceptance: the drone package lists adapter stubs naming a target backend
     category and the obligation shape it would need, all honestly
     non-discharging; the export contract validates; focused tests pass.
