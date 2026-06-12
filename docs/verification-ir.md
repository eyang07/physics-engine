# Verification-Problem IR — Design Spec (v1)

Advances `docs/VISION.md` §10/§11 priority 3, building on the
safety/certificate layer (`docs/safety-certificates.md`). Status:
**implemented** (see Verification record at the bottom).

## Goal

Make exported verification problems genuinely dischargeable by an external
tool. IR v0 carried variables, parameters, regions, and obligations, but the
obligations arrived as pre-computed Lie-derivative expressions — the model
itself was lost, so no reachability, SOS, or deductive backend could actually
verify anything. v1 adds the dynamics, open control/disturbance channels, and
first-class candidate-certificate records. The engine still **proposes and
organizes; external tools dispose**: nothing in the IR stores proof results.

## Design decisions

1. **Schema bump, no migration.** `SCHEMA_VERSION` is now
   `verification-problem/v1`. Artifacts are deterministic and regenerable
   (nothing under `data/generated/` is committed), so v0 payloads are simply
   regenerated; the IR does not read or migrate old files.
2. **Dynamics are the model obligations were derived along.** `DynamicsSpec`
   records `kind="continuous"` (the discrete analogue is future work), the
   time variable, the state names in problem-variable order, and one
   `ExpressionSpec` per state derivative. The safety adapters encode the
   *closed-loop* system, because that is what the Lie derivatives were taken
   along; `dynamics` stays optional for obligation-only problems.
3. **Inputs are named, optionally interval-bounded channels.** `InputSpec`
   carries a role (`control` or `disturbance`) and optional lower/upper
   bounds. `dynamics_spec_from_controlled` encodes an open-loop
   `ControlledFirstOrderSystem` with its admissible `Box` bounds;
   `dynamics_spec_from_system` encodes a closed-loop `FirstOrderSystem` with
   no inputs.
4. **Candidates are first-class and link to their obligations.**
   `CandidateSpec` records kind (`lyapunov` or `barrier`), the certificate
   expression, the Lyapunov equilibrium, the candidate region, and the ids of
   the proof obligations that must be discharged before the candidate means
   anything. `status` is locked to `"candidate"` in `__post_init__`, the same
   construction-level honesty used for `ObligationSpec.rigor` and the stub
   adapter's report status.
5. **Cross-references are validated at the problem level.**
   `VerificationProblem` rejects dynamics whose state does not match the
   problem variables in order, candidate links to unknown obligation or
   region ids, duplicate candidate ids, and equilibria of the wrong
   dimension. Parameters now also collect free symbols from the dynamics RHS
   (excluding state and time) and the candidate expression.
6. **Deferred (out of v1):** discrete-time dynamics, domain-assumption
   records beyond regions, visualization hooks, real external backends, and
   any proof-result storage.

## Files

- `engine/verification/ir.py` — `DynamicsSpec`, `InputSpec`, `CandidateSpec`,
  extended `VerificationProblem`, schema bump.
- `engine/verification/system_codec.py` — `dynamics_spec_from_system`,
  `dynamics_spec_from_controlled`.
- `engine/verification/safety_adapter.py` — adapters now pass the system and
  candidate through; `verification_problem_from_obligations` accepts optional
  `system` and `candidate` keywords.
- `engine/verification/inspection_adapter.py` — renders Dynamics and
  Candidate certificates report sections.
- `tests/test_verification_ir.py`, `tests/test_inspection_adapter.py`.

## Invariants / proof obligations (for this implementation)

1. **Model fidelity (proven on examples).** The encoded RHS of the
   closed-loop pendulum and damped oscillator match the symbolic systems the
   obligations were derived along.
2. **Honest labeling (proven by construction).** `CandidateSpec` cannot be
   constructed with any status other than `"candidate"`; obligations keep
   `rigor="external-required"`; nothing in the IR can record a proof result.
3. **Referential integrity (proven).** Mismatched dynamics state, dangling
   candidate-obligation ids, and wrong-dimension equilibria raise.
4. **Determinism (measured).** Serialization remains bit-identical across
   runs; the inspection report renders the new sections deterministically.

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

Implemented and verified 2026-06-12: `pytest -q` green (see `docs/BACKEND.md`
baseline for the current count); the exported controlled-pendulum artifact
carries closed-loop dynamics, the barrier candidate, and its three linked
obligations under `verification-problem/v1`.
