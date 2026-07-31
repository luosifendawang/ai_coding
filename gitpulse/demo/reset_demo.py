#!/usr/bin/env python3
"""Reset a GitPulse demo repository."""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--path", type=Path, required=True)
    parser.add_argument("--yes", action="store_true")
    args = parser.parse_args()
    path = args.path.resolve()
    if not (path / ".gitpulse-demo").exists():
        print("拒绝重置：目标目录缺少 .gitpulse-demo 标记。")
        return 2
    if not args.yes:
        print(f"将删除 Demo 目录：{path}\n请添加 --yes 确认。")
        return 1
    shutil.rmtree(path)
    print(f"Demo 已重置：{path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
