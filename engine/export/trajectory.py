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

    @classmethod
    def from_arrays(
        cls,
        time: Sequence[float],
        states: Sequence[Sequence[float]],
        state_names: Sequence[str],
    ) -> "Trajectory":
        return cls(
            np.asarray(time, dtype=float),
            np.asarray(states, dtype=float),
            tuple(state_names),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "time": self.time.tolist(),
            "state_names": list(self.state_names),
            "states": self.states.tolist(),
        }

    def write_json(self, path: str | Path) -> None:
        output_path = Path(path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")

