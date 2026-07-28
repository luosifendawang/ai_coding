#!/usr/bin/env python3
"""Create a repeatable GitPulse demo repository."""

from __future__ import annotations

import argparse
from pathlib import Path
import subprocess


def run(repo: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True, text=True)


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("/tmp/gitpulse-demo"))
    args = parser.parse_args()
    repo = args.output.resolve()
    repo.mkdir(parents=True, exist_ok=True)
    (repo / ".gitpulse-demo").write_text("demo\n", encoding="utf-8")
    if not (repo / ".git").exists():
        run(repo, "init")
    run(repo, "config", "user.name", "GitPulse Demo")
    run(repo, "config", "user.email", "demo@example.test")
    write(repo / "src/usb/device.py", "class UsbDevice:\n    def close(self):\n        return True\n")
    write(repo / "tests/test_device.py", "def test_close():\n    assert True\n")
    write(repo / "docs/usb.md", "# USB Demo\n")
    write(repo / "config/demo-secret.py", 'API_KEY = "sk-testexample1234567890abcdef"\n')
    write(repo / "generated/large.txt", "demo\n" * 2000)
    run(repo, "add", "src", "tests", "docs")
    run(repo, "commit", "--allow-empty", "-m", "fix(usb): 修复设备断开资源释放")
    write(repo / "src/logging.py", "def format_log(value):\n    return f'[demo] {value}'\n")
    run(repo, "add", "src/logging.py")
    print(repo)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
