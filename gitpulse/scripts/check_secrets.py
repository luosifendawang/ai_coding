"""Conservative release-time secret scan."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9]{20,}"),
    re.compile(r"(?i)(?:api_key|secret|password)\s*=\s*['\"][^'\"]{12,}['\"]"),
]
PLACEHOLDERS = [
    "GITPULSE_API_KEY",
    "GITPULSE_FEISHU_APP_SECRET",
    "example",
    "test",
]


def scan(paths: list[Path]) -> tuple[list[str], int]:
    findings: list[str] = []
    placeholders = 0
    for root in paths:
        if not root.exists():
            continue
        files = (
            [root]
            if root.is_file()
            else [path for path in root.rglob("*") if path.is_file()]
        )
        for path in files:
            if any(
                part in {".git", ".pytest_cache", "__pycache__", "dist"}
                for part in path.parts
            ):
                continue
            if path.suffix in {".pyc", ".db", ".png", ".jpg", ".gif"}:
                continue
            text = path.read_text(encoding="utf-8", errors="ignore")
            for pattern in PATTERNS:
                for match in pattern.findall(text):
                    value = match if isinstance(match, str) else " ".join(match)
                    if "test_secret_scanner.py" in str(path) or any(
                        marker in value for marker in PLACEHOLDERS
                    ):
                        placeholders += 1
                    else:
                        findings.append(f"{path}: {value[:12]}...")
    return findings, placeholders


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    roots = [
        Path("src"),
        Path("tests"),
        Path("demo"),
        Path("docs"),
        Path("README.md"),
        Path("pyproject.toml"),
    ]
    findings, placeholders = scan(roots)
    text = f"发现疑似秘密：{len(findings)}\n测试占位符：{placeholders}\n"
    if findings:
        text += "\n".join(findings) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    print(text, end="")
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
