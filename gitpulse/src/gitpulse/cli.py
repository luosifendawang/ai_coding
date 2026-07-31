"""Typer command line interface for GitPulse."""

from __future__ import annotations

import json
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Annotated, Any

import typer
from rich.console import Console
from rich.table import Table

from gitpulse import __version__
from gitpulse.config import default_config, load_config
from gitpulse.diagnostics.doctor import DoctorService
from gitpulse.diagnostics.renderer import DiagnosticRenderer
from gitpulse.exceptions import GitPulseError
from gitpulse.logging import configure_logging
from gitpulse.models.history import CommitHistoryFilters
from gitpulse.models.risk import RiskLevel
from gitpulse.models.storage import RepositoryRecord
from gitpulse.models.worklog import WorklogCreate, WorklogFilters, WorklogUpdate
from gitpulse.release.readiness import ReleaseReadinessChecker
from gitpulse.release.report import ReleaseReportRenderer
from gitpulse.services.check_service import CheckResult, CheckService
from gitpulse.services.commit_record_service import (
    CommitConfirmationRequest,
    CommitRecordService,
)
from gitpulse.services.commit_service import CommitService
from gitpulse.services.data_service import DataService
from gitpulse.services.history_service import HistoryService
from gitpulse.services.notification_service import NotificationService
from gitpulse.services.storage_service import StorageService
from gitpulse.services.weekly_service import WeeklyGenerateRequest, WeeklyService
from gitpulse.services.worklog_service import WorklogService
from gitpulse.setup.wizard import SetupWizard
from gitpulse.storage.orm_models import utc_now

console = Console()

app = typer.Typer(
    name="gitpulse",
    help="GitPulse - AI 开发工作成果助手",
    no_args_is_help=True,
)
worklog_app = typer.Typer(help="管理手动工作记录", no_args_is_help=True)
notify_app = typer.Typer(help="发送周报到飞书", no_args_is_help=True)
history_app = typer.Typer(help="查看历史记录", no_args_is_help=False)
data_app = typer.Typer(help="管理本地数据", no_args_is_help=True)
app.add_typer(worklog_app, name="worklog")
app.add_typer(notify_app, name="notify")
app.add_typer(history_app, name="history")
app.add_typer(data_app, name="data")


def version_callback(value: bool) -> None:
    if value:
        console.print(f"GitPulse {__version__}")
        raise typer.Exit()


@app.callback()
def _main_callback(
    version: Annotated[
        bool,
        typer.Option("--version", callback=version_callback, help="显示版本号。"),
    ] = False,
    debug: Annotated[bool, typer.Option("--debug", help="显示调试日志。")] = False,
) -> None:
    """GitPulse - AI 开发工作成果助手."""
    configure_logging(debug=debug)


def main() -> None:
    """Console script entry point."""
    app()


@app.command()
def init() -> None:
    """初始化项目。"""
    from gitpulse.git.repository import GitRepository

    console.print("正在初始化 GitPulse...")
    repository = GitRepository(Path.cwd())
    info = repository.get_repository_info()
    db = _database_from_default_config()
    current = utc_now()
    with db.session_scope() as session:
        from gitpulse.storage.repositories import RepositoryRepository

        saved = RepositoryRepository(session).upsert(
            RepositoryRecord(
                id=f"repo_{abs(hash(str(info.root_path))) & 0xffffffff:x}",
                name=info.name,
                root_path=str(info.root_path),
                remote_url=info.remote_url,
                created_at=current,
                updated_at=current,
                last_seen_at=current,
            )
        )
    console.print(f"✓ 检测到 Git 仓库：{info.name}")
    console.print(f"✓ 初始化数据库：{db.database_path}")
    console.print(f"✓ 保存仓库信息：{saved.id}")
    console.print("初始化完成。")


@app.command()
def web(
    port: Annotated[int | None, typer.Option("--port", help="本地 Web 服务端口。")] = None,
    open_browser: Annotated[
        bool,
        typer.Option("--open/--no-open", help="启动后自动打开浏览器。"),
    ] = True,
    project: Annotated[
        Path,
        typer.Option("--project", help="要管理的本地项目目录。"),
    ] = Path("."),
    debug: Annotated[bool, typer.Option("--debug", help="启用 Web 调试日志。")] = False,
) -> None:
    """启动仅监听本机的 Web 控制台。"""
    from gitpulse.commands.web import run_web

    run_web(
        project=project,
        port=port,
        open_browser=open_browser,
        debug=debug,
        console=console,
    )


