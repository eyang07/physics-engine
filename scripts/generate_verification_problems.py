"""Generate verification-problem IR for the viewer (backend-only data).

Writes, per problem, a viewer-shaped payload (the verification-problem IR plus a
self-contained controlled trajectory) and the backend-agnostic IR artifact on
its own (the same serialization the inspection adapter emits, without the viewer
trajectory) so the viewer can offer it for external discharge, plus a small index
the Verification domain lists. Like the trajectory generators, output is
deterministic and regenerable; nothing here is committed and nothing claims proof
discharge.

The IR carries candidate certificates and proof obligations only — every
obligation is labeled ``external-required`` and the viewer renders that honesty
verbatim. This script consumes the public verification API
(``VerificationProblem.to_dict`` / ``write_json``) and reuses the problem
definitions from ``scripts.export_verification_problems``; it does not re-derive
any physics.
"""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from pathlib import Path

import numpy as np

from engine.export import (
    validate_viewer_verification_export,
    validate_viewer_verification_problems,
    validate_viewer_verification_trajectory,
)
from engine.verification import VerificationProblem, certificate_series_for_trajectory
from scripts.export_verification_problems import (
    ViewerVerificationExample,
    viewer_verification_examples,
)

DEFAULT_GENERATED_DIR = Path("data/generated/verification")
DEFAULT_VIEWER_DIR = Path("viewer/public/data/verification")
INDEX_VERSION = 1


def _problem_summary(payload: dict, data_path: str, ir_path: str) -> dict:
    """A thin catalog entry the viewer lists; the detail lives in the IR file."""

    metadata = payload.get("metadata") or {}
    return {
        "id": payload["id"],
        "name": payload["name"],
        "model": metadata.get("verificationModel"),
        "status": metadata.get("status", "candidate"),
        "schemaVersion": payload.get("schemaVersion"),
        "dataPath": data_path,
        "irPath": ir_path,
        "counts": {
            "regions": len(payload.get("regions", [])),
            "obligations": len(payload.get("obligations", [])),
            "candidates": len(payload.get("candidates", [])),
        },
    }


def _controlled_trajectory_payload(
    problem: VerificationProblem,
    example: ViewerVerificationExample,
) -> dict:
    """The controlled path plus its candidate-certificate series.

    The viewer animates this self-contained trajectory in the Verification world;
    the certificate series are evaluated along the very system the obligations are
    derived for, so the path and the barrier describe one system.
    """

    time, states = example.trajectory_factory()
    state_names = [variable.name for variable in problem.variables]
    diagnostics = certificate_series_for_trajectory(
        problem,
        time=time,
        states=states,
        state_names=state_names,
        variable_to_state_axis=example.variable_to_state_axis,
    )
    return {
        "time": [float(value) for value in time],
        "stateNames": state_names,
        "states": np.asarray(states, dtype=float).tolist(),
        "series": {name: list(values) for name, values in diagnostics.series.items()},
        "certificateSeries": list(diagnostics.metadata),
    }


def write_verification_problems(
    *,
    generated_dir: Path = DEFAULT_GENERATED_DIR,
    viewer_dir: Path = DEFAULT_VIEWER_DIR,
) -> list[str]:
    """Serialize every viewer verification problem and its index. Returns ids."""

    examples = viewer_verification_examples()
    problems: list[VerificationProblem] = [
        example.problem_factory() for example in examples
    ]
    validate_viewer_verification_problems(problems)
    generated_dir.mkdir(parents=True, exist_ok=True)
    viewer_dir.mkdir(parents=True, exist_ok=True)

    summaries: list[dict] = []
    records: list[tuple[str, dict]] = []
    payloads_by_data_path: dict[str, dict] = {}
    ir_payloads_by_ir_path: dict[str, dict] = {}
    for example, problem in zip(examples, problems, strict=True):
        # The backend-agnostic IR is the problem serialization without the
        # viewer-only trajectory; the viewer payload is that IR plus trajectory.
        ir_payload = problem.to_dict()
        payload = {
            **ir_payload,
            "trajectory": _controlled_trajectory_payload(problem, example),
        }
        validate_viewer_verification_trajectory(
            payload["trajectory"],
            problem_id=problem.id,
        )
        filename = f"{payload['id']}.json"
        data_path = f"/data/verification/{filename}"
        ir_filename = f"{payload['id']}.ir.json"
        ir_path = f"/data/verification/{ir_filename}"
        payloads_by_data_path[data_path] = payload
        ir_payloads_by_ir_path[ir_path] = ir_payload
        records.append((filename, payload))
        records.append((ir_filename, ir_payload))
        summaries.append(_problem_summary(payload, data_path, ir_path))

    index_payload = {"version": INDEX_VERSION, "problems": summaries}
    validate_viewer_verification_export(
        index_payload,
        payloads_by_data_path,
        version=INDEX_VERSION,
        ir_payloads_by_ir_path=ir_payloads_by_ir_path,
    )
    for filename, payload in records:
        text = json.dumps(payload, indent=2) + "\n"
        (generated_dir / filename).write_text(text, encoding="utf-8")
        (viewer_dir / filename).write_text(text, encoding="utf-8")
    index_text = json.dumps(index_payload, indent=2) + "\n"
    (generated_dir / "index.json").write_text(index_text, encoding="utf-8")
    (viewer_dir / "index.json").write_text(index_text, encoding="utf-8")
    return [summary["id"] for summary in summaries]


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--generated-dir",
        type=Path,
        default=DEFAULT_GENERATED_DIR,
        help="directory for ignored backend-generated verification files",
    )
    parser.add_argument(
        "--viewer-dir",
        type=Path,
        default=DEFAULT_VIEWER_DIR,
        help="directory for ignored viewer verification files",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> None:
    args = parse_args(argv)

    ids = write_verification_problems(
        generated_dir=args.generated_dir,
        viewer_dir=args.viewer_dir,
    )
    print(f"wrote {len(ids)} verification problem(s): {', '.join(ids)}")
    print(f"generated dir: {args.generated_dir}")
    print(f"viewer dir: {args.viewer_dir}")


if __name__ == "__main__":
    main()
