import pytest

from gitpulse.config import DiffConfig
from gitpulse.models.diff import DiffCollection, DiffSource, FileChangeStatus, FileDiff
from gitpulse.security.diff_truncator import TRUNCATION_MARKER, DiffTruncator


def make_collection(*patches: str) -> DiffCollection:
    return DiffCollection(
        source=DiffSource.STAGED,
        files=[
            FileDiff.with_extension(
                new_path=f"src/file{index}.py",
                status=FileChangeStatus.MODIFIED,
                patch=patch,
            )
            for index, patch in enumerate(patches)
        ],
    )


def test_truncator_keeps_small_diff() -> None:
    collection = make_collection("small")

    result = DiffTruncator(DiffConfig(max_file_chars=20, max_total_chars=20)).truncate(collection)

    assert result.files[0].patch == "small"
    assert result.truncated_files == []


def test_truncator_truncates_large_file() -> None:
    collection = make_collection("x" * 100)

    result = DiffTruncator(DiffConfig(max_file_chars=40, max_total_chars=200)).truncate(collection)

    assert result.files[0].is_truncated is True
    assert TRUNCATION_MARKER.strip() in result.files[0].patch
    assert result.files[0].new_path in result.truncated_files


def test_truncator_truncates_total_size() -> None:
    collection = make_collection("a" * 30, "b" * 30, "c" * 30)

    result = DiffTruncator(DiffConfig(max_file_chars=100, max_total_chars=70)).truncate(collection)

    assert result.truncated_files
    assert result.original_total_chars == 90
    assert result.final_total_chars == sum(len(file.patch) for file in result.files)


def test_truncator_rejects_invalid_limits() -> None:
    with pytest.raises(ValueError):
        DiffConfig(max_file_chars=0, max_total_chars=10)
