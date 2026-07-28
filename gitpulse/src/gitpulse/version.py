"""Version helpers."""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

PACKAGE_NAME = "gitpulse"
FALLBACK_VERSION = "0.1.0"


def get_version() -> str:
    """Return the installed package version with a development fallback."""
    try:
        return version(PACKAGE_NAME)
    except PackageNotFoundError:
        return FALLBACK_VERSION
