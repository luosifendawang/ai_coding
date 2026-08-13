"""Release readiness checks."""

from __future__ import annotations

import os
import re
import site
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from importlib.resources import files
from pathlib import Path

from gitplus.storage.migrations.manager import CURRENT_SCHEMA_VERSION, MIGRATIONS
from gitplus.version import get_version


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
        self.root = (root or Path.cwd()).resolve()

    def run(self) -> ReleaseReadiness:
        version = get_version()
        checks = [
            self._file_exists("README.md"),
            self._readme_complete(),
            self._version_consistent(version),
            self._migration_sequence(),
            self._package_resources(),
            self._secret_scan(),
            self._command("Ruff", [sys.executable, "-m", "ruff", "check", "."], timeout=60),
            self._command("Mypy", [sys.executable, "-m", "mypy", "src"], timeout=90),
            self._build_and_install(),
        ]
        if not os.getenv("GITPLUS_RELEASE_CHECK_ACTIVE"):
            checks.insert(
                6,
                self._command(
                    "Pytest",
                    [sys.executable, "-m", "pytest"],
                    timeout=300,
                    env={"GITPLUS_RELEASE_CHECK_ACTIVE": "1"},
                ),
            )
        return ReleaseReadiness(version=version, checks=checks)

    def _file_exists(self, name: str) -> ReleaseCheck:
        exists = (self.root / name).exists()
        return ReleaseCheck(
            name=name, passed=exists, message="存在" if exists else "缺失"
        )

    def _readme_complete(self) -> ReleaseCheck:
        path = self.root / "README.md"
        text = path.read_text(encoding="utf-8") if path.exists() else ""
        required = [
            "pipx install gitplus",
            "gitplus init",
            "gitplus web",
            "127.0.0.1",
            "不会自动 Push",
            "Webhook",
            "mode: app",
        ]
        missing = [item for item in required if item not in text]
        return ReleaseCheck(
            name="README completeness",
            passed=not missing,
            message="完整" if not missing else "缺少：" + ", ".join(missing),
        )

    def _version_consistent(self, version: str) -> ReleaseCheck:
        text = (self.root / "pyproject.toml").read_text("utf-8")
        match = re.search(r"(?m)^version\s*=\s*\"([^\"]+)\"", text)
        project_version = match.group(1) if match else None
        return ReleaseCheck(
            name="Version consistency",
            passed=project_version == version,
            message=f"package={project_version}, runtime={version}",
        )

    def _migration_sequence(self) -> ReleaseCheck:
        versions = [migration.version for migration in MIGRATIONS]
        expected = list(range(1, CURRENT_SCHEMA_VERSION + 1))
        return ReleaseCheck(
            name="Database migrations",
            passed=versions == expected,
            message=f"{versions}",
        )

    def _package_resources(self) -> ReleaseCheck:
        required = [
            files("gitplus.prompts").joinpath("commit_system.txt"),
            files("gitplus.prompts").joinpath("weekly_system.txt"),
            files("gitplus.web").joinpath("templates/base.html"),
            files("gitplus.web").joinpath("templates/index.html"),
            files("gitplus.web").joinpath("static/css/app.css"),
            files("gitplus.web").joinpath("static/js/app.js"),
        ]
        missing = [str(item) for item in required if not item.is_file()]
        return ReleaseCheck(
            name="Web and prompt resources",
            passed=not missing,
            message="完整" if not missing else "缺少：" + ", ".join(missing),
        )

    def _secret_scan(self) -> ReleaseCheck:
        suspicious = []
        patterns = [
            re.compile(r"sk-[A-Za-z0-9]{20,}"),
            re.compile(r"(?i)(?:api_key|secret|password)\s*=\s*['\"][^'\"]{12,}['\"]"),
        ]
        for path in [
            self.root / "src",
            self.root / "tests",
            self.root / "docs",
            self.root / "README.md",
        ]:
            if not path.exists():
                continue
            files_to_scan = (
                [path]
                if path.is_file()
                else [item for item in path.rglob("*") if item.is_file()]
            )
            for file in files_to_scan:
                if "__pycache__" in file.parts or file.suffix in {".pyc", ".db"}:
                    continue
                text = file.read_text(encoding="utf-8", errors="ignore")
                for pattern in patterns:
                    for match in pattern.findall(text):
                        value = match if isinstance(match, str) else " ".join(match)
                        if any(
                            marker in value
                            for marker in [
                                "test",
                                "example",
                                "...",
                                "hardcoded",
                                "client-secret",
                                "${",
                            ]
                        ):
                            continue
                        suspicious.append(str(file.relative_to(self.root)))
        return ReleaseCheck(
            name="Secret scan",
            passed=not suspicious,
            message=f"{len(set(suspicious))} suspicious files",
        )

    def _build_and_install(self) -> ReleaseCheck:
        with tempfile.TemporaryDirectory(prefix="gitplus-release-") as tmp:
            tmp_path = Path(tmp)
            build = self._run(
                [
                    sys.executable,
                    "-m",
                    "build",
                    "--no-isolation",
                    "--outdir",
                    str(tmp_path / "dist"),
                ],
                timeout=90,
            )
            if build.returncode != 0:
                return ReleaseCheck("Build and wheel install", False, self._summary(build))
            wheels = sorted((tmp_path / "dist").glob("*.whl"))
            sdists = sorted((tmp_path / "dist").glob("*.tar.gz"))
            if not wheels or not sdists:
                return ReleaseCheck(
                    "Build and wheel install",
                    False,
                    "缺少 wheel 或 sdist",
                )
            target = tmp_path / "install"
            install = self._run(
                [
                    sys.executable,
                    "-m",
                    "pip",
                    "install",
                    "--no-deps",
                    "--target",
                    str(target),
                    str(wheels[-1]),
                ],
                timeout=90,
            )
            if install.returncode != 0:
                return ReleaseCheck(
                    "Build and wheel install", False, self._summary(install)
                )
            env = {
                **os.environ,
                "PYTHONPATH": str(target),
                "HOME": str(tmp_path / "home"),
                "XDG_CONFIG_HOME": str(tmp_path / "config"),
            }
            cli = self._run(
                [
                    sys.executable,
                    "-c",
                    "from gitplus.cli import main; import sys; sys.argv=['gitplus','--version']; main()",
                ],
                timeout=20,
                env=env,
            )
            return ReleaseCheck(
                "Build and wheel install",
                cli.returncode == 0,
                "wheel/sdist ok, CLI ok" if cli.returncode == 0 else self._summary(cli),
            )

    def _command(
        self,
        name: str,
        command: list[str],
        *,
        timeout: int,
        env: dict[str, str] | None = None,
    ) -> ReleaseCheck:
        result = self._run(command, timeout=timeout, env=env)
        return ReleaseCheck(
            name=name,
            passed=result.returncode == 0,
            message="通过" if result.returncode == 0 else self._summary(result),
        )

    def _run(
        self,
        command: list[str],
        *,
        timeout: int,
        env: dict[str, str] | None = None,
    ) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory(prefix="gitplus-release-home-") as tmp:
            isolated_home = Path(tmp)
            isolated_env = {
                **os.environ,
                "HOME": str(isolated_home / "home"),
                "XDG_CONFIG_HOME": str(isolated_home / "config"),
            }
            user_site = site.getusersitepackages()
            if Path(user_site).exists():
                python_path = isolated_env.get("PYTHONPATH")
                isolated_env["PYTHONPATH"] = (
                    user_site if not python_path else os.pathsep.join([user_site, python_path])
                )
            if env:
                isolated_env.update(env)
            try:
                return subprocess.run(
                    command,
                    cwd=self.root,
                    check=False,
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                    env=isolated_env,
                )
            except subprocess.TimeoutExpired as exc:
                stdout = exc.stdout.decode() if isinstance(exc.stdout, bytes) else exc.stdout
                stderr = exc.stderr.decode() if isinstance(exc.stderr, bytes) else exc.stderr
                return subprocess.CompletedProcess(
                    command,
                    124,
                    stdout=stdout or "",
                    stderr=stderr or "timeout",
                )

    def _summary(self, result: subprocess.CompletedProcess[str]) -> str:
        output = (result.stdout or result.stderr or "").strip().splitlines()
        tail = " | ".join(output[-3:]) if output else "无输出"
        return f"exit={result.returncode}: {tail[:500]}"
