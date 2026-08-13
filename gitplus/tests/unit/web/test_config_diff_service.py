from gitplus.web.services.config_diff_service import ConfigDiffService


def test_diff_is_field_level_and_masks_secret() -> None:
    changes = ConfigDiffService().compare(
        {"ai": {"model": "old", "api_key": "old-secret"}},
        {"ai": {"model": "new", "api_key": "new-secret"}},
        source="project",
    )

    assert {item["path"] for item in changes} == {"ai.model", "ai.api_key"}
    assert "old-secret" not in str(changes)
    assert "new-secret" not in str(changes)
