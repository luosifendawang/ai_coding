"""Plain text weekly report exporter."""

from __future__ import annotations

from pathlib import Path

from gitpulse.exceptions import WeeklyExportError
from gitpulse.models.weekly import WeeklyReport


class TextWeeklyExporter:
    """Render and write weekly reports as plain text."""

    def render(self, report: WeeklyReport, *, include_sources: bool = True) -> str:
        from gitpulse.exporters.markdown import MarkdownWeeklyExporter

        markdown = MarkdownWeeklyExporter().render(report, include_sources=include_sources)
        text = markdown.replace("# ", "").replace("## ", "").replace("### ", "")
        return text

    def export(self, report: WeeklyReport, output_path: Path, *, overwrite: bool = False) -> Path:
        if output_path.exists() and not overwrite:
            raise WeeklyExportError(f"导出文件已存在：{output_path}")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = output_path.with_suffix(output_path.suffix + ".tmp")
        tmp_path.write_text(self.render(report), encoding="utf-8")
        tmp_path.replace(output_path)
        return output_path
