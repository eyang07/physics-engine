from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any, Sequence

import numpy as np


@dataclass(frozen=True)
class Trajectory:
    time: np.ndarray
    states: np.ndarray
    state_names: tuple[str, ...]
    metadata: dict[str, Any] | None = None
    # Named scalar quantities sampled along the trajectory (energy, conserved
    # quantities, momenta). The viewer displays these directly instead of
    # recomputing physics, so the Python/TS boundary stays clean.
    series: dict[str, Sequence[float]] | None = None

    @classmethod
    def from_arrays(
        cls,
        time: Sequence[float],
        states: Sequence[Sequence[float]],
        state_names: Sequence[str],
        metadata: dict[str, Any] | None = None,
        series: dict[str, Sequence[float]] | None = None,
    ) -> "Trajectory":
        return cls(
            np.asarray(time, dtype=float),
            np.asarray(states, dtype=float),
            tuple(state_names),
            metadata,
            series,
        )

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "time": self.time.tolist(),
            "state_names": list(self.state_names),
            "states": self.states.tolist(),
        }
        if self.metadata is not None:
            payload["metadata"] = self.metadata
        if self.series is not None:
            payload["series"] = {
                name: np.asarray(values, dtype=float).tolist()
                for name, values in self.series.items()
            }
        return payload

    def write_json(self, path: str | Path) -> None:
        output_path = Path(path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")