@app.command()
def commit(
    staged: Annotated[bool, typer.Option("--staged", help="读取暂存区 diff。")] = True,
    unstaged: Annotated[bool, typer.Option("--unstaged", help="读取未暂存 diff。")] = False,
    lang: Annotated[str, typer.Option("--lang", help="Commit Message 语言。")] = "zh-CN",
    format_: Annotated[
        str,
        typer.Option("--format", help="Commit Message 格式。"),
    ] = "conventional",
    no_body: Annotated[bool, typer.Option("--no-body", help="不生成 body。")] = False,
    copy: Annotated[bool, typer.Option("--copy", help="复制结果到剪贴板。")] = False,
    context: Annotated[str | None, typer.Option("--context", help="用户补充修改背景。")] = None,
    json_output: Annotated[bool, typer.Option("--json", help="输出 JSON。")] = False,
    provider: Annotated[str | None, typer.Option("--provider", help="覆盖 AI Provider：mock 或 openai-compatible。")] = None,
    show_evidence: Annotated[bool, typer.Option("--show-evidence", help="显示生成依据。")] = False,
    show_security: Annotated[bool, typer.Option("--show-security", help="显示安全扫描结果。")] = False,
    save: Annotated[bool, typer.Option("--save", help="保存为 GitPulse 工作记录。")] = False,
    no_save: Annotated[bool, typer.Option("--no-save", help="不保存工作记录。")] = False,
) -> None:
    """生成 Commit Message。"""
    if provider and provider not in {"mock", "openai-compatible"}:
        raise typer.BadParameter("--provider 仅支持 mock 或 openai-compatible")
    cfg = load_config()
    commit_config = cfg.commit.model_copy(
        update={"language": lang, "format": format_, "include_body": not no_body}
    )
    ai_update: dict[str, Any] = {"provider": provider}
    if provider == "mock":
        ai_update["is_local"] = True
    ai_config = cfg.ai.model_copy(update={key: value for key, value in ai_update.items() if value is not None})
    result = CommitService(ai_config=ai_config, commit_config=commit_config).generate_commit_message(
        source="unstaged" if unstaged else "staged",
        user_context=context,
    )
    if json_output:
        typer.echo(json.dumps(_commit_result_to_json(result), ensure_ascii=False, indent=2))
    else:
        _print_commit_result(result, show_evidence=show_evidence, show_security=show_security, no_body=no_body)
    if save and not no_save and result.generation:
        candidate = result.generation.candidates["standard"]
        db = _database_from_default_config()
        saved = CommitRecordService(db).save_confirmed_record(
            CommitConfirmationRequest(
                result=result,
                selected_candidate="standard",
                final_subject=candidate.subject,
                final_body=[] if no_body else candidate.body,
            )
        )
        console.print(f"已保存工作记录：{saved.id}")
        console.print("GitPulse 未执行 git commit。")
    if copy:
        console.print("复制到剪贴板功能尚未启用，已在终端展示 Commit Message。")
    if result.diff.stats.files_changed == 0 or not result.generation:
        raise typer.Exit(code=1)


@app.command()
def check(
    staged: Annotated[bool, typer.Option("--staged", help="扫描暂存区 Diff。")] = True,
    unstaged: Annotated[bool, typer.Option("--unstaged", help="扫描未暂存 Diff。")] = False,
    output_format: Annotated[str, typer.Option("--format", help="输出格式：table 或 json。")] = "table",
    show_low_risk: Annotated[bool, typer.Option("--show-low-risk", help="显示低风险结果。")] = False,
    no_mask_preview: Annotated[bool, typer.Option("--no-mask-preview", help="不显示脱敏预览。")] = False,
) -> None:
    """检查当前提交风险。"""
    if output_format not in {"table", "json"}:
        raise typer.BadParameter("--format 仅支持 table 或 json")
    result = CheckService().run(staged=not unstaged if staged else False)
    if output_format == "json":
        typer.echo(json.dumps(_check_result_to_json(result), ensure_ascii=False, indent=2))
    else:
        _print_check_table(result, show_low_risk=show_low_risk, show_mask_preview=not no_mask_preview)
    if not result.security.scan_completed:
        raise typer.Exit(code=2)
    if result.security.block_remote_model:
        raise typer.Exit(code=1)


