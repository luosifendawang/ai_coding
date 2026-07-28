"""Release report rendering."""

from __future__ import annotations

from gitpulse.release.readiness import ReleaseReadiness


class ReleaseReportRenderer:
    """Render release readiness summaries."""

    def render(self, readiness: ReleaseReadiness) -> str:
        lines = [f"# GitPulse {readiness.version} 发布检查", ""]
        for check in readiness.checks:
            mark = "PASS" if check.passed else "FAIL"
            lines.append(f"- {mark} {check.name}: {check.message}")
        lines.extend(["", f"结论：{'Ready' if readiness.ready else 'Ready with limitations'}"])
        return "\n".join(lines) + "\n"
