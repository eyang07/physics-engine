from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from engine.export import Trajectory


def assert_metadata_keys(
    trajectory: Trajectory,
    expected: set[str],
) -> Mapping[str, Any]:
    assert trajectory.metadata is not None
    assert set(trajectory.metadata) == expected
    return trajectory.metadata


def assert_renderer_hint_keys(
    metadata: Mapping[str, Any],
    expected: set[str],
) -> Mapping[str, Any]:
    hints = metadata["rendererHints"]
    assert isinstance(hints, Mapping)
    assert set(hints) == expected
    return hints


def assert_invariant_residual_names(
    metadata: Mapping[str, Any],
    expected: Sequence[str],
) -> None:
    assert [record["name"] for record in metadata["invariantResiduals"]] == (
        list(expected)
    )


def assert_lyapunov_diagnostic_references_series(
    trajectory: Trajectory,
) -> Mapping[str, Any]:
    assert trajectory.metadata is not None
    assert trajectory.series is not None
    lyapunov = trajectory.metadata["diagnostics"]["lyapunov"]
    assert set(lyapunov) == {
        "kind",
        "method",
        "series",
        "localGrowthSeries",
        "initialTangent",
        "finalTangent",
        "finalEstimate",
        "sampleCount",
        "timeWindow",
    }
    assert lyapunov["kind"] == "finite-time-largest"
    assert lyapunov["method"] == "sampled-variational-jacobian"
    assert lyapunov["series"] in trajectory.series
    assert lyapunov["localGrowthSeries"] in trajectory.series
    assert lyapunov["sampleCount"] == len(trajectory.time)
    assert lyapunov["timeWindow"] == [float(trajectory.time[0]), float(trajectory.time[-1])]
    assert len(trajectory.series[lyapunov["series"]]) == len(trajectory.time)
    assert len(trajectory.series[lyapunov["localGrowthSeries"]]) == len(
        trajectory.time
    )
    return lyapunov


def assert_embedded_certificate_trajectory(
    trajectory: Mapping[str, Any],
    *,
    state_names: Sequence[str],
    series_names: set[str],
    certificate_kinds: set[str],
) -> None:
    assert trajectory["stateNames"] == list(state_names)
    assert len(trajectory["time"]) == len(trajectory["states"]) > 0
    assert set(trajectory["series"]) == series_names
    assert {record["kind"] for record in trajectory["certificateSeries"]} == (
        certificate_kinds
    )
    for series_name in series_names:
        assert len(trajectory["series"][series_name]) == len(trajectory["time"])
