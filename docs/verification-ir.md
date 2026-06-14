# Verification-Problem IR — Design Spec (v3)

Advances `docs/VISION.md` §10/§11 priority 3, building on the
safety/certificate layer (`docs/safety-certificates.md`). Status:
**implemented** (see Verification record at the bottom).

## Goal

Make exported verification problems genuinely dischargeable by an external
tool. IR v0 carried variables, parameters, regions, and obligations, but the
obligations arrived as pre-computed Lie-derivative expressions — the model
itself was lost, so no reachability, SOS, or deductive backend could actually
verify anything. v1 added continuous dynamics, open control/disturbance
channels, and first-class candidate-certificate records. v2 added explicit
assumptions, links obligations to the assumptions they require, and encodes
discrete-time dynamics. The v2 payload can also carry optional
`openLoopDynamics` alongside closed-loop `dynamics` so controlled feedback
exports preserve the admissible input channels the controller was derived
from. v3 adds self-contained viewer-facing verification payloads:
`regionGeometry` scalar-field grids and boundary polylines so TypeScript can
render safe/unsafe/initial/domain regions without evaluating symbolic
inequalities, plus controlled trajectories with time-aligned candidate value
and flow-derivative series. Verification problems also carry sampled
`proofStatuses` for obligation-region grids. The engine still **proposes and
organizes; external tools dispose**: nothing in the IR stores proof results.

## Design decisions

1. **Schema bump, no migration.** `SCHEMA_VERSION` is now
   `verification-problem/v3`. Artifacts are deterministic and regenerable
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
   Viewer export additionally validates that every `regionGeometry`
   projection/state-axis mapping is internally consistent with the problem's
   variables and declared state-axis mapping.
8. **Viewer geometry is sampled metadata, not verification.** `regionGeometry`
   entries carry a named projection, two IR plane variables, explicit
   IR-variable-to-state-axis mappings, the sampled scalar field of the defining
   region expression, sampled boundary polylines from that grid, the original
   level/convention, and `rigor="measured"`. This is a render aid only; it does
   not prove region containment or invariance.
9. **Measured certificate diagnostics are separate from obligations.**
   Each self-contained verification trajectory exports additional scalar
   `series` entries for candidate value (`B(x(t))` or `V(x(t))`) and flow
   derivative (`dB/dt` / `dV/dt` evaluated from the verification dynamics at
   trajectory samples). The join table lives in the trajectory
   `certificateSeries`, with `problemId`, `candidateId`, `obligationIds`,
   comparison baselines, and `rigor="measured"`.
   Verification-problem JSON exports `proofStatuses` records, one per sampled
   obligation surface in the current concrete slice. Each record links
   `obligationId`, `candidateId`, `regionId`, the sampled evaluation source
   such as `regionGeometry:<regionId>`, sample count, worst sampled value, and
   a machine-readable status (`measured-holds`, `measured-violated`, or
   `external-required`). These records are measured evidence only and keep
   `externalStatus="external-required"` distinct from the sampled status.
10. **Deferred (out of v3):** richer
   assumption languages beyond scalar expression comparisons, boundary
   topology guarantees, real external backends, and any proof-result storage.
11. **Adapter diagnostics are outcomes, not proofs.** Verification adapters
   report normalized diagnostics through `VerificationDiagnostic` with
   statuses such as `not-attempted`, `externally-required`, `unsupported`,
   and `malformed`. The inspection stub writes these diagnostics to a
   machine-readable outcome artifact; it still cannot record success,
   discharge, proof, or certification.
12. **Adapter capability checks are explicit.** `engine.verification`
   classifies each obligation into a target family such as
   `continuous-lyapunov`, `discrete-barrier`, or `obligation-only`, and records
   structural shape features such as region scoping, excluded points,
   assumptions, strict comparisons, and nonzero right-hand sides. Adapters
   advertise discharge capabilities separately from inspection support,
   including supported target families, dynamics kinds, candidate kinds, and
   obligation shape features. Diagnostics include the target classification and
   a `capabilityAssessment` explaining unsupported facets. The inspection stub
   advertises no discharge capabilities. Ambiguous or incomplete target shapes,
   currently mixed-candidate ownership and candidate obligations without
   encoded dynamics, are classified as malformed adapter targets rather than as
   unsupported proof attempts.
13. **Target-specific prechecks are structural only.** The SOS-polynomial
   requirement checker verifies that certificate targets have polynomial
   dynamics, regions, candidate expressions, and obligation expressions before
   a future SOS-style adapter could attempt them. It emits only unsupported or
   malformed diagnostics; it records no success, proof, or certificate result.
   When a controlled export includes `openLoopDynamics`, the checker validates
   that preserved model too and treats declared control/disturbance channels as
   known input symbols.

## Files

- `engine/verification/ir.py` — `DynamicsSpec`, `InputSpec`,
  `AssumptionSpec`, `CandidateSpec`, `RegionGeometrySpec`, extended
  `VerificationProblem`, schema bump.
- `engine/verification/diagnostics.py` — typed adapter diagnostics with a
  small status/severity vocabulary for inspection and future backend
  integrations.
- `engine/verification/capabilities.py` — adapter capability declarations and
  deterministic obligation-target classification.
