"""Logging setup for GitPulse."""

from __future__ import annotations

import sys

from loguru import logger


SENSITIVE_MARKERS = ("api_key", "token", "secret", "webhook", "password")


def mask_log_message(message: str) -> str:
    """Mask obvious secret-like values in log messages."""
    masked = message
    for marker in SENSITIVE_MARKERS:
        masked = masked.replace(marker, f"{marker[:2]}****")
        masked = masked.replace(marker.upper(), f"{marker[:2].upper()}****")
    return masked


def configure_logging(debug: bool = False) -> None:
    """Configure application logging with a conservative default level."""
    logger.remove()
    level = "DEBUG" if debug else "INFO"
    logger.add(
        sys.stderr,
        level=level,
        format="<level>{level}</level> {message}",
        filter=lambda record: not record["extra"].get("suppress", False),
    )

