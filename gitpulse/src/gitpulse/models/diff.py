"""Diff related models."""

from __future__ import annotations

from enum import Enum
from pathlib import PurePosixPath

from pydantic import BaseModel, Field


class FileChangeStatus(str, Enum):
    ADDED = "A"
    MODIFIED = "M"
    DELETED = "D"
    RENAMED = "R"
    COPIED = "C"
    UNMERGED = "U"
    UNKNOWN = "UNKNOWN"


class DiffSource(str, Enum):
    STAGED = "staged"
    UNSTAGED = "unstaged"
    COMMIT = "commit"
    RANGE = "range"


class IgnoredFile(BaseModel):
    path: str
    reason: str


class FileDiff(BaseModel):
    old_path: str | None = None
    new_path: str
    status: FileChangeStatus
    additions: int = 0
    deletions: int = 0
    patch: str = ""
    extension: str | None = None
    is_binary: bool = False
    is_new_file: bool = False
    is_deleted_file: bool = False
    is_renamed: bool = False
    is_copied: bool = False
    is_truncated: bool = False
    original_patch_chars: int = 0

    @classmethod
    def with_extension(cls, **data: object) -> "FileDiff":
        path = str(data.get("new_path") or "")
        data.setdefault("extension", "".join(PurePosixPath(path).suffixes) or None)
        return cls(**data)


class DiffStats(BaseModel):
    files_changed: int = 0
    insertions: int = 0
    deletions: int = 0
    total_patch_chars: int = 0


class DiffCollection(BaseModel):
    source: DiffSource
    base_commit: str | None = None
    target_commit: str | None = None
    files: list[FileDiff] = Field(default_factory=list)
    stats: DiffStats = Field(default_factory=DiffStats)
    ignored_files: list[IgnoredFile] = Field(default_factory=list)
    truncated_files: list[str] = Field(default_factory=list)
    original_total_chars: int = 0
    final_total_chars: int = 0

