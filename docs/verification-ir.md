# Verification-Problem IR — Design Spec (v2)

Advances `docs/VISION.md` §10/§11 priority 3, building on the
safety/certificate layer (`docs/safety-certificates.md`). Status:
**implemented** (see Verification record at the bottom).

## Goal

Make exported verification problems genuinely dischargeable by an external
tool. IR v0 carried variables, parameters, regions, and obligations, but the
obligations arrived as pre-computed Lie-derivative expressions — the model
itself was lost, so no reachability, SOS, or deductive backend could actually
verify anything. v1 added continuous dynamics, open control/disturbance
channels, and first-class candidate-certificate records. v2 adds explicit
assumptions, links obligations to the assumptions they require, and encodes
discrete-time dynamics. The current v2 payload can also carry optional
`openLoopDynamics` alongside closed-loop `dynamics` so controlled feedback
exports preserve the admissible input channels the controller was derived
from. The engine still **proposes and organizes; external tools dispose**:
nothing in the IR stores proof results.

## Design decisions

1. **Schema bump, no migration.** `SCHEMA_VERSION` is now
   `verification-problem/v2`. Artifacts are deterministic and regenerable
   (nothing under `data/generated/` is committed), so old payloads are simply
   regenerated; the IR does not read or migrate old files.
2. **Dynamics are the model obligations were derived along.** `DynamicsSpec`
   records either `kind="continuous"` with `timeVariable` and one `rhs`
   expression per state derivative, or `kind="discrete"` with `stepVariable`
   and one `update` expression per next-state component. The safety adapters
   encode the *closed-loop* system in `dynamics`, because that is what the
   Lie derivatives or one-step differences were taken along; `dynamics` stays
   optional for obligation-only problems.
3. **Inputs are named, optionally interval-bounded channels.** `InputSpec`
   carries a role (`control` or `disturbance`) and optional lower/upper
   bounds. `dynamics_spec_from_controlled` and
   `dynamics_spec_from_controlled_discrete` encode open-loop controlled
   systems with their admissible `Box` bounds; `dynamics_spec_from_system`
   and `dynamics_spec_from_discrete` encode closed-loop systems with no
   inputs.
4. **Open-loop context is optional and non-authoritative.** Controlled
   discrete safety exports place the closed-loop map used for obligations in
   `dynamics`, the source controlled system in `openLoopDynamics`, and the
   symbolic feedback law in `metadata.feedbackLaw`. External tools can then
   inspect both the proof model and the original admissible channels without
   treating simulation or controller construction as a proof result.
5. **Candidates are first-class and link to their obligations.**
   `CandidateSpec` records kind (`lyapunov` or `barrier`), the certificate
   expression, the Lyapunov equilibrium, the candidate region, and the ids of
   the proof obligations that must be discharged before the candidate means
   anything. `status` is locked to `"candidate"` in `__post_init__`, the same
   construction-level honesty used for `ObligationSpec.rigor` and the stub
   adapter's report status.
6. **Assumptions are first-class preconditions, not results.**
   `AssumptionSpec` records model/domain/regularity facts in canonical
   expression-comparison form. Obligations reference required assumptions by
   id through `assumptionIds`. The safety adapter makes SymPy parameter-domain
   facts such as `k > 0` explicit for external backends instead of relying on
   implicit symbol assumptions.
7. **Cross-references are validated at the problem level.**
   `VerificationProblem` rejects dynamics whose state does not match the
   problem variables in order, open-loop dynamics whose state does not match
   the problem variables, candidate links to unknown obligation or region ids,
   obligation links to unknown assumption ids, duplicate candidate or
   assumption ids, assumption variables unknown to the problem, and equilibria
   of the wrong dimension. Parameters now also collect free symbols from the
   dynamics RHS/update (excluding state and time/step) and the candidate
   expression.
8. **Deferred (out of v2):** richer
   assumption languages beyond scalar expression comparisons, visualization
   hooks, real external backends, and any proof-result storage.
9. **Adapter diagnostics are outcomes, not proofs.** Verification adapters
   report normalized diagnostics through `VerificationDiagnostic` with
   statuses such as `not-attempted`, `externally-required`, `unsupported`,
   and `malformed`. The inspection stub writes these diagnostics to a
   machine-readable outcome artifact; it still cannot record success,
   discharge, proof, or certification.
