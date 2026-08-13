"""Field-level configuration diff helpers."""

from __future__ import annotations

SECRET_PATHS = {
    "ai.api_key",
    "feishu.app_secret",
    "feishu.secret",
    "feishu.webhook",
}


class ConfigDiffService:
    """Produce safe field-level previews."""

    def flatten(self, value: dict[str, object], prefix: str = "") -> dict[str, object]:
        flattened: dict[str, object] = {}
        for key, item in value.items():
            path = f"{prefix}.{key}" if prefix else key
            if isinstance(item, dict):
                flattened.update(self.flatten(item, path))
            else:
                flattened[path] = item
        return flattened

    def compare(
        self,
        old: dict[str, object],
        new: dict[str, object],
        *,
        source: str,
    ) -> list[dict[str, object]]:
        old_flat = self.flatten(old)
        new_flat = self.flatten(new)
        changes: list[dict[str, object]] = []
        for path in sorted(set(old_flat) | set(new_flat)):
            before = old_flat.get(path)
            after = new_flat.get(path)
            if before == after:
                continue
            if path in SECRET_PATHS:
                before = "********" if before else "未配置"
                after = "********" if after else "已删除"
            changes.append(
                {"path": path, "old": before, "new": after, "source": source}
            )
        return changes
