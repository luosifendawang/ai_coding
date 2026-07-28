"""JSON weekly report exporter."""

from __future__ import annotations

import json
from pathlib import Path

from gitpulse.exceptions import WeeklyExportError
from gitpulse.models.weekly import WeeklyReport


class JsonWeeklyExporter:
    """Render and write weekly reports as JSON."""

    def render(self, report: WeeklyReport) -> str:
        return json.dumps(report.model_dump(mode="json"), ensure_ascii=False, indent=2)

    def export(self, report: WeeklyReport, output_path: Path, *, overwrite: bool = False) -> Path:
        if output_path.exists() and not overwrite:
            raise WeeklyExportError(f"导出文件已存在：{output_path}")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = output_path.with_suffix(output_path.suffix + ".tmp")
        tmp_path.write_text(self.render(report), encoding="utf-8")
        tmp_path.replace(output_path)
        return output_path
