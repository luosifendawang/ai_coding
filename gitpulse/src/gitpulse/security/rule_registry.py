"""Security rule definitions and registry."""

from __future__ import annotations

import re
from dataclasses import dataclass
from re import Pattern

from gitpulse.config import CustomSecurityPattern, SecurityConfig
from gitpulse.models.risk import RiskCategory, RiskLevel


@dataclass(frozen=True)
class SecurityRule:
    id: str
    name: str
    pattern: Pattern[str]
    category: RiskCategory
    level: RiskLevel
    description: str
    suggestion: str
    replacement: str
    blocks_remote_model: bool
    enabled_by_default: bool = True
    confidence: float = 1.0


def compile_rule(
    *,
    rule_id: str,
    name: str,
    pattern: str,
    category: RiskCategory,
    level: RiskLevel,
    description: str,
    suggestion: str,
    replacement: str,
    blocks_remote_model: bool,
    confidence: float = 1.0,
) -> SecurityRule:
    compiled = re.compile(pattern, re.MULTILINE | re.DOTALL)
    if compiled.match(""):
        raise ValueError(f"security rule must not match empty string: {rule_id}")
    return SecurityRule(
        id=rule_id,
        name=name,
        pattern=compiled,
        category=category,
        level=level,
        description=description,
        suggestion=suggestion,
        replacement=replacement,
        blocks_remote_model=blocks_remote_model,
        confidence=confidence,
    )


class RuleRegistry:
    """Build enabled security rules from built-ins and configuration."""

    def __init__(self, config: SecurityConfig) -> None:
        self.config = config

    def get_rules(self) -> list[SecurityRule]:
        ignored = set(self.config.ignored_rules)
        rules = [rule for rule in self._builtin_rules() if rule.id not in ignored]
        rules.extend(self._custom_rules(ignored))
        return rules

    def _custom_rules(self, ignored: set[str]) -> list[SecurityRule]:
        custom_rules: list[SecurityRule] = []
        for pattern in self.config.custom_patterns:
            if pattern.id in ignored:
                continue
            custom_rules.append(
                compile_rule(
                    rule_id=pattern.id,
                    name=pattern.name,
                    pattern=pattern.pattern,
                    category=RiskCategory.UNKNOWN,
                    level=RiskLevel(pattern.level),
                    description=pattern.description,
                    suggestion="请检查自定义规则命中的内容。",
                    replacement=pattern.replacement,
                    blocks_remote_model=RiskLevel(pattern.level) in {RiskLevel.HIGH, RiskLevel.CRITICAL},
                )
            )
        return custom_rules

    def _builtin_rules(self) -> list[SecurityRule]:
        rules: list[SecurityRule] = []
        if self.config.scan_secrets:
            rules.extend(secret_rules())
        if self.config.scan_internal_network:
            rules.extend(network_rules(self.config.internal_domain_suffixes))
        if self.config.scan_personal_information:
            rules.extend(personal_information_rules())
        if self.config.mask_local_paths:
            rules.append(local_path_rule())
        return rules


