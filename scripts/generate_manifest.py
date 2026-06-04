from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

from engine.export.manifest import write_manifest
from scripts.example_specs import LENSES, SPECS


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate the shared example manifest.")
    parser.add_argument("--output", type=Path, default=Path("data/generated/manifest.json"))
    parser.add_argument("--viewer-output", type=Path, default=Path("viewer/public/data/manifest.json"))
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> None:
    args = parse_args(argv)
    write_manifest(SPECS, args.output, args.viewer_output, lenses=LENSES)
    print(f"Wrote manifest with {len(SPECS)} systems to {args.output}")
    print(f"Wrote viewer copy to {args.viewer_output}")


if __name__ == "__main__":
    main()
