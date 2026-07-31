"""Git output parsers."""

from __future__ import annotations

import shlex

from gitpulse.models.diff import FileChangeStatus, FileDiff
from gitpulse.models.repository import GitStatusEntry

CONFLICT_STATUSES = {"DD", "AU", "UD", "UA", "DU", "AA", "UU"}


def normalize_git_path(path: str) -> str:
    """Normalize Git relative paths to POSIX separators."""
    return path.replace("\\", "/").strip()


def parse_porcelain_status_z(output: str) -> list[GitStatusEntry]:
    """Parse `git status --porcelain=v1 -z` output."""
    if not output:
        return []

    parts = output.split("\0")
    entries: list[GitStatusEntry] = []
    index = 0
    while index < len(parts):
        item = parts[index]
        index += 1
        if not item:
            continue
        if len(item) < 3:
            continue

        index_status = item[0]
        worktree_status = item[1]
        path = normalize_git_path(item[3:])
        original_path = None
        if index_status in {"R", "C"} and index < len(parts):
            original_path = normalize_git_path(parts[index])
            index += 1

        status_pair = f"{index_status}{worktree_status}"
        entries.append(
            GitStatusEntry(
                index_status=index_status,
                worktree_status=worktree_status,
                path=path,
                original_path=original_path,
                is_conflict=status_pair in CONFLICT_STATUSES,
            )
        )
    return entries


def strip_diff_prefix(path: str) -> str:
    if path in {"/dev/null", ""}:
        return path
    if path.startswith(("a/", "b/")):
        return path[2:]
    return path


def parse_git_patch(patch: str) -> list[FileDiff]:
    """Parse unified Git patch text into file-level diffs."""
    if not patch.strip():
        return []

    blocks: list[str] = []
    current: list[str] = []
    for line in patch.splitlines(keepends=True):
        if line.startswith("diff --git ") and current:
            blocks.append("".join(current))
            current = [line]
        else:
            current.append(line)
    if current:
        blocks.append("".join(current))

    return [_parse_file_diff_block(block) for block in blocks if block.startswith("diff --git ")]


def _parse_file_diff_block(block: str) -> FileDiff:
    lines = block.splitlines()
    header = lines[0]
    old_path, new_path = _paths_from_diff_header(header)
    status = FileChangeStatus.MODIFIED
    is_binary = False
    is_new = False
    is_deleted = False
    is_renamed = False
    is_copied = False

    for line in lines[1:]:
        if line.startswith("new file mode"):
            status = FileChangeStatus.ADDED
            is_new = True
        elif line.startswith("deleted file mode"):
            status = FileChangeStatus.DELETED
            is_deleted = True
        elif line.startswith("rename from "):
            old_path = normalize_git_path(line.removeprefix("rename from "))
            status = FileChangeStatus.RENAMED
            is_renamed = True
        elif line.startswith("rename to "):
            new_path = normalize_git_path(line.removeprefix("rename to "))
        elif line.startswith("copy from "):
            old_path = normalize_git_path(line.removeprefix("copy from "))
            status = FileChangeStatus.COPIED
            is_copied = True
        elif line.startswith("copy to "):
            new_path = normalize_git_path(line.removeprefix("copy to "))
        elif line.startswith(("Binary files ", "GIT binary patch")):
            is_binary = True
        elif line.startswith("--- "):
            candidate = strip_diff_prefix(_clean_patch_path(line.removeprefix("--- ")))
            if candidate != "/dev/null":
                old_path = normalize_git_path(candidate)
        elif line.startswith("+++ "):
            candidate = strip_diff_prefix(_clean_patch_path(line.removeprefix("+++ ")))
            if candidate != "/dev/null":
                new_path = normalize_git_path(candidate)

    if "--- /dev/null" in block:
        is_new = True
        status = FileChangeStatus.ADDED
    if "+++ /dev/null" in block:
        is_deleted = True
        status = FileChangeStatus.DELETED

    additions, deletions = count_patch_lines(block)
    safe_patch = "[GitPulse: binary file diff omitted]" if is_binary else block
    return FileDiff.with_extension(
        old_path=old_path if old_path != "/dev/null" else None,
        new_path=new_path,
        status=status,
        additions=additions,
        deletions=deletions,
        patch=safe_patch,
        is_binary=is_binary,
        is_new_file=is_new,
        is_deleted_file=is_deleted,
        is_renamed=is_renamed,
        is_copied=is_copied,
        original_patch_chars=len(block),
    )


def _paths_from_diff_header(header: str) -> tuple[str | None, str]:
    rest = header.removeprefix("diff --git ")
    try:
        parts = shlex.split(rest)
    except ValueError:
        parts = rest.split()
    if len(parts) >= 2:
        return normalize_git_path(strip_diff_prefix(parts[0])), normalize_git_path(strip_diff_prefix(parts[1]))
    if " b/" in rest:
        left, right = rest.split(" b/", 1)
        return normalize_git_path(strip_diff_prefix(left)), normalize_git_path(right)
    return None, "UNKNOWN"


def _clean_patch_path(path: str) -> str:
    value = path.split("\t", 1)[0].strip()
    if not value.startswith(('"', "'")):
        return value
    try:
        parsed = shlex.split(value)
    except ValueError:
        parsed = []
    return parsed[0] if parsed else value


def count_patch_lines(block: str) -> tuple[int, int]:
    additions = 0
    deletions = 0
    for line in block.splitlines():
        if line.startswith(("+++", "---")):
            continue
        if line.startswith("+"):
            additions += 1
        elif line.startswith("-"):
            deletions += 1
    return additions, deletions


def parse_numstat_z(output: str) -> dict[str, tuple[int, int]]:
    """Parse `git diff --numstat -z` output keyed by new path."""
    if not output:
        return {}
    parts = output.split("\0")
    stats: dict[str, tuple[int, int]] = {}
    index = 0
    while index < len(parts):
        item = parts[index]
        index += 1
        if not item:
            continue
        columns = item.split("\t")
        if len(columns) >= 3:
            additions = 0 if columns[0] == "-" else int(columns[0])
            deletions = 0 if columns[1] == "-" else int(columns[1])
            path = normalize_git_path(columns[2])
            stats[path] = (additions, deletions)
            continue
        if len(columns) == 2 and index + 1 < len(parts):
            additions = 0 if columns[0] == "-" else int(columns[0])
            deletions = 0 if columns[1] == "-" else int(columns[1])
            old_path = parts[index]
            new_path = parts[index + 1]
            index += 2
            stats[normalize_git_path(new_path or old_path)] = (additions, deletions)
    return stats