def secret_rules() -> list[SecurityRule]:
    return [
        compile_rule(
            rule_id="openai_api_key",
            name="OpenAI API Key",
            pattern=r"\bsk-[A-Za-z0-9_-]{20,}\b",
            category=RiskCategory.SECRET,
            level=RiskLevel.HIGH,
            description="检测到疑似 OpenAI 风格 API Key。",
            suggestion="将 API Key 放在未纳入版本控制的本地配置或凭证管理器中，并从暂存区移除该内容。",
            replacement="<API_KEY>",
            blocks_remote_model=True,
        ),
        compile_rule(
            rule_id="github_token",
            name="GitHub Token",
            pattern=r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9_]{20,}\b|\bgithub_pat_[A-Za-z0-9_]{20,}\b",
            category=RiskCategory.SECRET,
            level=RiskLevel.HIGH,
            description="检测到疑似 GitHub Token。",
            suggestion="撤销该 Token，并改用环境变量或凭证管理器。",
            replacement="<ACCESS_TOKEN>",
            blocks_remote_model=True,
        ),
        compile_rule(
            rule_id="gitlab_token",
            name="GitLab Token",
            pattern=r"\bglpat-[A-Za-z0-9_-]{20,}\b",
            category=RiskCategory.SECRET,
            level=RiskLevel.HIGH,
            description="检测到疑似 GitLab Token。",
            suggestion="撤销该 Token，并改用环境变量或凭证管理器。",
            replacement="<ACCESS_TOKEN>",
            blocks_remote_model=True,
        ),
        compile_rule(
            rule_id="aws_access_key",
            name="AWS Access Key",
            pattern=r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b",
            category=RiskCategory.CREDENTIAL,
            level=RiskLevel.HIGH,
            description="检测到疑似 AWS Access Key ID。",
            suggestion="请确认凭证是否有效，并迁移到安全凭证管理。",
            replacement="<ACCESS_TOKEN>",
            blocks_remote_model=True,
        ),
        compile_rule(
            rule_id="bearer_token",
            name="Bearer Token",
            pattern=r"\bBearer\s+[A-Za-z0-9._~+/=-]{24,}\b",
            category=RiskCategory.SECRET,
            level=RiskLevel.HIGH,
            description="检测到疑似 Bearer Token。",
            suggestion="请避免在代码中硬编码 Authorization Token。",
            replacement="<ACCESS_TOKEN>",
            blocks_remote_model=True,
        ),
        compile_rule(
            rule_id="jwt",
            name="JWT",
            pattern=r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b",
            category=RiskCategory.SECRET,
            level=RiskLevel.HIGH,
            description="检测到疑似 JWT。",
            suggestion="请避免提交可用的 JWT 或会话令牌。",
            replacement="<ACCESS_TOKEN>",
            blocks_remote_model=True,
        ),
        compile_rule(
            rule_id="hardcoded_password",
            name="Hardcoded Password",
            pattern=r"(?i)\b(?:password|passwd|pwd)\b\s*[:=]\s*[\"'](?!\s*(?:changeme|your_password|example|test-token))[A-Za-z0-9_@#$%^&*+=!?.:-]{8,}[\"']",
            category=RiskCategory.CREDENTIAL,
            level=RiskLevel.HIGH,
            description="检测到疑似硬编码密码。",
            suggestion="请改用环境变量或本地 Secret 管理。",
            replacement="<PASSWORD>",
            blocks_remote_model=True,
        ),
        compile_rule(
            rule_id="api_key_in_env_name",
            name="API Key Used As Environment Variable Name",
            pattern=(
                r"(?i)\bapi_key_env\b"
                r"(?:\s*:\s*[A-Za-z_][A-Za-z0-9_.\[\] |,]*\s*=|\s*[:=])\s*"
                r"[\"'][A-Za-z0-9_.-]{12,}[\"']"
            ),
            category=RiskCategory.SECRET,
            level=RiskLevel.HIGH,
            description="api_key_env 中疑似填写了 API Key，而不是环境变量名称。",
            suggestion="请将凭证写入未纳入版本控制的 .gitpulse.yml 的 ai.api_key，并将 api_key_env 恢复为环境变量名称。",
            replacement="<API_KEY>",
            blocks_remote_model=True,
        ),
        compile_rule(
            rule_id="hardcoded_secret",
            name="Hardcoded Secret",
            pattern=(
                r"(?i)\b(?:secret|token|api_key|access_key|client_secret)\b"
                r"(?:\s*:\s*[A-Za-z_][A-Za-z0-9_.\[\] |,]*\s*=|\s*[:=])\s*[\"']?"
                r"(?!\s*(?:changeme|your_token_here|example-token|test-token))"
                r"[A-Za-z0-9_@#$%^&*+=!?.:/-]{12,}[\"']?"
            ),
            category=RiskCategory.SECRET,
            level=RiskLevel.HIGH,
            description="检测到疑似硬编码 Secret 或 Token。",
            suggestion="请改用未纳入版本控制的本地配置或凭证管理器。",
            replacement="<ACCESS_TOKEN>",
            blocks_remote_model=True,
        ),
        compile_rule(
            rule_id="pem_private_key",
            name="PEM Private Key",
            pattern=r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----[\s\S]*?(?:-----END (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|$)",
            category=RiskCategory.PRIVATE_KEY,
            level=RiskLevel.CRITICAL,
            description="检测到 PEM 私钥内容。",
            suggestion="立即从暂存区移除私钥，并轮换相关凭证。",
            replacement="<PRIVATE_KEY>",
            blocks_remote_model=True,
        ),
        compile_rule(
            rule_id="database_url",
            name="Database URL",
            pattern=r"\b(?:postgresql|postgres|mysql|mariadb|mongodb(?:\+srv)?|redis|rediss|sqlserver|oracle)://[^\s\"']+",
            category=RiskCategory.DATABASE_URL,
            level=RiskLevel.HIGH,
            description="检测到数据库连接字符串。",
            suggestion="请确认连接串中不包含用户名、密码或内部地址。",
            replacement="<DATABASE_URL>",
            blocks_remote_model=True,
        ),
        compile_rule(
            rule_id="cloud_connection_string",
            name="Cloud Connection String",
            pattern=r"\b(?:AccountKey|SharedAccessKey|DefaultEndpointsProtocol)\s*=\s*[^;\s\"']{12,}",
            category=RiskCategory.CLOUD_CONNECTION,
            level=RiskLevel.HIGH,
            description="检测到疑似云服务连接字符串。",
            suggestion="请改用云服务 Secret 管理或环境变量。",
            replacement="<ACCESS_TOKEN>",
            blocks_remote_model=True,
        ),
    ]