@app.command()
def weekly(
    current: Annotated[bool, typer.Option("--current", help="生成本周周报。")] = False,
    last_week: Annotated[bool, typer.Option("--last-week", help="生成上周周报。")] = False,
    date_from: Annotated[str | None, typer.Option("--from", help="开始日期 YYYY-MM-DD。")] = None,
    date_to: Annotated[str | None, typer.Option("--to", help="结束日期 YYYY-MM-DD。")] = None,
    include_uncommitted: Annotated[
        bool,
        typer.Option("--include-uncommitted", help="包含用户确认的未提交变更。"),
    ] = False,
    format_: Annotated[str, typer.Option("--format", help="导出格式：markdown、text 或 json。")] = "markdown",
    output: Annotated[Path | None, typer.Option("--output", help="导出文件路径。")] = None,
    author: Annotated[list[str] | None, typer.Option("--author", help="Git 作者邮箱，可多次传入。")] = None,
    risk: Annotated[list[str] | None, typer.Option("--risk", help="补充风险，可多次传入。")] = None,
    plan: Annotated[list[str] | None, typer.Option("--plan", help="补充下周计划，可多次传入。")] = None,
    no_ai: Annotated[bool, typer.Option("--no-ai", help="只使用本地规则生成。")] = False,
    save_draft: Annotated[bool, typer.Option("--save-draft", help="保存周报草稿。")] = False,
    confirm: Annotated[bool, typer.Option("--confirm", help="保存为已确认正式周报。")] = False,
    json_output: Annotated[bool, typer.Option("--json", help="输出 JSON。")] = False,
    send_feishu: Annotated[bool, typer.Option("--send-feishu", help="确认并发送到飞书。")] = False,
) -> None:
    """生成开发周报。"""
    if send_feishu and not confirm:
        raise typer.BadParameter("--send-feishu 只能与 --confirm 一起使用，draft 周报不能发送。")
    if format_ not in {"markdown", "text", "json"}:
        raise typer.BadParameter("--format 仅支持 markdown、text 或 json")
    if last_week and (current or date_from or date_to):
        raise typer.BadParameter("--last-week 不能与 --current 或自定义日期同时使用")
    if (date_from and not date_to) or (date_to and not date_from):
        raise typer.BadParameter("--from 和 --to 需要同时提供")
    range_kind = "custom" if date_from or date_to else ("last" if last_week else "current")
    cfg = load_config()
    service = WeeklyService(_database_from_default_config(), config=cfg.weekly)
    report = service.generate(
        WeeklyGenerateRequest(
            range_kind=range_kind,  # type: ignore[arg-type]
            date_from=_parse_date(date_from),
            date_to=_parse_date(date_to),
            authors=author or [],
            risks=risk or [],
            plans=plan or [],
            include_uncommitted=include_uncommitted,
            confirm=confirm,
        ),
        use_ai=not no_ai,
    )
    if save_draft or confirm or send_feishu:
        report = service.save(report)
    send_result = None
    if send_feishu:
        send_result = NotificationService(_database_from_default_config(), feishu_config=cfg.feishu).send_weekly(
            report.id,
            confirmed=True,
            force=False,
        )
    if output:
        service.export(report, format_, output, overwrite=True)
    if json_output or format_ == "json":
        typer.echo(service.render(report, "json"))
    elif output:
        console.print(f"周报已导出：{output}")
        if save_draft or confirm:
            console.print(f"周报已保存：{report.id}")
        if send_result:
            console.print(f"飞书通知状态：{send_result.record.status}")
    else:
        typer.echo(service.render(report, format_))
        if send_result:
            console.print(f"飞书通知状态：{send_result.record.status}")


