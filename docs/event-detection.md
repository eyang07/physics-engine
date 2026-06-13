# Event-Based Unsafe-Set Detection — Design Spec (v0)

Sharpens the unsafe-set entry times that `SafetySpecification` reports.
Status: **implemented** (see Verification record at the bottom).

## Goal

Replace grid-snapped unsafe-set entry detection with event root-finding.
`SafetySpecification.trajectory_report` reports `first_entry_time` as the
timestamp of the first *sample* that lands inside an unsafe set, so its
resolution is the sample spacing. For a witness that the trajectory reaches an
unsafe set, the entry time should be located by the integrator's root-finder
instead, sharp to integration tolerance. Backend-only: no manifest, gallery,
or viewer change.

## Design decisions

1. **A generic event-integration primitive lives in numerics.**
   `integrate_with_events` (`engine/numerics/integrators.py`) wraps SciPy's
   `solve_ivp` events API: it integrates adaptively with DOP853 and returns,
   per event function, every located zero crossing in time order
   (`EventIntegrationResult`). `directions` restrict crossings to rising
   (`+1`), falling (`-1`), or both (`0`); `terminal` flags stop integration at
   first crossing. This is a reusable building block, not safety-specific.
2. **The unsafe margin is the event function.** An unsafe set is a sublevel
   set `{g(x) <= level}` with signed margin `level - g(x)`, nonnegative
   inside. Entering it is the margin crossing zero upward, so
   `SafetySpecification.event_entry_report` hands each unsafe set's margin to
   the integrator with `direction = +1` and reads off the first crossing.
3. **Membership at `t0` is checked directly, not root-found.** The root-finder
   only sees sign changes during integration; a trajectory that *starts*
   inside an unsafe set never crosses the margin. That case is detected by
   evaluating the margin at the initial state and, when already inside,
   reporting entry at the initial time/state with `started_inside=True`. This
   keeps the method honest about the one case events cannot witness.
4. **Rigor is unchanged: still measured.** A located entry is a genuine
   witness that the trajectory reaches the unsafe set; a clean run over one
   horizon from one initial state is evidence only. The report is labeled
   `rigor="measured"` and carries the standard measured-note. Sharper numbers
   are not validated numerics and prove nothing about other trajectories.
5. **The method takes a numeric RHS, not a system.** Like the integrators it
   builds on, `event_entry_report` accepts a plain `rhs(t, x)` callable plus
   initial state and `t_span`, so it composes with closed-loop reductions,
   lambdified dynamics, or any other numeric flow without coupling to a
   specific system type. The sampled `trajectory_report` is unchanged and
   remains the right tool for safe-margin minima across a whole trajectory.

## Files

- `engine/numerics/integrators.py` — `EventIntegrationResult`,
  `integrate_with_events`.
- `engine/numerics/__init__.py` — exports.
- `engine/dynamics/safety.py` — `UnsafeEntryEvent`, `EventEntryReport`,
  `SafetySpecification.event_entry_report`, `_scalar_evaluator`.
- `engine/dynamics/__init__.py` — exports.
- `tests/test_event_detection.py` — obligations below.

## Invariants / proof obligations (for this implementation)

1. **Sharp crossing (measured).** For the harmonic oscillator `x = cos t`, the
   falling zero crossing of `x` is located at `t = pi/2` to `1e-6`, and the
   direction restriction filters out the rising crossing.
2. **Terminal stop (measured).** A terminal event halts the integration at the
   first crossing; the returned final time equals the crossing time.
3. **Sharper than the grid (measured).** For `dx/dt = 1` the unsafe threshold
   `0.53` is located at `t = 0.53` to `1e-6`, strictly earlier than the
   `dt = 0.1` sampled report's snapped `t = 0.6`.
4. **Initial membership (measured).** A trajectory starting inside an unsafe
   set is reported as entering at `t0` with `started_inside=True`.
5. **No entry (measured).** A trajectory that never reaches the threshold
   reports `entered=False`, `first_entry_time=None`, `entry_state=None`.
6. **Validation (proven).** Empty event lists, non-increasing spans, and
   direction/terminal lengths that mismatch the event count raise; a
   specification with no unsafe sets raises in `event_entry_report`.

## Verification commands

```sh
pytest tests/test_event_detection.py tests/test_safety_certificates.py -q
pytest -q
```

No generator or viewer commands: nothing crosses the manifest boundary.

## Out of scope

Validated/guaranteed entry times (this is measured numerics); event-located
*safe*-margin minima or exit times; reachability over sets of initial states;
discrete-time event detection; manifest/export schema changes; frontend
surfaces.

## Verification record

Implemented and verified 2026-06-12: `pytest -q` green including
`tests/test_event_detection.py` (see `docs/BACKEND.md` baseline for the
current count).
