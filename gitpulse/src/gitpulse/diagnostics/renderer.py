"""Render diagnostic reports."""

from __future__ import annotations

from gitpulse.diagnostics.models import DiagnosticReport, DiagnosticStatus

SYMBOLS = {
    DiagnosticStatus.PASS: "✓",
    DiagnosticStatus.WARNING: "!",
    DiagnosticStatus.FAIL: "✗",
    DiagnosticStatus.SKIPPED: "-",
}


class DiagnosticRenderer:
    """Render reports for CLI output."""

    def render_text(self, report: DiagnosticReport) -> str:
        lines = ["GitPulse 环境检查", ""]
        for item in report.items:
            lines.append(f"{SYMBOLS[item.status]} {item.name}: {item.message}")
            if item.suggestion:
                lines.append(f"  建议：{item.suggestion}")
        lines.extend(["", "检查结果：", self._summary(report)])
        return "\n".join(lines)

    def _summary(self, report: DiagnosticReport) -> str:
        if report.status == DiagnosticStatus.FAIL:
            return "存在阻断性问题。"
        if report.status == DiagnosticStatus.WARNING:
            return "可运行，部分可选功能未配置。"
        return "环境检查通过。"