@app.command("config")
def config_command() -> None:
    """管理配置。"""
    config = load_config()
    console.print(config.model_dump())


@app.command()
def doctor(
    json_output: Annotated[bool, typer.Option("--json", help="输出 JSON。")] = False,
    check_ai: Annotated[bool, typer.Option("--check-ai", help="检查 AI 环境变量配置。")] = False,
    check_feishu: Annotated[bool, typer.Option("--check-feishu", help="检查飞书应用机器人配置。")] = False,
) -> None:
    """检查 GitPulse 运行环境。"""
    report = DoctorService(load_config()).run(
        check_ai=check_ai, check_feishu=check_feishu
    )
    if json_output:
        typer.echo(report.model_dump_json())
    else:
        console.print(DiagnosticRenderer().render_text(report))


@app.command()
def setup(
    user: Annotated[bool, typer.Option("--user", help="写入用户级配置。")] = True,
    project: Annotated[bool, typer.Option("--project", help="写入当前项目 .gitpulse.yml。")] = False,
    yes: Annotated[bool, typer.Option("--yes", help="确认写入配置。")] = False,
    preview: Annotated[bool, typer.Option("--preview", help="只显示配置预览。")] = False,
) -> None:
    """配置用户级或项目级 GitPulse 环境。"""
    scope = "project" if project else "user"
    result = SetupWizard().run(scope=scope, write=False)
    console.print("欢迎使用 GitPulse")
    console.print(f"配置目标：{result.path}")
    console.print(result.preview)
    if preview:
        return
    if not yes and not typer.confirm("确认写入上述配置？", default=False):
        console.print("已取消。")
        raise typer.Exit(code=1)
    written = SetupWizard().run(scope=scope, write=True)
    console.print(f"配置已写入：{written.path}")


@app.command("release-check")
def release_check(
    output: Annotated[Path | None, typer.Option("--output", help="写入发布检查报告。")] = None,
    json_output: Annotated[bool, typer.Option("--json", help="输出 JSON。")] = False,
) -> None:
    """执行发布就绪检查。"""
    readiness = ReleaseReadinessChecker(Path.cwd()).run()
    if json_output:
        typer.echo(json.dumps({"version": readiness.version, "ready": readiness.ready, "checks": [check.__dict__ for check in readiness.checks]}, ensure_ascii=False, indent=2))
    else:
        text = ReleaseReportRenderer().render(readiness)
        if output:
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(text, encoding="utf-8")
            console.print(f"发布检查报告已写入：{output}")
        else:
            console.print(text)


def _check_result_to_json(result: CheckResult) -> dict[str, object]:
    security = result.security
    return {
        "scan_completed": security.scan_completed,
        "passed": security.passed,
        "block_remote_model": security.block_remote_model,
        "source": result.source,
        "repository": {
            "name": result.repository.name,
            "branch": result.repository.current_branch,
            "head": result.repository.head_commit,
        },
        "diff": {
            "files": result.diff.stats.files_changed,
            "insertions": result.diff.stats.insertions,
            "deletions": result.diff.stats.deletions,
            "ignored_files": [item.model_dump() for item in result.diff.ignored_files],
            "truncated_files": result.diff.truncated_files,
        },
        "summary": security.summary.model_dump(),
        "findings": [
            finding.model_dump(mode="json", exclude={"location"}) for finding in security.findings
        ],
        "warnings": security.warnings,
        "errors": security.errors,
    }


def _commit_result_to_json(result) -> dict[str, object]:
    generation = result.generation
    return {
        "repository": {
            "name": result.repository.name,
            "branch": result.repository.current_branch,
        },
        "diff": {
            "files_changed": result.diff.stats.files_changed,
            "insertions": result.diff.stats.insertions,
            "deletions": result.diff.stats.deletions,
            "truncated": bool(result.diff.truncated_files),
        },
        "security": {
            "scan_completed": result.security.scan_completed,
            "block_remote_model": result.security.block_remote_model,
            "high": result.security.summary.high,
            "critical": result.security.summary.critical,
        },
        "ai_called": result.ai_called,
        "provider": result.provider_name,
        "warnings": result.warnings,
        "generation": generation.model_dump(mode="json") if generation else None,
    }


