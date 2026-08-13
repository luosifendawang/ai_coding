#!/usr/bin/env python3
"""Optional PyInstaller entry point."""

from __future__ import annotations

import shutil
import subprocess


def main() -> int:
    if not shutil.which("pyinstaller"):
        print("PyInstaller 未安装。请先安装可选依赖：pip install .[standalone]")
        return 1
    return subprocess.run(["pyinstaller", "-n", "gitplus", "-F", "src/gitplus/cli.py"], check=False).returncode


if __name__ == "__main__":
    raise SystemExit(main())
