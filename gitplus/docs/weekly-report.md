# Weekly Report

gitplus weekly report generation turns local Git commits, confirmed CommitRecords, Worklogs, and user supplied notes into an editable developer weekly report.

## Command

```bash
gitplus weekly --current --no-ai
gitplus weekly --last-week --format markdown
gitplus weekly --from 2026-07-27 --to 2026-08-02 --author you@example.com
gitplus weekly --risk "发布前继续观察兼容性" --plan "补充飞书机器人发送"
gitplus weekly --output weekly.md --save-draft
gitplus weekly --confirm --json
```

## Flow

1. Resolve the weekly date range.
2. Read current repository commits for configured or supplied Git emails.
3. Read confirmed CommitRecords from SQLite.
4. Read Worklogs within the date range.
5. Merge user supplied risks and next week plans.
6. Normalize all records into weekly raw items.
7. Deduplicate exact repeated work items.
8. Cluster completed work by repository scope or first directory.
9. Generate a structured draft with the AI generator or local rule fallback.
10. Validate every formal item against explicit sources.
11. Render Markdown, text, or JSON.
12. Optionally persist the draft or confirmed report.

## AI And Fallback

`gitplus weekly` is safe to run without network access. If no AI generator is configured, or `--no-ai` is used, gitplus uses the deterministic rule-based generator.

The AI generator is schema-first: it must return `WeeklyReportDraft` JSON and may only use input sources. Unsupported metrics, performance claims, and generic praise are rejected by validation.

## Current Boundaries

This stage does not send Feishu messages, export PDF or Word, create a web editor, evaluate code volume, rank people, or generate team reports.