def _format_candidate(subject: str, body: list[str], *, no_body: bool = False) -> str:
    if no_body or not body:
        return subject
    return subject + "\n\n" + "\n".join(f"- {item}" for item in body)


def _print_commit_result(result, *, show_evidence: bool, show_security: bool, no_body: bool) -> None:
    console.print("[bold]GitPulse Commit Message[/bold]")
    console.print(f"仓库：{result.repository.name}")
    console.print(f"分支：{result.repository.current_branch or '(detached HEAD)'}")
    console.print(f"修改文件：{result.diff.stats.files_changed}")
    console.print(f"新增行：{result.diff.stats.insertions}")
    console.print(f"删除行：{result.diff.stats.deletions}")
    if result.diff.stats.files_changed == 0:
        console.print("当前暂存区没有代码变更。\n\n请先执行：\n\ngit add <file>\n\n或者使用：\n\ngitpulse commit --unstaged")
        return
    if show_security:
        summary = result.security.summary
        console.print(f"安全扫描：严重 {summary.critical}，高风险 {summary.high}，中风险 {summary.medium}，低风险 {summary.low}")
    for warning in result.warnings:
        console.print(f"[yellow]{warning}[/yellow]")
    if not result.generation:
        if result.security.block_remote_model:
            console.print("检测到高风险敏感信息，已阻止远程 AI 调用。")
        return
    generation = result.generation
    console.print("\n[bold]AI 分析结果[/bold]")
    console.print(f"主要目的：{generation.primary_purpose}")
    console.print(f"类型：{generation.type}")
    console.print(f"范围：{generation.scope or '-'}")
    console.print(f"可信度：{generation.confidence}")
    table = Table(title="推荐 Commit Message")
    table.add_column("版本")
    table.add_column("内容")
    for key, label in [("concise", "简洁版"), ("standard", "标准版"), ("detailed", "详细版")]:
        candidate = generation.candidates[key]
        table.add_row(label, _format_candidate(candidate.subject, candidate.body, no_body=no_body))
    console.print(table)
    for warning in generation.validation_warnings:
        console.print(f"[yellow]提示：{warning}[/yellow]")
    for confirmation in generation.needs_confirmation:
        console.print(f"[yellow]待确认：{confirmation}[/yellow]")
    if generation.should_split:
        console.print(f"检测到当前变更可能包含多个独立主题，可信度：{generation.split_confidence:.0%}")
        console.print("GitPulse 只提供拆分建议，不会自动修改暂存区。")
    if show_evidence and generation.evidence:
        evidence_table = Table(title="生成依据")
        evidence_table.add_column("文件")
        evidence_table.add_column("依据")
        for evidence in generation.evidence:
            evidence_table.add_row(evidence.file, evidence.reason)
        console.print(evidence_table)


def _print_check_table(
    result: CheckResult,
    *,
    show_low_risk: bool,
    show_mask_preview: bool,
) -> None:
    console.print("[bold]GitPulse 安全检查[/bold]")
    repo = result.repository
    console.print(f"仓库：{repo.name}")
    console.print(f"分支：{repo.current_branch or '(detached HEAD)'}")
    console.print(f"来源：{'暂存区' if result.source == 'staged' else '未暂存区'}")

    if result.diff.stats.files_changed == 0:
        console.print("当前 Diff 为空，没有需要扫描的内容。")

    summary = result.security.summary
    table = Table(title="扫描汇总")
    table.add_column("项目")
    table.add_column("值")
    table.add_row("扫描文件", str(summary.files_scanned))
    table.add_row("发现风险", str(summary.total_findings))
    table.add_row("严重", str(summary.critical))
    table.add_row("高风险", str(summary.high))
    table.add_row("中风险", str(summary.medium))
    table.add_row("低风险", str(summary.low))
    table.add_row("远程模型调用", "已阻止" if result.security.block_remote_model else "允许")
    console.print(table)

    findings = result.security.findings if show_low_risk else [
        finding for finding in result.security.findings if finding.level != RiskLevel.LOW
    ]
    if findings:
        finding_table = Table(title="风险明细")
        finding_table.add_column("等级")
        finding_table.add_column("规则")
        finding_table.add_column("文件")
        finding_table.add_column("Diff 行")
        finding_table.add_column("内容")
        finding_table.add_column("建议")
        for finding in findings[:30]:
            finding_table.add_row(
                finding.level.value,
                finding.rule_name,
                finding.file_path or "-",
                str(finding.line_number or "-"),
                finding.masked_value or "-",
                finding.suggestion or "-",
            )
        console.print(finding_table)

    for warning in result.security.warnings:
        console.print(f"[yellow]警告：{warning}[/yellow]")
    for error in result.security.errors:
        console.print(f"[red]错误：{error}[/red]")
    if show_mask_preview and result.security.sanitized_diff and result.security.findings:
        console.print("脱敏预览已生成，可供后续本地流程使用。")


