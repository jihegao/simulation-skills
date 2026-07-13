"""Provider contract utility entrypoint."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .registry import V01SimulationContractRegistry


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("document", type=Path)
    args = parser.parse_args(argv)
    value = json.loads(args.document.read_text(encoding="utf-8"))
    V01SimulationContractRegistry().validate_object(value)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
