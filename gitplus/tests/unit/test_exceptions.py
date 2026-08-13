from gitplus.exceptions import ConfigurationError, GitPlusError


def test_custom_exceptions_share_base_type() -> None:
    assert issubclass(ConfigurationError, GitPlusError)

