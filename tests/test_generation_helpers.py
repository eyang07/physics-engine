from pathlib import Path

from engine.export import Trajectory
from scripts.example_specs import PENDULUM
from scripts.generation import (
    initial_state_defaults,
    physical_parameter_defaults,
    write_trajectory_outputs,
)


def test_physical_parameter_defaults_come_from_spec() -> None:
    assert physical_parameter_defaults(PENDULUM) == {
        "m": 1.0,
        "ell": 1.0,
        "g": 9.81,
    }


def test_initial_state_defaults_follow_state_order() -> None:
    assert initial_state_defaults(PENDULUM) == [0.85, 0.0]


def test_write_trajectory_outputs_writes_primary_and_viewer_copies(tmp_path: Path) -> None:
    trajectory = Trajectory.from_arrays(
        time=[0.0, 0.1],
        states=[[0.0, 1.0], [0.1, 0.9]],
        state_names=["x", "x_dot"],
    )
    output = tmp_path / "data" / "example.json"
    viewer_output = tmp_path / "viewer" / "example.json"

    returned = write_trajectory_outputs(trajectory, output, viewer_output)

    assert returned is trajectory
    assert output.read_text(encoding="utf-8") == viewer_output.read_text(encoding="utf-8")
