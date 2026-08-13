"""Feishu text notification builder."""

from __future__ import annotations

import re

from gitplus.config import FeishuConfig
from gitplus.models.weekly import WeeklyReport, WeeklyReportItem


class FeishuTextBuilder:
    """Build readable plain text weekly report notifications."""

    def build(self, report: WeeklyReport, config: FeishuConfig) -> str:
        lines = [
            "gitplus 开发周报",
            "",
            f"统计周期：{report.date_range.date_from.isoformat()} 至 {report.date_range.date_to.isoformat()}",
            "",
        ]
        if report.completed:
            lines.extend(["一、本周完成事项", ""])
            for index, topic in enumerate(report.completed, start=1):
                lines.append(f"{index}. {self._clean(topic.title)}")
                for item in topic.items:
                    lines.append(f"- {self._item(item, config)}")
                lines.append("")
        lines.extend(self._section("二、问题排查与支持", report.debugging, config))
        lines.extend(self._section("三、测试与验证", report.testing, config))
        lines.extend(self._section("四、风险与待处理", report.risks, config))
        lines.extend(self._section("五、下周计划", report.next_week, config))
        if config.include_report_id:
            lines.extend([f"报告 ID：{report.id}", ""])
        if config.mention_all:
            lines.append('<at user_id="all">所有人</at>')
        for open_id in config.mention_open_ids:
            lines.append(f'<at user_id="{open_id}"></at>')
        return "\n".join(lines).strip() + "\n"

    def _section(self, title: str, items: list[WeeklyReportItem], config: FeishuConfig) -> list[str]:
        if not items:
            return []
        lines = [title, ""]
        lines.extend(f"- {self._item(item, config)}" for item in items)
        lines.append("")
        return lines

    def _item(self, item: WeeklyReportItem, config: FeishuConfig) -> str:
        content = self._clean(item.content)
        if config.include_sources and item.sources:
            sources = "、".join(source.label.split(":", 1)[-1][:8] for source in item.sources)
            content += f"（来源：{sources}）"
        return content

    def _clean(self, value: str) -> str:
        return re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]+", " ", value).strip()
