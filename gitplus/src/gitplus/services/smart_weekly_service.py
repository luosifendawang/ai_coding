"""Business workflow for the new smart weekly assistant."""

from __future__ import annotations

import json
import re
import uuid
from collections import defaultdict
from datetime import date, datetime, timezone
from typing import Callable, cast

from sqlalchemy import select
from sqlalchemy.orm import Session

from gitplus.ai.provider import LLMProvider
from gitplus.config import AIConfig
from gitplus.models.ai import AIMessage, AIRequest
from gitplus.models.smart_weekly import (
    SmartWeeklyDraft,
    SmartWeeklySection,
    SmartWeeklySource,
)
from gitplus.storage.database import Database
from gitplus.storage.orm_models import WeeklyReportORM


class SmartWeeklyService:
    """Generate evidence-backed reports without depending on the removed UI."""

    def __init__(
        self,
        database: Database,
        history_query: Callable[..., dict[str, object]],
        provider_factory: Callable[[], tuple[LLMProvider, AIConfig]],
        repository_id: Callable[[], str],
    ) -> None:
        self.database = database
        self.history_query = history_query
        self.provider_factory = provider_factory
        self.repository_id = repository_id

    def sources(self, date_from: date, date_to: date) -> list[SmartWeeklySource]:
        result = self.history_query(
            date_from=date_from,
            date_to=date_to,
            record_types=None,
            repository=None,
            tag=None,
            commit_type=None,
            keyword=None,
            author=None,
            page=1,
            page_size=100,
        )
        raw_items = cast(list[dict[str, object]], result["items"])
        seen_commits: set[str] = set()
        sources: list[SmartWeeklySource] = []
        # Prefer confirmed CommitRecord over the corresponding raw Git commit.
        for item in raw_items:
            commit_hash = str(item.get("commit_hash") or "")
            if item["record_type"] == "commit_record" and commit_hash:
                seen_commits.add(commit_hash)
        for item in raw_items:
            commit_hash = str(item.get("commit_hash") or "")
            if item["record_type"] == "git_commit" and commit_hash in seen_commits:
                continue
            sources.append(
                SmartWeeklySource(
                    id=f"{item['record_type']}:{item['id']}",
                    kind=str(item["record_type"]),
                    occurred_at=str(item["occurred_at"]),
                    title=str(item["title"]),
                    summary=str(item.get("summary") or ""),
                    repository=str(item["repository"]),
                    source_ref=commit_hash or None,
                )
            )
        return sources

    def generate(
        self,
        date_from: date,
        date_to: date,
        selected_ids: list[str],
        *,
        use_ai: bool,
        extra_context: str,
    ) -> SmartWeeklyDraft:
        available = self.sources(date_from, date_to)
        selected = [item for item in available if item.id in selected_ids]
        if not selected:
            raise ValueError("所选周期内没有可用于生成周报的工作记录。")
        if use_ai:
            try:
                return self._generate_ai(selected, date_from, date_to, extra_context)
            except Exception as exc:  # noqa: BLE001 - provider failures fall back locally
                draft = self._generate_rules(
                    selected, date_from, date_to, extra_context
                )
                draft.warnings.append(f"AI 生成失败，已使用本地规则生成：{exc}")
                return draft
        return self._generate_rules(selected, date_from, date_to, extra_context)

    def refine(self, draft: SmartWeeklyDraft, instruction: str) -> SmartWeeklyDraft:
        provider, config = self.provider_factory()
        prompt = {
            "instruction": instruction,
            "report": draft.model_dump(mode="json"),
            "constraints": [
                "不得新增原报告中不存在的事实、数字或 source_ids",
                "保持 date_from、date_to 和 source_ids 不变",
                "输出完整 JSON 对象",
            ],
        }
        response = provider.generate(
            self._request(config, "你是周报编辑助手，只做有依据的改写。", prompt)
        )
        refined = self._parse_ai(
            response.content,
            draft.date_from,
            draft.date_to,
            draft.source_ids,
            provider.name,
        )
        refined.warnings = draft.warnings
        return refined

    def save(self, draft: SmartWeeklyDraft) -> str:
        report_id = f"smart_weekly_{uuid.uuid4().hex}"
        session = self.database.create_session()
        try:
            session.add(
                WeeklyReportORM(
                    id=report_id,
                    repository_id=self.repository_id(),
                    date_from=draft.date_from.isoformat(),
                    date_to=draft.date_to.isoformat(),
                    title=draft.title,
                    content_markdown=draft.markdown,
                    content_json=draft.model_dump_json(),
                    source_json=json.dumps(draft.source_ids, ensure_ascii=False),
                    source_coverage=1.0,
                    generator=f"smart_assistant:{draft.generator}",
                    status="draft",
                    version=1,
                    confirmed_at=None,
                )
            )
            session.commit()
            return report_id
        finally:
            session.close()

    def list_reports(self, status: str | None = None) -> list[dict[str, object]]:
        session = self.database.create_session()
        try:
            query = select(WeeklyReportORM).where(
                WeeklyReportORM.repository_id == self.repository_id(),
                WeeklyReportORM.generator.like("smart_assistant:%"),
            )
            if status:
                query = query.where(WeeklyReportORM.status == status)
            rows = session.execute(
                query.order_by(WeeklyReportORM.updated_at.desc()).limit(200)
            ).scalars()
            return [self._report_summary(row) for row in rows]
        finally:
            session.close()

    def get_report(self, report_id: str) -> dict[str, object]:
        session = self.database.create_session()
        try:
            report = self._owned_report(session, report_id)
            result = self._report_summary(report)
            result.update(
                {
                    "markdown": report.content_markdown,
                    "source_ids": json.loads(report.source_json or "[]"),
                    "content": json.loads(report.content_json or "{}"),
                }
            )
            return result
        finally:
            session.close()

    def update_report(
        self, report_id: str, title: str, markdown: str, expected_version: int
    ) -> dict[str, object]:
        session = self.database.create_session()
        try:
            report = self._owned_report(session, report_id)
            if report.version != expected_version:
                raise ValueError("周报已被其他操作修改，请刷新后重试。")
            report.title = title.strip()
            report.content_markdown = markdown.strip() + "\n"
            report.version += 1
            if report.status == "confirmed":
                report.status = "draft"
                report.confirmed_at = None
            session.commit()
            return self._report_summary(report)
        finally:
            session.close()

    def set_status(self, report_id: str, status: str) -> dict[str, object]:
        if status not in {"draft", "confirmed"}:
            raise ValueError("不支持的周报状态。")
        session = self.database.create_session()
        try:
            report = self._owned_report(session, report_id)
            report.status = status
            report.confirmed_at = (
                datetime.now(timezone.utc) if status == "confirmed" else None
            )
            report.version += 1
            session.commit()
            return self._report_summary(report)
        finally:
            session.close()

    def delete_report(self, report_id: str) -> None:
        session = self.database.create_session()
        try:
            report = self._owned_report(session, report_id)
            session.delete(report)
            session.commit()
        finally:
            session.close()

    def _owned_report(self, session: Session, report_id: str) -> WeeklyReportORM:
        report = session.get(WeeklyReportORM, report_id)
        if (
            report is None
            or report.repository_id != self.repository_id()
            or not report.generator.startswith("smart_assistant:")
        ):
            raise LookupError("未找到智能周报。")
        return report

    def _report_summary(self, report: WeeklyReportORM) -> dict[str, object]:
        return {
            "id": report.id,
            "title": report.title,
            "date_from": report.date_from,
            "date_to": report.date_to,
            "status": report.status,
            "version": report.version,
            "generator": report.generator.removeprefix("smart_assistant:"),
            "source_count": len(json.loads(report.source_json or "[]")),
            "created_at": report.created_at.isoformat(),
            "updated_at": report.updated_at.isoformat(),
            "confirmed_at": report.confirmed_at.isoformat()
            if report.confirmed_at
            else None,
        }

    def _generate_rules(
        self,
        sources: list[SmartWeeklySource],
        date_from: date,
        date_to: date,
        extra: str,
    ) -> SmartWeeklyDraft:
        buckets: dict[str, list[SmartWeeklySource]] = defaultdict(list)
        for source in sources:
            text = f"{source.title} {source.summary}".lower()
            if re.search(r"test|测试|质量|覆盖率|lint|refactor", text):
                buckets["quality"].append(source)
            elif re.search(r"risk|风险|阻塞|失败|异常|问题|bug|fix|修复", text):
                buckets["risks"].append(source)
            else:
                buckets["completed"].append(source)
        sections = [
            self._section("completed", "本周完成", buckets["completed"]),
            self._section("quality", "质量与改进", buckets["quality"]),
            self._section("risks", "问题与风险", buckets["risks"]),
            SmartWeeklySection(
                key="next_week",
                title="下周计划",
                items=[extra] if extra else [],
                source_ids=[],
            ),
        ]
        overview = f"本周围绕 {len(sources)} 项可追溯工作记录完成开发与改进。"
        return self._draft(
            date_from, date_to, overview, sections, sources, "rule_based"
        )

    def _generate_ai(
        self,
        sources: list[SmartWeeklySource],
        date_from: date,
        date_to: date,
        extra: str,
    ) -> SmartWeeklyDraft:
        provider, config = self.provider_factory()
        payload = {
            "date_from": date_from.isoformat(),
            "date_to": date_to.isoformat(),
            "sources": [item.model_dump() for item in sources],
            "extra_context": extra,
            "required_sections": ["completed", "quality", "risks", "next_week"],
        }
        system = (
            "你是智能周报助手。仅根据 sources 生成简洁中文周报。"
            "输出 JSON，字段为 title、overview、sections；sections 每项包含 key、title、items、source_ids。"
            'items 必须是字符串数组，例如 ["完成登录重构"]，不得把事项输出为对象。'
            "完成事项必须引用真实 source id；不得编造数字、结果或计划。"
        )
        response = provider.generate(self._request(config, system, payload))
        return self._parse_ai(
            response.content,
            date_from,
            date_to,
            [item.id for item in sources],
            provider.name,
        )

    def _parse_ai(
        self,
        content: str,
        date_from: date,
        date_to: date,
        allowed_ids: list[str],
        generator: str,
    ) -> SmartWeeklyDraft:
        data = json.loads(content)
        sections = [
            self._normalize_ai_section(item) for item in data.get("sections", [])
        ]
        if {section.key for section in sections} != {
            "completed",
            "quality",
            "risks",
            "next_week",
        }:
            raise ValueError("AI 返回的周报分区不完整。")
        allowed = set(allowed_ids)
        for section in sections:
            if not set(section.source_ids).issubset(allowed):
                raise ValueError("AI 返回了不存在的来源引用。")
        sources = [
            SmartWeeklySource(id=item, kind="", occurred_at="", title="", repository="")
            for item in allowed_ids
        ]
        return self._draft(
            date_from,
            date_to,
            str(data.get("overview") or ""),
            sections,
            sources,
            generator,
            title=str(data.get("title") or ""),
        )

    def _normalize_ai_section(self, raw: object) -> SmartWeeklySection:
        """Accept strict output plus common structured-item variations from LLMs."""
        if not isinstance(raw, dict):
            raise TypeError("AI 返回了无效的周报分区。")
        normalized = dict(raw)
        item_texts: list[str] = []
        item_source_ids: list[str] = []
        raw_items = normalized.get("items", [])
        if not isinstance(raw_items, list):
            raise TypeError("AI 返回的事项列表格式无效。")
        for item in raw_items:
            if isinstance(item, str):
                item_texts.append(item)
                continue
            if not isinstance(item, dict):
                raise TypeError("AI 返回了无法识别的周报事项。")
            text = next(
                (
                    str(item[field]).strip()
                    for field in ("description", "content", "text", "title")
                    if item.get(field)
                ),
                "",
            )
            if not text:
                raise ValueError("AI 返回的结构化事项缺少文字内容。")
            item_texts.append(text)
            source_id = item.get("source_id")
            if source_id:
                item_source_ids.append(str(source_id))
            source_ids = item.get("source_ids", [])
            if isinstance(source_ids, list):
                item_source_ids.extend(str(value) for value in source_ids if value)
        section_source_ids = normalized.get("source_ids", [])
        if not isinstance(section_source_ids, list):
            section_source_ids = []
        normalized["items"] = item_texts
        normalized["source_ids"] = list(
            dict.fromkeys(
                [*(str(value) for value in section_source_ids), *item_source_ids]
            )
        )
        return SmartWeeklySection.model_validate(normalized)

    def _request(self, config: AIConfig, system: str, payload: object) -> AIRequest:
        return AIRequest(
            messages=[
                AIMessage(role="system", content=system),
                AIMessage(role="user", content=json.dumps(payload, ensure_ascii=False)),
            ],
            model=config.model,
            temperature=min(config.temperature, 0.3),
            top_p=config.top_p,
            max_output_tokens=config.max_output_tokens,
        )

    def _section(
        self, key: str, title: str, sources: list[SmartWeeklySource]
    ) -> SmartWeeklySection:
        return SmartWeeklySection(
            key=key,
            title=title,
            items=[self._item_text(item) for item in sources],
            source_ids=[item.id for item in sources],
        )  # type: ignore[arg-type]

    def _item_text(self, source: SmartWeeklySource) -> str:
        return (
            f"{source.title}：{source.summary}"
            if source.summary and source.summary != source.title
            else source.title
        )

    def _draft(
        self,
        date_from: date,
        date_to: date,
        overview: str,
        sections: list[SmartWeeklySection],
        sources: list[SmartWeeklySource],
        generator: str,
        title: str = "",
    ) -> SmartWeeklyDraft:
        report_title = (
            title or f"智能周报（{date_from:%Y-%m-%d} 至 {date_to:%Y-%m-%d}）"
        )
        lines = [f"# {report_title}", "", overview, ""]
        for section in sections:
            lines.extend([f"## {section.title}", ""])
            lines.extend([f"- {item}" for item in section.items] or ["- 暂无"])
            lines.append("")
        return SmartWeeklyDraft(
            title=report_title,
            date_from=date_from,
            date_to=date_to,
            overview=overview,
            sections=sections,
            source_ids=[item.id for item in sources],
            markdown="\n".join(lines).strip() + "\n",
            generator=generator,
        )
