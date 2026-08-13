"""Privacy and secret masking."""

from __future__ import annotations

from collections import defaultdict

from gitplus.config import SecurityConfig
from gitplus.models.diff import DiffCollection
from gitplus.models.risk import MaskingResult, MaskMapping, SecurityFinding
from gitplus.security.rule_registry import SecurityRule


class PrivacyMasker:
    """Replace detected sensitive values with stable placeholders."""

    def __init__(self, config: SecurityConfig, rules: list[SecurityRule]) -> None:
        self.config = config
        self.rules = {rule.id: rule for rule in rules}
        self._private_mapping: dict[tuple[str, str], str] = {}
        self._counts_by_prefix: defaultdict[str, int] = defaultdict(int)

    def mask_text(self, text: str, findings: list[SecurityFinding]) -> MaskingResult:
        replacements: list[tuple[int, int, str, SecurityFinding]] = []
        for finding in findings:
            rule = self.rules.get(finding.rule_id)
            if not rule:
                continue
            raw_value = self._extract_value(text, finding)
            if not raw_value:
                continue
            placeholder = self._placeholder(rule.replacement, raw_value)
            start = self._offset(text, finding)
            replacements.append((start, start + len(raw_value), placeholder, finding))

        masked_text = text
        for start, end, placeholder, _finding in sorted(replacements, key=lambda item: item[0], reverse=True):
            masked_text = masked_text[:start] + placeholder + masked_text[end:]

        mapping_counts: dict[str, MaskMapping] = {}
        for _start, _end, placeholder, finding in replacements:
            if placeholder in mapping_counts:
                mapping_counts[placeholder].occurrence_count += 1
            else:
                mapping_counts[placeholder] = MaskMapping(
                    placeholder=placeholder,
                    category=finding.category.value,
                    masked_value=placeholder,
                )
        return MaskingResult(
            original_length=len(text),
            masked_length=len(masked_text),
            masked_text=masked_text,
            mappings=list(mapping_counts.values()),
        )

    def mask_collection(self, collection: DiffCollection, findings: list[SecurityFinding]) -> MaskingResult:
        chunks: list[str] = []
        mappings: list[MaskMapping] = []
        for file in collection.files:
            file_findings = [finding for finding in findings if finding.file_path == file.new_path]
            masked = self.mask_text(file.patch, file_findings)
            chunks.append(masked.masked_text)
            mappings.extend(masked.mappings)
        return MaskingResult(
            original_length=sum(len(file.patch) for file in collection.files),
            masked_length=sum(len(chunk) for chunk in chunks),
            masked_text="\n".join(chunks),
            mappings=mappings,
        )

    def _extract_value(self, text: str, finding: SecurityFinding) -> str:
        if finding.line_number is None or finding.column_start is None or finding.column_end is None:
            return ""
        lines = text.splitlines()
        if finding.line_number - 1 >= len(lines):
            return ""
        line = lines[finding.line_number - 1]
        return line[finding.column_start - 1 : finding.column_end - 1]

    def _offset(self, text: str, finding: SecurityFinding) -> int:
        lines = text.splitlines(keepends=True)
        return sum(len(line) for line in lines[: (finding.line_number or 1) - 1]) + (finding.column_start or 1) - 1

    def _placeholder(self, replacement: str, raw_value: str) -> str:
        if replacement == "<PRIVATE_KEY>":
            return replacement
        key = (replacement, raw_value)
        if key not in self._private_mapping:
            self._counts_by_prefix[replacement] += 1
            base = replacement.strip("<>")
            self._private_mapping[key] = f"<{base}_{self._counts_by_prefix[replacement]}>"
        return self._private_mapping[key]