10. **Adapter capability checks are explicit.** `engine.verification`
   classifies each obligation into a target family such as
   `continuous-lyapunov`, `discrete-barrier`, or `obligation-only`.
   Adapters advertise discharge capabilities separately from inspection
   support, and diagnostics include both the target classification and whether
   the adapter supports that target. The inspection stub advertises no
   discharge capabilities. Ambiguous or incomplete target shapes, currently
   mixed-candidate ownership and candidate obligations without encoded
   dynamics, are classified as malformed adapter targets rather than as
   unsupported proof attempts.

## Files

- `engine/verification/ir.py` — `DynamicsSpec`, `InputSpec`,
  `AssumptionSpec`, `CandidateSpec`, extended `VerificationProblem`, schema
  bump.
- `engine/verification/diagnostics.py` — typed adapter diagnostics with a
  small status/severity vocabulary for inspection and future backend
  integrations.
- `engine/verification/capabilities.py` — adapter capability declarations and
  deterministic obligation-target classification.
- `engine/verification/system_codec.py` — `dynamics_spec_from_system`,
  `dynamics_spec_from_controlled`, `dynamics_spec_from_discrete`,
  `dynamics_spec_from_controlled_discrete`.
- `engine/verification/safety_adapter.py` — adapters now pass the system and
  candidate through; `verification_problem_from_obligations` accepts optional
  `system`, `open_loop_system`, and `candidate` keywords, with discrete
  Lyapunov/barrier adapter entry points for both `DiscreteSystem` obligations
  and controlled-discrete feedback exports.
- `engine/verification/inspection_adapter.py` — renders Dynamics,
  Open-loop dynamics, Assumptions, and Candidate certificates report sections;
  writes canonical problem JSON, human inspection markdown, and
  machine-readable inspection outcome JSON.
- `tests/test_verification_ir.py`, `tests/test_inspection_adapter.py`.

## Invariants / proof obligations (for this implementation)

1. **Model fidelity (proven on examples).** The encoded RHS/update
   expressions of continuous and discrete systems match the symbolic systems
   they were derived from.
2. **Honest labeling (proven by construction).** `CandidateSpec` cannot be
   constructed with any status other than `"candidate"`; obligations keep
   `rigor="external-required"`; nothing in the IR can record a proof result.
3. **Assumption explicitness (proven on examples).** Positive SymPy
   parameter-domain facts are serialized as `AssumptionSpec` records, and
   exported obligations link to those records by id.
4. **Discrete safety export (proven on examples).** Discrete Lyapunov and
   barrier candidate obligations serialize with `kind="discrete"` dynamics
   and linked candidate records.
5. **Controlled discrete feedback export (proven on examples).** Controlled
   discrete Lyapunov/barrier exports serialize closed-loop discrete dynamics,
   open-loop bounded input channels, feedback-law metadata, and linked
   candidate records.
6. **Referential integrity (proven).** Mismatched dynamics state, dangling
   candidate-obligation ids, dangling obligation-assumption ids, unknown
   assumption variables, mismatched open-loop dynamics state, and
   wrong-dimension equilibria raise. Duplicate variables/parameters,
   parameter names shadowing state variables, and unknown region variables also
   raise.
7. **Determinism (measured).** Serialization remains bit-identical across
   runs; the inspection report renders the new sections deterministically.
8. **Diagnostic honesty (proven by construction).** Inspection outcomes use
   only non-success statuses (`not-attempted`, `externally-required`,
   `unsupported`, `malformed`) and every obligation receives an
   `externally-required` diagnostic until a real backend exists. Each such
   diagnostic carries its obligation target and required discharge capability.
   The inspection stub also emits target-level `unsupported` diagnostics for
   well-formed obligations it cannot discharge and `malformed` diagnostics for
   ambiguous or incomplete target shapes.

## Verification commands

```sh
pytest tests/test_verification_ir.py tests/test_inspection_adapter.py -q
pytest -q
python -m scripts.export_verification_problems
```

No generator or viewer commands: nothing crosses the manifest boundary.

## Out of scope

Everything listed under "Deferred" above, plus any change to the
manifest/export schema and any frontend surface.

## Verification record

Implemented and verified 2026-06-12 as IR v1 with dynamics and candidate
certificates. Updated 2026-06-13: IR v2 adds explicit `AssumptionSpec`
records, obligation-level `assumptionIds`, and discrete-time dynamics
encoding; focused verification/inspection tests pass with
`pytest tests/test_verification_ir.py tests/test_inspection_adapter.py -q`.
Updated later on 2026-06-13: added adapter capability declarations,
target-specific obligation classification, and stricter IR validation for
duplicate names and region variables.
Updated again on 2026-06-13: inspection diagnostics now distinguish
well-formed-but-unsupported targets from malformed target shapes such as
candidate obligations without dynamics and mixed candidate ownership.
