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

    @classmethod
    def from_arrays(
        cls,
        time: Sequence[float],
        states: Sequence[Sequence[float]],
        state_names: Sequence[str],
        metadata: dict[str, Any] | None = None,
    ) -> "Trajectory":
        return cls(
            np.asarray(time, dtype=float),
            np.asarray(states, dtype=float),
            tuple(state_names),
            metadata,
        )

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "time": self.time.tolist(),
            "state_names": list(self.state_names),
            "states": self.states.tolist(),
        }
        if self.metadata is not None:
            payload["metadata"] = self.metadata
        return payload

    def write_json(self, path: str | Path) -> None:
        output_path = Path(path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")
