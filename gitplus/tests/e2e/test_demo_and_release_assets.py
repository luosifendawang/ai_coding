import json
import subprocess
import sys
from pathlib import Path


def test_demo_create_and_reset_are_safe(tmp_path: Path) -> None:
    demo_dir = tmp_path / "demo"
    create = subprocess.run(
        [sys.executable, "demo/create_demo_repo.py", "--output", str(demo_dir)],
        cwd=Path.cwd(),
        check=False,
        capture_output=True,
        text=True,
    )
    blocked = subprocess.run(
        [sys.executable, "demo/reset_demo.py", "--path", str(tmp_path / "not-demo"), "--yes"],
        cwd=Path.cwd(),
        check=False,
        capture_output=True,
        text=True,
    )
    assert create.returncode == 0, create.stderr
    assert (demo_dir / ".gitplus-demo").exists()
    assert blocked.returncode == 2

    reset = subprocess.run(
        [sys.executable, "demo/reset_demo.py", "--path", str(demo_dir), "--yes"],
        cwd=Path.cwd(),
        check=False,
        capture_output=True,
        text=True,
    )

    assert reset.returncode == 0
    assert not demo_dir.exists()


def test_evaluation_dataset_has_at_least_50_samples() -> None:
    result = subprocess.run(
        [sys.executable, "evaluation/run_evaluation.py"],
        cwd=Path.cwd(),
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert json.loads(result.stdout)["total_samples"] >= 50


def test_secret_scan_script_reports_no_real_secrets(tmp_path: Path) -> None:
    result = subprocess.run(
        [sys.executable, "scripts/check_secrets.py", "--output", str(tmp_path / "security.md")],
        cwd=Path.cwd(),
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stdout
    assert "发现疑似秘密：0" in result.stdout
