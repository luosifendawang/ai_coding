import subprocess
from pathlib import Path


def run_git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=repo,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=True,
    )


def init_repo(path: Path, *, configure_user: bool = True) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    run_git(path, "init")
    run_git(path, "config", "core.quotepath", "false")
    if configure_user:
        run_git(path, "config", "user.name", "Test User")
        run_git(path, "config", "user.email", "test@example.com")
    return path


def commit_file(repo: Path, filename: str = "README.md", content: str = "hello\n") -> str:
    target = repo / filename
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    run_git(repo, "add", filename)
    run_git(repo, "commit", "-m", "initial commit")
    return run_git(repo, "rev-parse", "HEAD").stdout.strip()
