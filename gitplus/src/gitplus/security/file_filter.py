"""File filtering for Git diffs."""

from __future__ import annotations

from fnmatch import fnmatchcase

from gitplus.config import DiffConfig


class FileFilter:
    """Apply configured ignore rules to Git relative paths."""

    def __init__(self, config: DiffConfig) -> None:
        self.config = config

    def should_ignore(self, path: str, is_binary: bool) -> tuple[bool, str | None]:
        normalized = path.replace("\\", "/").lstrip("/")
        if is_binary and self.config.ignore_binary:
            return True, "binary file ignored by configuration"
        if normalized.split("/")[-1] in {"package-lock.json", "yarn.lock", "pnpm-lock.yaml"}:
            return True, "known dependency lock file"
        for pattern in self.config.ignore_patterns:
            normalized_pattern = pattern.replace("\\", "/").lstrip("/")
            if fnmatchcase(normalized, normalized_pattern) or fnmatchcase(
                normalized.split("/")[-1], normalized_pattern
            ):
                return True, f"matched ignore pattern: {pattern}"
        return False, None
