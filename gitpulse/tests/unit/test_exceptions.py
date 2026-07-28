from gitpulse.exceptions import ConfigurationError, GitPulseError


def test_custom_exceptions_share_base_type() -> None:
    assert issubclass(ConfigurationError, GitPulseError)

