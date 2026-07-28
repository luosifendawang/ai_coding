from gitpulse.config import DiffConfig
from gitpulse.security.file_filter import FileFilter


def test_file_filter_matches_configured_patterns() -> None:
    file_filter = FileFilter(DiffConfig())

    ignored = [
        "package-lock.json",
        "dist/app.js",
        "build/output.bin",
        "node_modules/pkg/index.js",
        "assets/app.min.js",
    ]

    for path in ignored:
        should_ignore, reason = file_filter.should_ignore(path, is_binary=False)
        assert should_ignore is True
        assert reason


def test_file_filter_does_not_match_similar_names() -> None:
    file_filter = FileFilter(DiffConfig())

    for path in ["src/main.py", "src/config.locked.py", "distribution/app.js"]:
        should_ignore, reason = file_filter.should_ignore(path, is_binary=False)
        assert should_ignore is False
        assert reason is None


def test_file_filter_can_ignore_binary_files() -> None:
    file_filter = FileFilter(DiffConfig(ignore_binary=True))

    should_ignore, reason = file_filter.should_ignore("assets/logo.png", is_binary=True)

    assert should_ignore is True
    assert "binary" in reason

