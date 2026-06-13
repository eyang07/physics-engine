from __future__ import annotations

import numpy as np
import pytest
import sympy as sp

from engine.dynamics import SafetySpecification, SublevelSet
from engine.numerics import integrate_fixed_step, integrate_with_events


def test_integrate_with_events_locates_zero_crossing() -> None:
    # Harmonic oscillator x'' = -x with x(0)=1, v(0)=0: x = cos t, v = -sin t.
    # x falls through zero at t = pi/2; the located crossing must be sharp.
    def rhs(t: float, y: np.ndarray) -> np.ndarray:
        return np.array([y[1], -y[0]])

    def x_zero(t: float, y: np.ndarray) -> float:
        return y[0]

    result = integrate_with_events(
        rhs, [1.0, 0.0], (0.0, 3.0), events=[x_zero], directions=[-1.0]
    )

    assert result.event_times[0].shape == (1,)
    assert result.event_times[0][0] == pytest.approx(np.pi / 2, abs=1e-6)
    assert result.event_states[0][0, 0] == pytest.approx(0.0, abs=1e-6)
    # The rising crossing is filtered out by the direction restriction.
    assert result.event_states[0][0, 1] == pytest.approx(-1.0, abs=1e-6)


def test_terminal_event_stops_integration() -> None:
    def rhs(t: float, y: np.ndarray) -> np.ndarray:
        return np.array([1.0])

    def threshold(t: float, y: np.ndarray) -> float:
        return y[0] - 0.5

    result = integrate_with_events(
        rhs, [0.0], (0.0, 10.0), events=[threshold], terminal=[True]
    )

    assert result.event_times[0][0] == pytest.approx(0.5, abs=1e-6)
    assert result.time[-1] == pytest.approx(0.5, abs=1e-6)


def test_integrate_with_events_validation() -> None:
    def rhs(t: float, y: np.ndarray) -> np.ndarray:
        return np.array([1.0])

    with pytest.raises(ValueError, match="at least one event"):
        integrate_with_events(rhs, [0.0], (0.0, 1.0), events=[])
    with pytest.raises(ValueError, match="t1 > t0"):
        integrate_with_events(rhs, [0.0], (1.0, 1.0), events=[lambda t, y: y[0]])
    with pytest.raises(ValueError, match="match the event count"):
        integrate_with_events(
            rhs, [0.0], (0.0, 1.0), events=[lambda t, y: y[0]], directions=[1.0, -1.0]
        )


def _drift_spec(threshold: float) -> SafetySpecification:
    # Unsafe set {x >= threshold} as a sublevel set {-x <= -threshold}.
    x = sp.Symbol("x", real=True)
    return SafetySpecification(
        state=(x,),
        safe_set=SublevelSet(state=(x,), expression=x, level=10.0, name="box"),
        unsafe_sets=(
            SublevelSet(state=(x,), expression=-x, level=-threshold, name="barrier"),
        ),
    )


def _unit_drift(t: float, y: np.ndarray) -> np.ndarray:
    return np.array([1.0])


def test_event_entry_time_is_sharper_than_grid() -> None:
    # dx/dt = 1, x(0) = 0, so x(t) = t and the unsafe threshold 0.53 is
    # reached at t = 0.53 exactly. Grid sampling at dt = 0.1 cannot see this.
    spec = _drift_spec(0.53)

    report = spec.event_entry_report(_unit_drift, [0.0], (0.0, 1.0))
    entry = report.unsafe_sets[0]

    assert report.rigor == "measured"
    assert report.entered_any
    assert entry.entered and not entry.started_inside
    assert entry.first_entry_time == pytest.approx(0.53, abs=1e-6)
    assert entry.entry_state[0] == pytest.approx(0.53, abs=1e-6)

    # The sampled report snaps the entry to the next grid point (t = 0.6).
    times, states = integrate_fixed_step(_unit_drift, [0.0], (0.0, 1.0), 0.1)
    grid = spec.trajectory_report(times, states)
    assert grid.unsafe_sets[0].first_entry_time == pytest.approx(0.6)
    assert entry.first_entry_time < grid.unsafe_sets[0].first_entry_time


def test_event_entry_report_flags_initial_membership() -> None:
    # Starting at x = 0 is already inside {x >= -0.5}; there is no crossing to
    # root-find, so the report attributes entry to the initial time/state.
    spec = _drift_spec(-0.5)

    report = spec.event_entry_report(_unit_drift, [0.0], (0.0, 1.0))
    entry = report.unsafe_sets[0]

    assert entry.entered and entry.started_inside
    assert entry.first_entry_time == pytest.approx(0.0)
    assert entry.entry_state[0] == pytest.approx(0.0)


def test_event_entry_report_reports_no_entry() -> None:
    # Drifting up toward +inf never reaches the threshold below the start.
    spec = _drift_spec(5.0)

    report = spec.event_entry_report(_unit_drift, [0.0], (0.0, 1.0))
    entry = report.unsafe_sets[0]

    assert not report.entered_any
    assert not entry.entered and not entry.started_inside
    assert entry.first_entry_time is None
    assert entry.entry_state is None


def test_event_entry_report_requires_unsafe_sets() -> None:
    x = sp.Symbol("x", real=True)
    spec = SafetySpecification(
        state=(x,),
        safe_set=SublevelSet(state=(x,), expression=x, level=10.0, name="box"),
    )
    with pytest.raises(ValueError, match="no unsafe sets"):
        spec.event_entry_report(_unit_drift, [0.0], (0.0, 1.0))
