"""Diagnostic checks for gitplus."""

from __future__ import annotations

import locale
import os
import shutil
import subprocess
import sys
from importlib.resources import files
from pathlib import Path

from gitplus.config import (
    GitPlusConfig,
    load_secret_value,
    user_config_path,
    user_secrets_path,
)
from gitplus.diagnostics.models import DiagnosticItem, DiagnosticStatus
from gitplus.git.repository import GitRepository
from gitplus.security.rule_registry import RuleRegistry
from gitplus.storage.database import Database
from gitplus.storage.migrations.manager import CURRENT_SCHEMA_VERSION, MigrationManager
from gitplus.version import get_version


class DiagnosticChecks:
    """Run local non-mutating environment checks."""

    def __init__(
        self, config: GitPlusConfig, *, database: Database | None = None
    ) -> None:
        self.config = config
        self.database = database

    def run(
        self, *, check_ai: bool = False, check_feishu: bool = False
    ) -> list[DiagnosticItem]:
        items = [
            self.python_version(),
            self.git_available(),
            self.git_repository(),
            self.git_user(),
            self.user_config(),
            self.project_config(),
            self.secret_permissions(),
            self.config_schema(),
            self.database_connection(),
            self.prompt_resources(),
            self.security_rules(),
            self.ai_configuration(check_ai=check_ai),
            self.feishu_configuration(check_feishu=check_feishu),
            self.web_port(),
            self.report_directory(),
            self.timezone(),
            self.encoding(),
            self.version(),
        ]
        return items

    def python_version(self) -> DiagnosticItem:
        version = ".".join(str(part) for part in sys.version_info[:3])
        status = (
            DiagnosticStatus.PASS
            if sys.version_info >= (3, 9)
            else DiagnosticStatus.WARNING
        )
        suggestion = (
            None
            if status == DiagnosticStatus.PASS
            else "发布包声明 Python >=3.9；当前解释器版本过低。"
        )
        return DiagnosticItem(
            id="python",
            name="Python",
            status=status,
            message=f"Python {version}",
            suggestion=suggestion,
        )

    def git_available(self) -> DiagnosticItem:
        if not shutil.which("git"):
            return DiagnosticItem(
                id="git",
                name="Git",
                status=DiagnosticStatus.FAIL,
                message="未找到 git 命令。",
                suggestion="请安装 Git 并确保它在 PATH 中。",
            )
        result = subprocess.run(
            ["git", "--version"], check=False, capture_output=True, text=True
        )
        return DiagnosticItem(
            id="git",
            name="Git",
            status=DiagnosticStatus.PASS,
            message=result.stdout.strip(),
        )

    def git_repository(self) -> DiagnosticItem:
        repo = GitRepository(Path.cwd())
        if repo.is_repository():
            return DiagnosticItem(
                id="git_repo",
                name="Git 仓库",
                status=DiagnosticStatus.PASS,
                message="当前目录为 Git 仓库。",
            )
        return DiagnosticItem(
            id="git_repo",
            name="Git 仓库",
            status=DiagnosticStatus.WARNING,
            message="当前目录不是 Git 仓库。",
            suggestion="进入 Git 项目目录后运行 gitplus。",
        )

    def git_user(self) -> DiagnosticItem:
        repo = GitRepository(Path.cwd())
        if not repo.is_repository():
            return DiagnosticItem(
                id="git_user",
                name="Git 用户",
                status=DiagnosticStatus.SKIPPED,
                message="非 Git 仓库，已跳过。",
            )
        info = repo.get_repository_info()
        if info.git_user_name and info.git_user_email:
            return DiagnosticItem(
                id="git_user",
                name="Git 用户",
                status=DiagnosticStatus.PASS,
                message=f"Git 用户：{info.git_user_name} <{info.git_user_email}>",
            )
        return DiagnosticItem(
            id="git_user",
            name="Git 用户",
            status=DiagnosticStatus.WARNING,
            message="Git 用户身份未完整配置。",
            suggestion=(
                '运行 git config --global user.name "你的名字" 和 '
                'git config --global user.email "你的邮箱"。'
            ),
        )

    def config_schema(self) -> DiagnosticItem:
        return DiagnosticItem(
            id="config",
            name="配置 Schema",
            status=DiagnosticStatus.PASS,
            message="默认配置可解析。",
        )

    def user_config(self) -> DiagnosticItem:
        path = user_config_path()
        return DiagnosticItem(
            id="user_config",
            name="用户级配置",
            status=DiagnosticStatus.PASS if path.exists() else DiagnosticStatus.WARNING,
            message=str(path) if path.exists() else f"未找到：{path}",
            suggestion=None if path.exists() else "可运行 gitplus setup --user 创建。",
        )

    def project_config(self) -> DiagnosticItem:
        path = Path.cwd() / ".gitplus.yml"
        return DiagnosticItem(
            id="project_config",
            name="项目级配置",
            status=DiagnosticStatus.PASS if path.exists() else DiagnosticStatus.SKIPPED,
            message=str(path) if path.exists() else "当前项目未配置 .gitplus.yml。",
        )

    def secret_permissions(self) -> DiagnosticItem:
        path = user_secrets_path()
        if not path.exists():
            return DiagnosticItem(
                id="secret_permissions",
                name="Secret 文件权限",
                status=DiagnosticStatus.SKIPPED,
                message=f"未找到：{path}",
            )
        mode = path.stat().st_mode & 0o777
        ok = mode == 0o600
        return DiagnosticItem(
            id="secret_permissions",
            name="Secret 文件权限",
            status=DiagnosticStatus.PASS if ok else DiagnosticStatus.WARNING,
            message=f"{path} 权限 {mode:o}",
            suggestion=None if ok else "建议执行 chmod 600 配置凭证文件。",
        )

    def database_connection(self) -> DiagnosticItem:
        database = self.database or Database(self.config.storage.database_path)
        try:
            database.initialize()
            version = MigrationManager(database.engine).current_version()
        except Exception as exc:  # noqa: BLE001 - storage adapters expose multiple errors
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
        status = (
            DiagnosticStatus.PASS
            if version == CURRENT_SCHEMA_VERSION
            else DiagnosticStatus.WARNING
        )
        return DiagnosticItem(
            id="database",
            name="数据库",
            status=status,
            message=f"数据库 Schema 版本：{version}/{CURRENT_SCHEMA_VERSION}",
        )

    def prompt_resources(self) -> DiagnosticItem:
        required = [
            "commit_system.txt",
            "commit_user.txt",
            "weekly_system.txt",
            "weekly_user.txt",
        ]
        missing = [
            name
            for name in required
            if not files("gitplus.prompts").joinpath(name).is_file()
        ]
        if missing:
            return DiagnosticItem(
                id="prompts",
                name="Prompt 资源",
                status=DiagnosticStatus.FAIL,
                message=f"缺少：{', '.join(missing)}",
            )
        return DiagnosticItem(
            id="prompts",
            name="Prompt 资源",
            status=DiagnosticStatus.PASS,
            message="Prompt 资源完整。",
        )

    def security_rules(self) -> DiagnosticItem:
        rules = RuleRegistry(self.config.security).get_rules()
        return DiagnosticItem(
            id="security_rules",
            name="安全规则",
            status=DiagnosticStatus.PASS,
            message=f"已加载 {len(rules)} 条规则。",
        )

    def ai_configuration(self, *, check_ai: bool) -> DiagnosticItem:
        env_name = self.config.ai.api_key_env
        if os.getenv(env_name):
            return DiagnosticItem(
                id="ai",
                name="AI 配置",
                status=DiagnosticStatus.PASS,
                message=f"已配置环境变量：{env_name}",
            )
        status = DiagnosticStatus.WARNING if check_ai else DiagnosticStatus.SKIPPED
        return DiagnosticItem(
            id="ai",
            name="AI 配置",
            status=status,
            message=f"未配置 AI API Key 环境变量：{env_name}",
            suggestion="本地 mock 或规则降级功能仍可使用。",
        )

    def feishu_configuration(self, *, check_feishu: bool) -> DiagnosticItem:
        if self.config.feishu.mode == "webhook":
            if self.config.feishu.webhook:
                return DiagnosticItem(
                    id="feishu",
                    name="飞书配置",
                    status=DiagnosticStatus.PASS,
                    message="飞书 Webhook 机器人已配置。",
                )
            status = DiagnosticStatus.WARNING if check_feishu else DiagnosticStatus.SKIPPED
            return DiagnosticItem(
                id="feishu",
                name="飞书配置",
                status=status,
                message="飞书 Webhook 机器人配置不完整：Webhook。",
            )
        app_id = self.config.feishu.app_id or os.getenv(self.config.feishu.app_id_env)
        app_secret = (
            self.config.feishu.app_secret
            or os.getenv(self.config.feishu.app_secret_env)
            or load_secret_value("feishu.app_secret")
        )
        receive_id = self.config.feishu.receive_id or os.getenv(
            self.config.feishu.receive_id_env
        )
        missing = [
            label
            for label, value in [
                ("App ID", app_id),
                ("App Secret", app_secret),
                ("Receive ID", receive_id),
            ]
            if not value
        ]
        if missing:
            status = (
                DiagnosticStatus.WARNING if check_feishu else DiagnosticStatus.SKIPPED
            )
            return DiagnosticItem(
                id="feishu",
                name="飞书配置",
                status=status,
                message=f"飞书应用机器人配置不完整：{', '.join(missing)}。",
            )
        return DiagnosticItem(
            id="feishu",
            name="飞书配置",
            status=DiagnosticStatus.PASS,
            message="飞书应用机器人凭证和接收目标已配置。",
        )

    def web_port(self) -> DiagnosticItem:
        return DiagnosticItem(
            id="web_port",
            name="Web 端口",
            status=DiagnosticStatus.PASS,
            message=f"127.0.0.1:{self.config.web.port}",
        )

    def report_directory(self) -> DiagnosticItem:
        path = Path(self.config.storage.report_dir).expanduser()
        writable = path.exists() and os.access(path, os.W_OK)
        if not path.exists():
            parent_writable = os.access(path.parent if path.parent else Path.cwd(), os.W_OK)
            return DiagnosticItem(
                id="report_dir",
                name="报告目录",
                status=DiagnosticStatus.PASS if parent_writable else DiagnosticStatus.WARNING,
                message=f"目录尚未创建：{path}",
                suggestion=None if parent_writable else "请检查报告目录父级权限。",
            )
        return DiagnosticItem(
            id="report_dir",
            name="报告目录",
            status=DiagnosticStatus.PASS if writable else DiagnosticStatus.WARNING,
            message=str(path),
            suggestion=None if writable else "请检查报告目录写权限。",
        )

    def timezone(self) -> DiagnosticItem:
        return DiagnosticItem(
            id="timezone",
            name="时区",
            status=DiagnosticStatus.PASS,
            message=self.config.weekly.timezone,
        )

    def encoding(self) -> DiagnosticItem:
        return DiagnosticItem(
            id="encoding",
            name="系统编码",
            status=DiagnosticStatus.PASS,
            message=locale.getpreferredencoding(False),
        )

    def version(self) -> DiagnosticItem:
        return DiagnosticItem(
            id="version",
            name="版本",
            status=DiagnosticStatus.PASS,
            message=f"gitplus {get_version()}",
        )
