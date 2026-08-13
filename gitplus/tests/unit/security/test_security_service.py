from gitplus.config import SecurityConfig
from gitplus.models.diff import DiffCollection, DiffSource, FileChangeStatus, FileDiff
from gitplus.services.security_service import SecurityService


def collection_with_patch(patch: str) -> DiffCollection:
    return DiffCollection(
        source=DiffSource.STAGED,
        files=[
            FileDiff.with_extension(
                new_path="config.py",
                status=FileChangeStatus.MODIFIED,
                patch=patch,
            )
        ],
    )


def test_security_service_returns_sanitized_diff_and_blocks_high_risk() -> None:
    result = SecurityService(SecurityConfig()).process_diff(
        collection_with_patch("+API_KEY='sk-testexample1234567890abcdef'\n")
    )

    assert result.scan_completed is True
    assert result.block_remote_model is True
    assert result.summary.high == 1
    assert "sk-testexample" not in result.sanitized_diff
    assert "<API_KEY_1>" in result.sanitized_diff


def test_security_service_allows_sanitized_medium_and_low_risks() -> None:
    result = SecurityService(SecurityConfig()).process_diff(
        collection_with_patch('+SERVER="10.0.0.1"\n+HOME="/home/testuser/cache"\n')
    )

    assert result.block_remote_model is False
    assert result.summary.medium == 1
    assert result.summary.low == 1
    assert "10.0.0.1" not in result.sanitized_diff
    assert "/home/testuser" not in result.sanitized_diff

def test_security_service_can_be_disabled() -> None:
    result = SecurityService(SecurityConfig(enabled=False)).process_diff(collection_with_patch("+safe = True\n"))

    assert result.scan_completed is True
    assert result.block_remote_model is False
    assert result.findings == []

