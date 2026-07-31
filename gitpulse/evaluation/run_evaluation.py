#!/usr/bin/env python3
"""Summarize evaluation sample files."""

from __future__ import annotations

import json
from pathlib import Path


def count(path: Path) -> int:
    return sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip())


def main() -> int:
    root = Path(__file__).parent
    files = sorted(root.glob("*_cases.jsonl"))
    report = {"files": {path.name: count(path) for path in files}}
    report["total_samples"] = sum(report["files"].values())
    output = Path("artifacts/evaluation-report.md")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("# Evaluation Report\n\n```json\n" + json.dumps(report, ensure_ascii=False, indent=2) + "\n```\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
