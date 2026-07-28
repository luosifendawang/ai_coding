"""Diagnostic checks for GitPulse."""

from __future__ import annotations

import locale
import os
import shutil
import subprocess
import sys
from importlib.resources import files
from pathlib import Path

from gitpulse.config import GitPulseConfig
from gitpulse.diagnostics.models import DiagnosticItem, DiagnosticStatus
from gitpulse.git.repository import GitRepository
from gitpulse.integrations.feishu_client import FeishuWebhookValidator
from gitpulse.security.rule_registry import RuleRegistry
from gitpulse.storage.database import Database
from gitpulse.storage.migrations.manager import CURRENT_SCHEMA_VERSION, MigrationManager
from gitpulse.version import get_version


class DiagnosticChecks:
    """Run local non-mutating environment checks."""

    def __init__(self, config: GitPulseConfig, *, database: Database | None = None) -> None:
        self.config = config
        self.database = database

    def run(self, *, check_ai: bool = False, check_feishu: bool = False) -> list[DiagnosticItem]:
        items = [
            self.python_version(),
            self.git_available(),
            self.git_repository(),
            self.git_user(),
            self.config_schema(),
            self.database_connection(),
            self.prompt_resources(),
            self.security_rules(),
            self.ai_configuration(check_ai=check_ai),
            self.feishu_configuration(check_feishu=check_feishu),
            self.timezone(),
            self.encoding(),
            self.version(),
        ]
        return items

    def python_version(self) -> DiagnosticItem:
        version = ".".join(str(part) for part in sys.version_info[:3])
        status = DiagnosticStatus.PASS if sys.version_info >= (3, 11) else DiagnosticStatus.WARNING
        suggestion = None if status == DiagnosticStatus.PASS else "发布包声明 Python >=3.11；当前解释器仅用于本地兼容验证。"
        return DiagnosticItem(id="python", name="Python", status=status, message=f"Python {version}", suggestion=suggestion)

    def git_available(self) -> DiagnosticItem:
        if not shutil.which("git"):
            return DiagnosticItem(
                id="git",
                name="Git",
                status=DiagnosticStatus.FAIL,
                message="未找到 git 命令。",
                suggestion="请安装 Git 并确保它在 PATH 中。",
            )
        result = subprocess.run(["git", "--version"], check=False, capture_output=True, text=True)
        return DiagnosticItem(id="git", name="Git", status=DiagnosticStatus.PASS, message=result.stdout.strip())

    def git_repository(self) -> DiagnosticItem:
        repo = GitRepository(Path.cwd())
        if repo.is_repository():
            return DiagnosticItem(id="git_repo", name="Git 仓库", status=DiagnosticStatus.PASS, message="当前目录为 Git 仓库。")
        return DiagnosticItem(
            id="git_repo",
            name="Git 仓库",
            status=DiagnosticStatus.WARNING,
            message="当前目录不是 Git 仓库。",
            suggestion="进入 Git 项目目录后运行 GitPulse。",
        )

    def git_user(self) -> DiagnosticItem:
        repo = GitRepository(Path.cwd())
        if not repo.is_repository():
            return DiagnosticItem(id="git_user", name="Git 用户", status=DiagnosticStatus.SKIPPED, message="非 Git 仓库，已跳过。")
        info = repo.get_repository_info()
        if info.git_user_email:
            return DiagnosticItem(id="git_user", name="Git 用户", status=DiagnosticStatus.PASS, message=f"Git 邮箱：{info.git_user_email}")
        return DiagnosticItem(
            id="git_user",
            name="Git 用户",
            status=DiagnosticStatus.WARNING,
            message="Git 用户邮箱未配置。",
            suggestion="运行 git config user.email you@example.com。",
        )

    def config_schema(self) -> DiagnosticItem:
        return DiagnosticItem(id="config", name="配置 Schema", status=DiagnosticStatus.PASS, message="默认配置可解析。")

    def database_connection(self) -> DiagnosticItem:
        database = self.database or Database(self.config.storage.database_path)
        try:
            database.initialize()
            version = MigrationManager(database.engine).current_version()
        except Exception as exc:
            return DiagnosticItem(
                id="database",
                name="数据库",
                status=DiagnosticStatus.FAIL,
                message="数据库连接或迁移失败。",
                suggestion=str(exc)[:160],
            )
        finally:
            if self.database is None:
                database.dispose()
        status = DiagnosticStatus.PASS if version == CURRENT_SCHEMA_VERSION else DiagnosticStatus.WARNING
        return DiagnosticItem(
            id="database",
            name="数据库",
            status=status,
            message=f"数据库 Schema 版本：{version}/{CURRENT_SCHEMA_VERSION}",
        )

    def prompt_resources(self) -> DiagnosticItem:
        required = ["commit_system.txt", "commit_user.txt", "weekly_system.txt", "weekly_user.txt"]
        missing = [name for name in required if not files("gitpulse.prompts").joinpath(name).is_file()]
        if missing:
            return DiagnosticItem(id="prompts", name="Prompt 资源", status=DiagnosticStatus.FAIL, message=f"缺少：{', '.join(missing)}")
        return DiagnosticItem(id="prompts", name="Prompt 资源", status=DiagnosticStatus.PASS, message="Prompt 资源完整。")

    def security_rules(self) -> DiagnosticItem:
        rules = RuleRegistry(self.config.security).get_rules()
        return DiagnosticItem(id="security_rules", name="安全规则", status=DiagnosticStatus.PASS, message=f"已加载 {len(rules)} 条规则。")

    def ai_configuration(self, *, check_ai: bool) -> DiagnosticItem:
        env_name = self.config.ai.api_key_env
        if os.getenv(env_name):
            return DiagnosticItem(id="ai", name="AI 配置", status=DiagnosticStatus.PASS, message=f"已配置环境变量：{env_name}")
        status = DiagnosticStatus.WARNING if check_ai else DiagnosticStatus.SKIPPED
        return DiagnosticItem(
            id="ai",
            name="AI 配置",
            status=status,
            message=f"未配置 AI API Key 环境变量：{env_name}",
            suggestion="本地 mock 或规则降级功能仍可使用。",
        )

    def feishu_configuration(self, *, check_feishu: bool) -> DiagnosticItem:
        webhook = os.getenv(self.config.feishu.webhook_env)
        if not webhook:
            status = DiagnosticStatus.WARNING if check_feishu else DiagnosticStatus.SKIPPED
            return DiagnosticItem(id="feishu", name="飞书配置", status=status, message="未配置飞书机器人 Webhook。")
        try:
            FeishuWebhookValidator().validate(webhook)
        except Exception as exc:
            return DiagnosticItem(id="feishu", name="飞书配置", status=DiagnosticStatus.FAIL, message=str(exc))
        return DiagnosticItem(id="feishu", name="飞书配置", status=DiagnosticStatus.PASS, message="飞书 Webhook 基础校验通过。")

    def timezone(self) -> DiagnosticItem:
        return DiagnosticItem(id="timezone", name="时区", status=DiagnosticStatus.PASS, message=self.config.weekly.timezone)

    def encoding(self) -> DiagnosticItem:
        return DiagnosticItem(id="encoding", name="系统编码", status=DiagnosticStatus.PASS, message=locale.getpreferredencoding(False))

    def version(self) -> DiagnosticItem:
        return DiagnosticItem(id="version", name="版本", status=DiagnosticStatus.PASS, message=f"GitPulse {get_version()}")
