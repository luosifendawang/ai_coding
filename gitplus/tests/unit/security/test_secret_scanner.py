from __future__ import annotations

from gitplus.config import SecurityConfig
from gitplus.models.diff import DiffCollection, DiffSource, FileChangeStatus, FileDiff
from gitplus.models.risk import RiskLevel
from gitplus.security.rule_registry import RuleRegistry
from gitplus.security.secret_scanner import SecretScanner


def make_scanner(config: SecurityConfig | None = None) -> SecretScanner:
    config = config or SecurityConfig()
    return SecretScanner(RuleRegistry(config).get_rules(), config)


def test_scanner_detects_required_secret_rules_without_leaking_values() -> None:
    text = """
OPENAI_KEY = "sk-testexample1234567890abcdef"
GITHUB_TOKEN = "ghp_abcdefghijklmnopqrstuvwxyz123456"
GITLAB_TOKEN = "glpat-abcdefghijklmnopqrstuvwxyz12"
AWS_KEY = "AKIA1234567890ABCDEF"
AUTH = "Bearer abcdefghijklmnopqrstuvwxyz123456"
JWT = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.signatureABCDEF123456"
password = "hardcoded-secret-value"
secret = "client-secret-value-123"
"""

    findings = make_scanner().scan_text(text, file_path="config.py")
    rule_ids = {finding.rule_id for finding in findings}

    assert "openai_api_key" in rule_ids
    assert "github_token" in rule_ids
    assert "gitlab_token" in rule_ids
    assert "aws_access_key" in rule_ids
    assert "bearer_token" in rule_ids
    assert "jwt" in rule_ids
    assert "hardcoded_password" in rule_ids
    assert "hardcoded_secret" in rule_ids
    assert all(finding.level == RiskLevel.HIGH for finding in findings)
    assert all("sk-testexample" not in (finding.masked_value or "") for finding in findings)


def test_scanner_ignores_env_password_and_placeholder() -> None:
    text = 'password = os.getenv("DB_PASSWORD")\npassword = "${DB_PASSWORD}"\npassword = "changeme"\n'

    findings = make_scanner().scan_text(text, file_path="settings.py")

    assert findings == []


def test_scanner_detects_typed_and_yaml_api_key_assignments() -> None:
    text = """
api_key: str = "typed-secret-value-123"
api_key: yaml-secret-value-456
api_key_env: str = "GITPLUS_API_KEY"
"""

    findings = make_scanner().scan_text(text, file_path="config.py")
    hardcoded = [finding for finding in findings if finding.rule_id == "hardcoded_secret"]

    assert len(hardcoded) == 2
    assert all(finding.level == RiskLevel.HIGH for finding in hardcoded)


def test_scanner_detects_api_key_misused_as_env_name() -> None:
    text = """
api_key_env: str = "provider-key.value-123456"
api_key_env: str = "GITPLUS_API_KEY"
"""

    findings = make_scanner().scan_text(text, file_path="config.py")
    misconfigured = [finding for finding in findings if finding.rule_id == "api_key_in_env_name"]

    assert len(misconfigured) == 1
    assert misconfigured[0].blocks_remote_model is True


def test_scanner_detects_private_key_database_and_cloud_connection() -> None:
    text = """
PRIVATE = "-----BEGIN RSA PRIVATE KEY-----
abc
-----END RSA PRIVATE KEY-----"
DATABASE_URL = "postgresql://user:password@10.0.0.8/app"
AZURE = "AccountKey=abcdefghijklmnopqrstuvwxyz123456"
"""

    findings = make_scanner().scan_text(text, file_path="secrets.py")
    by_rule = {finding.rule_id: finding for finding in findings}

    assert by_rule["pem_private_key"].level == RiskLevel.CRITICAL
    assert by_rule["pem_private_key"].masked_value == "<PRIVATE_KEY>"
    assert by_rule["database_url"].level == RiskLevel.HIGH
    assert by_rule["cloud_connection_string"].level == RiskLevel.HIGH


def test_scanner_detects_privacy_and_network_rules() -> None:
    text = """
SERVER = "10.0.0.1"
LOCAL = "127.0.0.1"
PUBLIC = "8.8.8.8"
BAD = "172.32.0.1"
HOME = "/home/testuser/project"
MAIL = "dev@example.test"
PHONE = "+86 13812345678"
ID_CARD = "11010519491231002X"
HOST = "service.demo.internal"
"""

    findings = make_scanner().scan_text(text, file_path="app.py")
    rule_ids = [finding.rule_id for finding in findings]

    assert rule_ids.count("private_ipv4") == 2
    assert "local_user_path" in rule_ids
    assert "email" in rule_ids
    assert "china_phone_number" in rule_ids
    assert "china_id_card" in rule_ids
    assert "internal_domain" in rule_ids
    assert "8.8.8.8" not in [finding.masked_value for finding in findings]


def test_scanner_calculates_line_and_limits_findings() -> None:
    scanner = make_scanner(SecurityConfig(max_findings_per_rule=1))
    text = "safe\nA='sk-testexample1234567890abcdef'\nB='sk-testexample1234567890abcdeg'\n"

    findings = scanner.scan_text(text, file_path="config.py")

    assert len([finding for finding in findings if finding.rule_id == "openai_api_key"]) == 1
    assert findings[0].line_number == 2


def test_scan_collection_warns_for_truncated_file() -> None:
    file_diff = FileDiff.with_extension(
        new_path="config.py",
        status=FileChangeStatus.MODIFIED,
        patch="+KEY='sk-testexample1234567890abcdef'\n",
        is_truncated=True,
    )
    result = make_scanner().scan_collection(DiffCollection(source=DiffSource.STAGED, files=[file_diff]))

    assert result.summary.high == 1
    assert result.block_remote_model is True
    assert result.warnings
