from gitplus.config import SecurityConfig
from gitplus.security.privacy_masker import PrivacyMasker
from gitplus.security.rule_registry import RuleRegistry
from gitplus.security.secret_scanner import SecretScanner


def test_masker_replaces_repeated_values_stably_without_public_original_mapping() -> None:
    config = SecurityConfig()
    rules = RuleRegistry(config).get_rules()
    scanner = SecretScanner(rules, config)
    text = "A='10.0.0.1'\nB='10.0.0.1'\nC='10.0.0.2'\n"
    findings = scanner.scan_text(text, file_path="app.py")

    result = PrivacyMasker(config, rules).mask_text(text, findings)

    assert "10.0.0.1" not in result.masked_text
    assert "10.0.0.2" not in result.masked_text
    assert result.masked_text.count("<PRIVATE_IP_1>") == 2
    assert "<PRIVATE_IP_2>" in result.masked_text
    assert all("10.0.0." not in mapping.masked_value for mapping in result.mappings)


def test_masker_preserves_non_sensitive_text() -> None:
    config = SecurityConfig()
    rules = RuleRegistry(config).get_rules()
    text = "print('hello')\n"
    findings = SecretScanner(rules, config).scan_text(text, file_path="safe.py")

    result = PrivacyMasker(config, rules).mask_text(text, findings)

    assert result.masked_text == text

