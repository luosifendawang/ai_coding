#!/usr/bin/env python3
"""Run gitplus release readiness checks."""

from __future__ import annotations

import argparse
from pathlib import Path

from gitplus.release.readiness import ReleaseReadinessChecker
from gitplus.release.report import ReleaseReportRenderer


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("artifacts/release-readiness.md"))
    args = parser.parse_args()
    readiness = ReleaseReadinessChecker(Path.cwd()).run()
    text = ReleaseReportRenderer().render(readiness)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(text, encoding="utf-8")
    print(text)
    return 0 if readiness.ready else 1


if __name__ == "__main__":
    raise SystemExit(main())
