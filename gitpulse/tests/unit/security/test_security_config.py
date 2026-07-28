import pytest
from pydantic import ValidationError

from gitpulse.config import SecurityConfig


def test_security_config_defaults_are_safe() -> None:
    config = SecurityConfig()

    assert config.enabled is True
    assert config.block_remote_on_high_risk is True
    assert config.block_remote_on_scan_failure is True
    assert config.keep_last_chars == 4


def test_security_config_rejects_invalid_limits() -> None:
    with pytest.raises(ValidationError):
        SecurityConfig(keep_last_chars=13)

    with pytest.raises(ValidationError):
        SecurityConfig(max_findings_per_rule=0)


def test_security_config_rejects_duplicate_custom_pattern_ids() -> None:
    with pytest.raises(ValidationError):
        SecurityConfig(
            custom_patterns=[
                {"id": "custom_rule", "name": "A", "pattern": r"abc+", "level": "low", "description": "a"},
                {"id": "custom_rule", "name": "B", "pattern": r"def+", "level": "low", "description": "b"},
            ]
        )


def test_security_config_rejects_empty_matching_pattern() -> None:
    with pytest.raises(ValidationError):
        SecurityConfig(
            custom_patterns=[
                {"id": "bad_rule", "name": "Bad", "pattern": r".*", "level": "low", "description": "bad"}
            ]
        )