- `engine/verification/target_requirements.py` — target-specific structural
  requirement diagnostics, currently an SOS-polynomial precheck.
- `engine/verification/region_geometry.py` — deterministic scalar-field grid
  sampling and boundary-polyline extraction for region render metadata.
- `engine/verification/measured.py` — measured candidate series and sampled
  proof-status records for viewer diagnostics, with no proof discharge.
- `engine/export/verification_contract.py` — manifest/verification cross-link
  validation used before writing viewer verification data, including sampled
  proof-status state-axis mappings.
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
  machine-readable inspection outcome JSON. The backend export script writes a
  deterministic inspection artifact index alongside those files, with a reusable
  validator for downstream discovery tools.
- `tests/test_verification_ir.py`, `tests/test_inspection_adapter.py`.

## Viewer export contract checks

Viewer-facing verification data is guarded by backend-owned contract checks in
`engine/export/verification_contract.py` before JSON is written. These checks
make the TypeScript renderer's inputs coherent; they are not proof,
certification, validated numerics, or obligation discharge.

- **Index validation** checks the catalog version, problem entries, data paths,
  and summary count shape.
- **Trajectory validation** checks time/state alignment, state names, per-series
  time alignment, and `certificateSeries` references into the exported numeric
  `series`.
- **Problem-payload validation** checks internal links among declared variables,
  regions, region geometry, obligations, candidates, `proofStatuses`,
  trajectory state names, and certificate comparison baselines.
- **Round-trip export validation** checks the index against the referenced
  problem payloads: ids, names, schema versions, summary counts, and embedded
  trajectories must agree.

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
   raise. Viewer verification export also rejects region geometry or
   proof-status records whose variables and state-axis mappings do not match the
   problem.
7. **Determinism (measured).** Serialization remains bit-identical across
   runs; the inspection report renders the new sections deterministically.
8. **Viewer-region geometry (measured).** Region geometry grids sample the
   symbolic region expression exactly at deterministic grid points and carry
   `rigor="measured"` plus the original level/convention. They are render
   metadata, not certificates. Boundary polylines are extracted from those
   measured grids and carry the same rigor.
9. **Measured certificate diagnostics (measured).** Self-contained
   verification trajectories export candidate value and flow-derivative series
   aligned to their time grids, with `certificateSeries` linking each series
   back to the verification problem, candidate, obligations, and comparison
   baselines. Viewer verification problems export sampled region-grid
   `proofStatuses` for each obligation, all with `rigor="measured"` and
   `externalStatus="external-required"`.
10. **Diagnostic honesty (proven by construction).** Inspection outcomes use
   only non-success statuses (`not-attempted`, `externally-required`,
   `unsupported`, `malformed`) and every obligation receives an
   `externally-required` diagnostic until a real backend exists. Each such
   diagnostic carries its obligation target, required discharge capability,
   structural shape features, and a facet-level capability assessment. The
   inspection stub also emits target-level `unsupported` diagnostics for
   well-formed obligations it cannot discharge and `malformed` diagnostics for
   ambiguous or incomplete target shapes.
11. **SOS-polynomial requirements (proven on examples).** A polynomial damped
   oscillator Lyapunov problem and a controlled-discrete polynomial Lyapunov
   export emit no requirement failures, while the trigonometric pendulum
   barrier and a non-polynomial open-loop controlled export emit `unsupported`
   diagnostics for non-polynomial dynamics/candidate expressions. Generic
   non-certificate claims are rejected as unsupported targets.

## Verification commands

```sh
pytest tests/test_verification_ir.py tests/test_inspection_adapter.py tests/test_pendulum_workflow.py -q
pytest -q
python -m scripts.export_verification_problems
```

Run `python -m scripts.generate_manifest` and
`python -m scripts.generate_verification_problems` when checking the viewer
contract shape. Use `--generated-dir` and `--viewer-dir` to redirect
verification artifacts into temporary directories for smoke checks. Generated
files remain ignored.

## Out of scope

Everything listed under "Deferred" above, plus any frontend surface.

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
Updated again on 2026-06-13: IR v3 adds measured `regionGeometry` scalar-field
grids for viewer rendering.
Updated again on 2026-06-13: `regionGeometry` now includes sampled boundary
polylines extracted from the scalar grids for direct viewer contour rendering.
Updated again on 2026-06-13: viewer verification generation validates
region-geometry projection/state-axis mappings before writing JSON.
Updated again on 2026-06-13: added an SOS-polynomial structural requirement
checker for future certificate adapters. It emits only unsupported/malformed
diagnostics and does not attempt proof discharge.
Updated again on 2026-06-13: the SOS-polynomial checker now validates preserved
open-loop controlled dynamics and treats declared control/disturbance inputs as
known symbols.
Updated again on 2026-06-13: added measured candidate trajectory series and
measured region-grid `proofStatuses` for viewer verification exports. These
records remain sampled evidence and do not change obligation rigor from
`external-required`.
Updated 2026-06-14: adapter capability diagnostics now include structural
obligation shape features and facet-level support checks for target family,
dynamics kind, candidate kind, and obligation shape. The inspection stub still
records no proof discharge.