def network_rules(suffixes: list[str]) -> list[SecurityRule]:
    rules = [
        compile_rule(
            rule_id="private_ipv4",
            name="Private IPv4",
            pattern=r"\b(?:10(?:\.\d{1,3}){3}|192\.168(?:\.\d{1,3}){2}|172\.(?:1[6-9]|2\d|3[01])(?:\.\d{1,3}){2}|127(?:\.\d{1,3}){3})\b",
            category=RiskCategory.INTERNAL_NETWORK,
            level=RiskLevel.MEDIUM,
            description="检测到内网或本地 IPv4 地址。",
            suggestion="发送至远程模型前使用脱敏地址。",
            replacement="<PRIVATE_IP>",
            blocks_remote_model=False,
        )
    ]
    if suffixes:
        escaped = "|".join(re.escape(suffix.lstrip(".")) for suffix in suffixes)
        rules.append(
            compile_rule(
                rule_id="internal_domain",
                name="Internal Domain",
                pattern=rf"\b[A-Za-z0-9.-]+\.(?:{escaped})\b",
                category=RiskCategory.INTERNAL_NETWORK,
                level=RiskLevel.MEDIUM,
                description="检测到疑似内网域名。",
                suggestion="发送至远程模型前使用脱敏域名。",
                replacement="<INTERNAL_DOMAIN>",
                blocks_remote_model=False,
            )
        )
    return rules


def personal_information_rules() -> list[SecurityRule]:
    return [
        compile_rule(
            rule_id="email",
            name="Email Address",
            pattern=r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b",
            category=RiskCategory.PERSONAL_INFORMATION,
            level=RiskLevel.LOW,
            description="检测到邮箱地址。",
            suggestion="如需发送到远程模型，请使用脱敏邮箱。",
            replacement="<EMAIL>",
            blocks_remote_model=False,
        ),
        compile_rule(
            rule_id="china_phone_number",
            name="China Phone Number",
            pattern=r"(?<!\d)(?:\+86[\s-]?)?1[3-9]\d{9}(?!\d)",
            category=RiskCategory.PERSONAL_INFORMATION,
            level=RiskLevel.MEDIUM,
            description="检测到疑似中国大陆手机号。",
            suggestion="发送至远程模型前使用脱敏手机号。",
            replacement="<PHONE>",
            blocks_remote_model=False,
        ),
        compile_rule(
            rule_id="china_id_card",
            name="China ID Card",
            pattern=r"(?<!\d)(?:[1-9]\d{5}(?:19|20)\d{2}(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\d|3[01])\d{3}[\dXx]|[1-9]\d{14})(?!\d)",
            category=RiskCategory.PERSONAL_INFORMATION,
            level=RiskLevel.HIGH,
            description="检测到疑似中国大陆身份证号。",
            suggestion="请移除身份证号或使用脱敏占位符。",
            replacement="<ID_CARD>",
            blocks_remote_model=True,
        ),
    ]


def local_path_rule() -> SecurityRule:
    return compile_rule(
        rule_id="local_user_path",
        name="Local User Path",
        pattern=r"(?:(?:/home|/Users)/[A-Za-z0-9._-]+|[A-Za-z]:[\\/]+Users[\\/]+[A-Za-z0-9._-]+)(?:[\\/][^\s\"']*)?",
        category=RiskCategory.LOCAL_PATH,
        level=RiskLevel.LOW,
        description="检测到本地用户目录路径。",
        suggestion="建议在发送远程模型前脱敏本地路径。",
        replacement="<USER_HOME>",
        blocks_remote_model=False,
    )