def _database_from_default_config():
    return StorageService(default_config().storage).database()


def _parse_date(value: str | None) -> date | None:
    return date.fromisoformat(value) if value else None


@worklog_app.command("add")
def worklog_add(
    work_type: Annotated[str, typer.Option("--type", help="Worklog 类型。")] = "other",
    title: Annotated[str | None, typer.Option("--title", help="标题。")] = None,
    work_date: Annotated[str | None, typer.Option("--date", help="日期 YYYY-MM-DD。")] = None,
    description: Annotated[str | None, typer.Option("--description", help="详细说明。")] = None,
    result: Annotated[str | None, typer.Option("--result", help="处理结果。")] = None,
    duration: Annotated[int | None, typer.Option("--duration", help="耗时分钟。")] = None,
    tag: Annotated[list[str] | None, typer.Option("--tag", help="标签，可多次传入。")] = None,
    yes: Annotated[bool, typer.Option("--yes", help="跳过保存确认。")] = False,
    json_output: Annotated[bool, typer.Option("--json", help="输出 JSON。")] = False,
) -> None:
    """新增工作记录。"""
    if not title:
        raise typer.BadParameter("非交互模式需要提供 --title")
    if not yes and not typer.confirm("是否保存工作记录？", default=False):
        console.print("已取消。")
        raise typer.Exit(code=1)
    created = WorklogService(_database_from_default_config()).create(
        WorklogCreate(
            work_date=_parse_date(work_date) or datetime.now(timezone.utc).date(),
            work_type=work_type,  # type: ignore[arg-type]
            title=title,
            description=description,
            result=result,
            duration_minutes=duration,
            tags=tag or [],
        )
    )
    if json_output:
        typer.echo(created.model_dump_json())
    else:
        console.print(f"工作记录已保存。\n\nID：\n{created.id}")


@worklog_app.command("list")
def worklog_list(
    date_from: Annotated[str | None, typer.Option("--from", help="开始日期 YYYY-MM-DD。")] = None,
    date_to: Annotated[str | None, typer.Option("--to", help="结束日期 YYYY-MM-DD。")] = None,
    work_type: Annotated[str | None, typer.Option("--type", help="Worklog 类型。")] = None,
    tag: Annotated[list[str] | None, typer.Option("--tag", help="标签。")] = None,
    limit: Annotated[int, typer.Option("--limit", help="限制数量。")] = 100,
    json_output: Annotated[bool, typer.Option("--json", help="输出 JSON。")] = False,
) -> None:
    """查看工作记录。"""
    items = WorklogService(_database_from_default_config()).list(
        WorklogFilters(
            date_from=_parse_date(date_from),
            date_to=_parse_date(date_to),
            work_types=[work_type] if work_type else None,
            tags=tag,
            limit=limit,
        )
    )
    if json_output:
        typer.echo(json.dumps([item.model_dump(mode="json") for item in items], ensure_ascii=False, indent=2))
        return
    if not items:
        console.print("暂无工作记录。")
        return
    table = Table(title="Worklog")
    table.add_column("ID")
    table.add_column("日期")
    table.add_column("类型")
    table.add_column("标题")
    table.add_column("耗时")
    for item in items:
        table.add_row(item.id, item.work_date.isoformat(), item.work_type, item.title, str(item.duration_minutes or "-"))
    console.print(table)


