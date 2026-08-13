"""Compatibility module for built-in security patterns."""

from gitplus.security.rule_registry import (
    local_path_rule,
    network_rules,
    personal_information_rules,
    secret_rules,
)

__all__ = ["local_path_rule", "network_rules", "personal_information_rules", "secret_rules"]

