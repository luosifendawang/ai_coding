from gitplus.version import get_version


def test_get_version_returns_semver() -> None:
    version = get_version()

    assert version.count(".") >= 2