@worklog_app.command("show")
def worklog_show(record_id: str, json_output: Annotated[bool, typer.Option("--json", help="输出 JSON。")] = False) -> None:
    """查看单条工作记录。"""
    item = WorklogService(_database_from_default_config()).get(record_id)
    if json_output:
        typer.echo(item.model_dump_json())
        return
    console.print(f"工作记录\n\nID：{item.id}\n日期：{item.work_date}\n类型：{item.work_type}\n标题：{item.title}")
    if item.description:
        console.print(f"\n详细说明：\n{item.description}")
    if item.result:
        console.print(f"\n处理结果：\n{item.result}")


@worklog_app.command("edit")
def worklog_edit(
    record_id: str,
    title: Annotated[str | None, typer.Option("--title", help="新的标题。")] = None,
    result: Annotated[str | None, typer.Option("--result", help="新的结果。")] = None,
    duration: Annotated[int | None, typer.Option("--duration", help="新的耗时。")] = None,
    yes: Annotated[bool, typer.Option("--yes", help="跳过确认。")] = False,
) -> None:
    """编辑工作记录。"""
    if not yes and not typer.confirm("是否保存修改？", default=False):
        console.print("已取消。")
        raise typer.Exit(code=1)
    changes: dict[str, Any] = {}
    if title is not None:
        changes["title"] = title
    if result is not None:
        changes["result"] = result
    if duration is not None:
        changes["duration_minutes"] = duration
    updated = WorklogService(_database_from_default_config()).update(
        record_id,
        WorklogUpdate(**changes),
    )
    console.print(f"工作记录已更新：{updated.id}")


@worklog_app.command("delete")
def worklog_delete(record_id: str, yes: Annotated[bool, typer.Option("--yes", help="确认删除。")] = False) -> None:
    """删除工作记录。"""
    service = WorklogService(_database_from_default_config())
    item = service.get(record_id)
    if not yes and not typer.confirm(f"即将删除工作记录：{item.title}\n是否继续？", default=False):
        console.print("已取消。")
        raise typer.Exit(code=1)
    service.delete(record_id)
    console.print(f"工作记录已删除：{record_id}")


@history_app.callback(invoke_without_command=True)
def history_default(ctx: typer.Context) -> None:
    """查看历史记录。"""
    if ctx.invoked_subcommand is None:
        history_list()


@history_app.command("list")
def history_list(
    search: Annotated[str | None, typer.Option("--search", help="关键词。")] = None,
    commit_type: Annotated[str | None, typer.Option("--type", help="Commit 类型。")] = None,
    confidence: Annotated[str | None, typer.Option("--confidence", help="可信度。")] = None,
    limit: Annotated[int, typer.Option("--limit", help="限制数量。")] = 100,
    json_output: Annotated[bool, typer.Option("--json", help="输出 JSON。")] = False,
) -> None:
    """列出 Commit 工作记录。"""
    items = HistoryService(_database_from_default_config()).list_commit_records(
        CommitHistoryFilters(search=search, commit_type=commit_type, confidence=confidence, limit=limit)
    )
    if json_output:
        typer.echo(json.dumps([item.model_dump(mode="json") for item in items], ensure_ascii=False, indent=2))
        return
    if not items:
        console.print("暂无历史记录。")
        return
    table = Table(title="Commit 历史")
    table.add_column("ID")
    table.add_column("类型")
    table.add_column("Scope")
    table.add_column("Subject")
    for item in items:
        table.add_row(item.id, item.commit_type or "-", item.scope or "-", item.subject)
    console.print(table)


@history_app.command("show")
def history_show(record_id: str, json_output: Annotated[bool, typer.Option("--json", help="输出 JSON。")] = False) -> None:
    """查看 Commit 工作记录详情。"""
    item = HistoryService(_database_from_default_config()).get_commit_record(record_id)
    if json_output:
        typer.echo(item.model_dump_json())
        return
    console.print(f"Commit 工作记录\n\nID：{item.id}\n类型：{item.commit_type}\nScope：{item.scope or '-'}\n\n{item.subject}")


