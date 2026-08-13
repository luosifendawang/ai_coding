from gitplus.config import SecurityConfig
from gitplus.security.rule_registry import RuleRegistry


def test_rule_registry_loads_builtin_rules() -> None:
    rules = RuleRegistry(SecurityConfig()).get_rules()
    rule_ids = {rule.id for rule in rules}

    assert "openai_api_key" in rule_ids
    assert "github_token" in rule_ids
    assert "private_ipv4" in rule_ids
    assert "email" in rule_ids
    assert all(not rule.pattern.match("") for rule in rules)


def test_rule_registry_can_ignore_rules() -> None:
    rules = RuleRegistry(SecurityConfig(ignored_rules=["openai_api_key"])).get_rules()

    assert "openai_api_key" not in {rule.id for rule in rules}


def test_rule_registry_loads_custom_rules() -> None:
    rules = RuleRegistry(
        SecurityConfig(
            custom_patterns=[
                {
                    "id": "custom_demo_token",
                    "name": "Custom Demo Token",
                    "pattern": r"demo_[A-Za-z0-9]{8,}",
                    "level": "medium",
                    "description": "demo token",
                }
            ]
        )
    ).get_rules()

    custom = next(rule for rule in rules if rule.id == "custom_demo_token")
    assert custom.pattern.search("value=demo_ABCDEFGH")
    assert custom.level.value == "medium"

