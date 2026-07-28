"""Repository metadata models."""

from __future__ import annotations

from enum import Enum
from pathlib import Path

from pydantic import BaseModel, ConfigDict


class GitFileStatus(str, Enum):
    ADDED = "A"
    MODIFIED = "M"
    DELETED = "D"
    RENAMED = "R"
    COPIED = "C"
    UNMERGED = "U"
    UNTRACKED = "?"
    IGNORED = "!"


class GitStatusEntry(BaseModel):
    index_status: str
    worktree_status: str
    path: str
    original_path: str | None = None
    is_conflict: bool = False


class RepositoryInfo(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    name: str
    root_path: Path
    current_branch: str | None = None
    head_commit: str | None = None
    git_user_name: str | None = None
    git_user_email: str | None = None
    remote_url: str | None = None
    has_staged_changes: bool = False
    has_unstaged_changes: bool = False
    has_untracked_files: bool = False
    has_conflicts: bool = False