@data_app.command("info")
def data_info(json_output: Annotated[bool, typer.Option("--json", help="输出 JSON。")] = False) -> None:
    """查看本地数据概况。"""
    info = DataService(_database_from_default_config()).info()
    payload = {
        "database_path": str(info.database_path),
        "database_size_bytes": info.database_size_bytes,
        "schema_version": info.schema_version,
        "counts": info.counts,
    }
    if json_output:
        typer.echo(json.dumps(payload, ensure_ascii=False, indent=2))
        return
    table = Table(title="GitPulse 数据")
    table.add_column("项目")
    table.add_column("值")
    table.add_row("数据库", str(info.database_path))
    table.add_row("大小", str(info.database_size_bytes))
    table.add_row("Schema", str(info.schema_version))
    for name, count in info.counts.items():
        table.add_row(name, str(count))
    console.print(table)


@data_app.command("backup")
def data_backup(output_dir: Annotated[Path | None, typer.Option("--output-dir", help="备份目录。")] = None) -> None:
    """备份本地 SQLite 数据库。"""
    path = DataService(_database_from_default_config()).backup(output_dir)
    console.print(f"备份已创建：{path}")


@data_app.command("clear")
def data_clear(
    yes: Annotated[bool, typer.Option("--yes", help="确认清理。")] = False,
    no_backup: Annotated[bool, typer.Option("--no-backup", help="清理前不创建备份。")] = False,
) -> None:
    """清理本地 GitPulse 数据。"""
    if not yes and not typer.confirm("将清理 GitPulse 本地数据库记录，是否继续？", default=False):
        console.print("已取消。")
        raise typer.Exit(code=1)
    backup = DataService(_database_from_default_config()).clear(create_backup=not no_backup)
    console.print("本地数据已清理。")
    if backup:
        console.print(f"清理前备份：{backup}")


@notify_app.command("weekly")
def notify_weekly(
    report_id: Annotated[str, typer.Argument(help="已确认周报 ID。")],
    yes: Annotated[bool, typer.Option("--yes", help="确认发送。")] = False,
    force: Annotated[bool, typer.Option("--force", help="允许重复内容再次发送。")] = False,
    preview_only: Annotated[bool, typer.Option("--preview", help="只显示发送预览。")] = False,
    json_output: Annotated[bool, typer.Option("--json", help="输出 JSON。")] = False,
) -> None:
    """发送周报到飞书。"""
    cfg = load_config()
    service = NotificationService(_database_from_default_config(), feishu_config=cfg.feishu)
    if preview_only:
        payload, preview = service.preview_weekly(report_id)
        if json_output:
            typer.echo(json.dumps(payload.model_dump(mode="json"), ensure_ascii=False, indent=2))
        else:
            console.print(preview)
        return
    payload, preview = service.preview_weekly(report_id)
    if not yes:
        console.print(preview)
        if not typer.confirm("确认发送到飞书？", default=False):
            console.print("已取消。")
            raise typer.Exit(code=1)
    result = service.send_weekly(report_id, confirmed=True, force=force)
    if json_output:
        typer.echo(json.dumps(result.record.model_dump(mode="json"), ensure_ascii=False, indent=2))
    else:
        console.print(f"飞书通知状态：{result.record.status}")


@notify_app.command("test-feishu")
def notify_test_feishu(
    yes: Annotated[bool, typer.Option("--yes", help="确认发送测试消息。")] = False,
    json_output: Annotated[bool, typer.Option("--json", help="输出 JSON。")] = False,
) -> None:
    """测试飞书机器人连接。"""
    if not yes and not typer.confirm("确认发送飞书测试消息？", default=False):
        console.print("已取消。")
        raise typer.Exit(code=1)
    response = NotificationService(
        _database_from_default_config(),
        feishu_config=load_config().feishu,
    ).test_feishu_connection(confirmed=True)
    if json_output:
        typer.echo(response.model_dump_json())
    else:
        console.print("飞书连接测试完成。")


def run() -> None:
    """Run the Typer application with friendly business errors."""
    try:
        app()
    except GitPulseError as exc:
        console.print(f"[red]错误：{exc}[/red]")
        raise SystemExit(1) from None


if __name__ == "__main__":
    run()
