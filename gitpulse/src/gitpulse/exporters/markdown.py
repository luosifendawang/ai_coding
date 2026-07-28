"""Markdown weekly report exporter."""

from __future__ import annotations

from pathlib import Path

from gitpulse.exceptions import WeeklyExportError
from gitpulse.models.weekly import WeeklyReport, WeeklyReportItem


class MarkdownWeeklyExporter:
    """Render and write weekly reports as editable Markdown."""

    def render(self, report: WeeklyReport, *, include_sources: bool = True) -> str:
        lines = [
            f"# {self._escape(report.title)}",
            "",
            f"- 周期：{report.date_range.date_from.isoformat()} 至 {report.date_range.date_to.isoformat()}",
            f"- 状态：{report.status}",
            f"- 来源覆盖率：{report.source_coverage:.0%}",
            "",
        ]
        if report.completed:
            lines.extend(["## 本周完成", ""])
            for topic in report.completed:
                lines.extend([f"### {self._escape(topic.title)}", ""])
                if topic.summary:
                    lines.extend([self._escape(topic.summary), ""])
                lines.extend(self._items(topic.items, include_sources=include_sources))
        if report.debugging:
            lines.extend(["## 问题排查", ""])
            lines.extend(self._items(report.debugging, include_sources=include_sources))
        if report.testing:
            lines.extend(["## 测试与验证", ""])
            lines.extend(self._items(report.testing, include_sources=include_sources))
        if report.risks:
            lines.extend(["## 风险与阻塞", ""])
            lines.extend(self._items(report.risks, include_sources=include_sources))
        if report.next_week:
            lines.extend(["## 下周计划", ""])
            lines.extend(self._items(report.next_week, include_sources=include_sources))
        return "\n".join(lines).rstrip() + "\n"

    def export(self, report: WeeklyReport, output_path: Path, *, overwrite: bool = False) -> Path:
        if output_path.exists() and not overwrite:
            raise WeeklyExportError(f"导出文件已存在：{output_path}")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = output_path.with_suffix(output_path.suffix + ".tmp")
        tmp_path.write_text(self.render(report), encoding="utf-8")
        tmp_path.replace(output_path)
        return output_path

    def _items(self, items: list[WeeklyReportItem], *, include_sources: bool) -> list[str]:
        lines: list[str] = []
        for item in items:
            suffix = ""
            if include_sources and item.sources:
                suffix = f"（来源：{', '.join(source.label for source in item.sources)}）"
            lines.append(f"- {self._escape(item.content)}{suffix}")
        lines.append("")
        return lines

    def _escape(self, value: str) -> str:
        return value.replace("<", "&lt;").replace(">", "&gt;").strip()
