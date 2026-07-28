"""Release readiness checks."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
import subprocess

from gitpulse.storage.migrations.manager import CURRENT_SCHEMA_VERSION, MIGRATIONS
from gitpulse.version import get_version


@dataclass(frozen=True)
class ReleaseCheck:
    name: str
    passed: bool
    message: str


@dataclass(frozen=True)
class ReleaseReadiness:
    version: str
    checks: list[ReleaseCheck]

    @property
    def ready(self) -> bool:
        return all(check.passed for check in self.checks)


class ReleaseReadinessChecker:
    """Run non-publishing release checks."""

    def __init__(self, root: Path | None = None) -> None:
        self.root = root or Path.cwd()

    def run(self) -> ReleaseReadiness:
        version = get_version()
        checks = [
            self._file_exists("README.md"),
            self._file_exists("CHANGELOG.md"),
            self._file_exists("SECURITY.md"),
            self._file_exists("RELEASE_CHECKLIST.md"),
            self._changelog_contains(version),
            self._migration_sequence(),
            self._secret_scan(),
            self._git_status(),
        ]
        return ReleaseReadiness(version=version, checks=checks)

    def _file_exists(self, name: str) -> ReleaseCheck:
        exists = (self.root / name).exists()
        return ReleaseCheck(name=name, passed=exists, message="存在" if exists else "缺失")

    def _changelog_contains(self, version: str) -> ReleaseCheck:
        path = self.root / "CHANGELOG.md"
        ok = path.exists() and version in path.read_text(encoding="utf-8")
        return ReleaseCheck(name="CHANGELOG version", passed=ok, message=f"版本 {version}")

    def _migration_sequence(self) -> ReleaseCheck:
        versions = [migration.version for migration in MIGRATIONS]
        expected = list(range(1, CURRENT_SCHEMA_VERSION + 1))
        return ReleaseCheck(
            name="Database migrations",
            passed=versions == expected,
            message=f"{versions}",
        )

    def _secret_scan(self) -> ReleaseCheck:
        suspicious = []
        for path in [self.root / "src", self.root / "tests", self.root / "docs", self.root / "README.md"]:
            if not path.exists():
                continue
            files = [path] if path.is_file() else [item for item in path.rglob("*") if item.is_file()]
            for file in files:
                if "__pycache__" in file.parts or file.suffix in {".pyc", ".db"}:
                    continue
                text = file.read_text(encoding="utf-8", errors="ignore")
                matches = re.findall(r"(sk-[A-Za-z0-9]{20,}|open-apis/bot/v2/hook/[A-Za-z0-9-.]{3,})", text)
                real_matches = [
                    value
                    for value in matches
                    if "test" not in value and "example" not in value and "..." not in value and not value.endswith("abcd")
                ]
                if real_matches and "test_secret_scanner.py" not in str(file):
                    suspicious.append(str(file.relative_to(self.root)))
        return ReleaseCheck(name="Secret scan", passed=not suspicious, message=f"{len(suspicious)} suspicious files")

    def _git_status(self) -> ReleaseCheck:
        result = subprocess.run(["git", "status", "--short"], cwd=self.root, check=False, capture_output=True, text=True)
        clean = result.returncode == 0 and not result.stdout.strip()
        return ReleaseCheck(name="Git worktree", passed=clean, message="clean" if clean else "dirty or unavailable")
