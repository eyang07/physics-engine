from dataclasses import replace
from pathlib import Path

import pytest

from engine.export import Trajectory
from engine.export.manifest import ParameterVariant
from scripts.example_specs import PENDULUM
from scripts.generation import (
    initial_state_defaults,
    physical_parameter_defaults,
    variant_filename,
    write_parameter_variant_trajectories,
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


def test_variant_filename_requires_viewer_data_path() -> None:
    assert variant_filename("/data/example_variant.json", system_name="Example") == (
        "example_variant.json"
    )
    with pytest.raises(ValueError, match="Example variant path"):
        variant_filename("example_variant.json", system_name="Example")


def test_write_parameter_variant_trajectories_skips_default_variant(tmp_path: Path) -> None:
    written: list[tuple[str, Path, Path | None]] = []

    def write_variant(
        variant: ParameterVariant,
        output: Path,
        viewer_output: Path | None,
    ) -> Trajectory:
        written.append((variant.id, output, viewer_output))
        trajectory = Trajectory.from_arrays(
            time=[0.0, 0.1],
            states=[[0.0], [0.1]],
            state_names=["x"],
        )
        return write_trajectory_outputs(trajectory, output, viewer_output)

    spec = replace(
        PENDULUM,
        data_path="/data/default.json",
        variants=(
            ParameterVariant(
                id="default",
                label="default",
                parameters={},
                data_path="/data/default.json",
            ),
            ParameterVariant(
                id="other",
                label="other",
                parameters={},
                data_path="/data/other.json",
            ),
        ),
    )

    trajectories = write_parameter_variant_trajectories(
        spec,
        tmp_path / "data",
        write_variant=write_variant,
        viewer_output_dir=tmp_path / "viewer",
        system_name="Example",
    )

    assert len(trajectories) == 1
    assert written == [
        (
            "other",
            tmp_path / "data" / "other.json",
            tmp_path / "viewer" / "other.json",
        )
    ]
    assert (tmp_path / "data" / "other.json").exists()
    assert (tmp_path / "viewer" / "other.json").exists()
