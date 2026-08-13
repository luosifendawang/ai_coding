"""Feishu weekly card builder."""

from __future__ import annotations

from datetime import datetime, timezone

from gitplus.config import FeishuConfig
from gitplus.models.weekly import WeeklyReport, WeeklyReportItem


class FeishuWeeklyCardBuilder:
    """Build static Feishu interactive cards for weekly reports."""

    max_elements = 24

    def build(self, report: WeeklyReport, config: FeishuConfig) -> dict[str, object]:
        template = "orange" if report.risks else config.card_template
        elements: list[dict[str, object]] = [
            {
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": (
                        f"**统计周期：** {report.date_range.date_from.isoformat()} "
                        f"至 {report.date_range.date_to.isoformat()}"
                    ),
                },
            },
            {"tag": "hr"},
        ]
        elements.extend(self._completed(report, config))
        elements.extend(self._section("问题排查与支持", report.debugging, config))
        elements.extend(self._section("测试与验证", report.testing, config))
        elements.extend(self._section("风险与待处理", report.risks, config))
        elements.extend(self._section("下周计划", report.next_week, config))
        footer = []
        if config.include_report_id:
            footer.append(f"报告 ID：{report.id}")
        if config.include_generated_at:
            footer.append(f"生成时间：{datetime.now(timezone.utc).isoformat()}")
        if config.include_generator_info:
            footer.append(f"生成器：{report.generator}")
        mentions = self._mentions(config, card=True)
        if mentions:
            footer.append(mentions)
        if footer:
            elements.extend([{"tag": "hr"}, self._markdown("\n".join(footer))])
        elements = elements[: self.max_elements]
        return {
            "config": {"wide_screen_mode": True},
            "header": {
                "title": {"tag": "plain_text", "content": "gitplus 开发周报"},
                "template": template,
            },
            "elements": elements or [self._markdown("暂无可发送内容")],
        }

    def _completed(self, report: WeeklyReport, config: FeishuConfig) -> list[dict[str, object]]:
        if not report.completed:
            return []
        chunks = ["**本周完成事项**"]
        for index, topic in enumerate(report.completed, start=1):
            chunks.append(f"{index}. {self._escape(topic.title)}")
            for item in topic.items:
                chunks.append(f"- {self._item(item, config)}")
        return [self._markdown("\n".join(chunks)), {"tag": "hr"}]

    def _section(
        self,
        title: str,
        items: list[WeeklyReportItem],
        config: FeishuConfig,
    ) -> list[dict[str, object]]:
        if not items:
            return []
        content = "\n".join([f"**{title}**", *[f"- {self._item(item, config)}" for item in items]])
        return [self._markdown(content), {"tag": "hr"}]

    def _item(self, item: WeeklyReportItem, config: FeishuConfig) -> str:
        content = self._escape(item.content)
        if config.include_sources and item.sources:
            sources = "、".join(source.label.split(":", 1)[-1][:8] for source in item.sources)
            content += f"（来源：{sources}）"
        return content

    def _mentions(self, config: FeishuConfig, *, card: bool) -> str:
        parts = []
        if config.mention_all:
            parts.append("<at id=all></at>" if card else '<at user_id="all">所有人</at>')
        for open_id in config.mention_open_ids:
            parts.append(f"<at id={open_id}></at>" if card else f'<at user_id="{open_id}"></at>')
        return "".join(parts)

    def _markdown(self, content: str) -> dict[str, object]:
        return {"tag": "div", "text": {"tag": "lark_md", "content": content[:3000]}}

    def _escape(self, value: str) -> str:
        return value.replace("<", "&lt;").replace(">", "&gt;").strip()
