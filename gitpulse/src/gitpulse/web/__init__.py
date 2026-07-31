"""Local GitPulse Web console."""

from __future__ import annotations

from pathlib import Path
from typing import Any


def create_app(project_root: Path | None = None, **kwargs: Any):
    """Import FastAPI lazily so non-Web CLI commands keep a small startup path."""
    from gitpulse.web.app import create_app as factory

    return factory(project_root, **kwargs)
