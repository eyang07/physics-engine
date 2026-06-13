"""Generate verification-problem IR for the viewer (backend-only data).

Writes the same backend-agnostic verification-problem IR the inspection adapter
emits into the viewer's data directory, plus a small index the Verification
domain lists. Like the trajectory generators, output is deterministic and
regenerable; nothing here is committed and nothing claims proof discharge.

The IR carries candidate certificates and proof obligations only — every
obligation is labeled ``external-required`` and the viewer renders that honesty
verbatim. This script consumes the public verification API
(``VerificationProblem.to_dict`` / ``write_json``) and reuses the problem
definitions from ``scripts.export_verification_problems``; it does not re-derive
any physics.
"""

from __future__ import annotations

import json
from pathlib import Path

from engine.verification import VerificationProblem
from scripts.export_verification_problems import upright_pendulum_problem

DEFAULT_GENERATED_DIR = Path("data/generated/verification")
DEFAULT_VIEWER_DIR = Path("viewer/public/data/verification")
INDEX_VERSION = 1


def _problem_summary(payload: dict, data_path: str) -> dict:
    """A thin catalog entry the viewer lists; the detail lives in the IR file."""

    metadata = payload.get("metadata") or {}
    return {
        "id": payload["id"],
        "name": payload["name"],
        "system": metadata.get("system"),
        "status": metadata.get("status", "candidate"),
        "schemaVersion": payload.get("schemaVersion"),
        "dataPath": data_path,
        "counts": {
            "regions": len(payload.get("regions", [])),
            "obligations": len(payload.get("obligations", [])),
            "candidates": len(payload.get("candidates", [])),
        },
    }


def write_verification_problems(
    *,
    generated_dir: Path = DEFAULT_GENERATED_DIR,
    viewer_dir: Path = DEFAULT_VIEWER_DIR,
) -> list[str]:
    """Serialize every viewer verification problem and its index. Returns ids."""

    problems: list[VerificationProblem] = [upright_pendulum_problem()]
    generated_dir.mkdir(parents=True, exist_ok=True)
    viewer_dir.mkdir(parents=True, exist_ok=True)

    summaries: list[dict] = []
    for problem in problems:
        payload = problem.to_dict()
        filename = f"{payload['id']}.json"
        problem.write_json(generated_dir / filename)
        problem.write_json(viewer_dir / filename)
        summaries.append(_problem_summary(payload, f"/data/verification/{filename}"))

    index_text = json.dumps({"version": INDEX_VERSION, "problems": summaries}, indent=2) + "\n"
    (generated_dir / "index.json").write_text(index_text, encoding="utf-8")
    (viewer_dir / "index.json").write_text(index_text, encoding="utf-8")
    return [summary["id"] for summary in summaries]


def main() -> None:
    ids = write_verification_problems()
    print(f"Wrote {len(ids)} verification problem(s) and index.json: {', '.join(ids)}")


if __name__ == "__main__":
    main()
