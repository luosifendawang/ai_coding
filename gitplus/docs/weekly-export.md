# Weekly Export

Weekly reports can be rendered as Markdown, plain text, or JSON.

## Markdown

```bash
gitplus weekly --format markdown --output weekly.md
```

Markdown is the primary editable format. Sections are omitted when empty:

- 本周完成
- 问题排查
- 测试与验证
- 风险与阻塞
- 下周计划

Each item includes source labels when sources are available.

## Text

```bash
gitplus weekly --format text --output weekly.txt
```

Text output keeps the same content without Markdown heading markers.

## JSON

```bash
gitplus weekly --json
gitplus weekly --format json --output weekly.json
```

JSON exports the full `WeeklyReport` structure for automation or later editing.

## File Safety

Exporters write through a temporary file and then replace the target path. Existing output paths are protected by default at exporter level; the CLI intentionally overwrites explicit `--output` targets for repeated local generation.
