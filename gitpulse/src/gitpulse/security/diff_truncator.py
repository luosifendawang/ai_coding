"""Diff truncation utilities."""

from __future__ import annotations

from gitpulse.config import DiffConfig
from gitpulse.models.diff import DiffCollection

TRUNCATION_MARKER = "\n[GitPulse: 当前文件 Diff 已截断]\n"


class DiffTruncator:
    """Apply per-file and total patch size limits."""

    def __init__(self, config: DiffConfig) -> None:
        if config.max_file_chars <= 0 or config.max_total_chars <= 0:
            raise ValueError("max_file_chars and max_total_chars must be positive")
        self.config = config

    def truncate(self, collection: DiffCollection) -> DiffCollection:
        original_total = sum(len(file.patch) for file in collection.files)
        final_total = 0
        truncated_files: list[str] = list(collection.truncated_files)

        for file in collection.files:
            file.original_patch_chars = len(file.patch)
            if len(file.patch) > self.config.max_file_chars:
                keep = max(0, self.config.max_file_chars - len(TRUNCATION_MARKER))
                file.patch = file.patch[:keep] + TRUNCATION_MARKER
                file.is_truncated = True
                truncated_files.append(file.new_path)

        for file in collection.files:
            patch_len = len(file.patch)
            if final_total + patch_len <= self.config.max_total_chars:
                final_total += patch_len
                continue
            remaining = max(0, self.config.max_total_chars - final_total)
            if remaining > len(TRUNCATION_MARKER):
                file.patch = file.patch[: remaining - len(TRUNCATION_MARKER)] + TRUNCATION_MARKER
                final_total += len(file.patch)
            else:
                file.patch = TRUNCATION_MARKER
                final_total += len(file.patch)
            file.is_truncated = True
            truncated_files.append(file.new_path)
            for later in collection.files[collection.files.index(file) + 1 :]:
                if later.patch:
                    later.original_patch_chars = len(later.patch)
                    later.patch = TRUNCATION_MARKER
                    later.is_truncated = True
                    truncated_files.append(later.new_path)
                    final_total += len(later.patch)
            break

        collection.original_total_chars = original_total
        collection.final_total_chars = sum(len(file.patch) for file in collection.files)
        collection.truncated_files = list(dict.fromkeys(truncated_files))
        collection.stats.total_patch_chars = collection.final_total_chars
        return collection
