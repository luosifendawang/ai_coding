# Weekly Data Model

Weekly report generation uses explicit input, draft, and persisted report models.

## Inputs

- `WeeklyDateRange`: date range, timezone, and display label.
- `WeeklyCommitInput`: Git log commit evidence.
- `CommitRecord`: user confirmed commit work records stored in SQLite.
- `WeeklyWorklogInput`: manual worklogs.
- `WeeklyUncommittedInput`: optional user confirmed uncommitted work evidence.
- `WeeklyUserNote`: user supplied risks, plans, or other notes.

## Normalized Items

`WeeklyRawItem` is the shared internal shape used by clustering and fallback generation. It contains:

- category hint: `completed`, `debugging`, or `testing`
- repository and scope
- title, description, result, files
- source references

Commit subjects using Conventional Commit syntax provide commit type and scope. Worklogs map `debug` and `support` to debugging, `test` to testing, and other types to completed work.

## Draft And Report

`WeeklyReportDraft` is editable and may contain items that still need confirmation.

`WeeklyReport` is persisted and exported. It contains rendered Markdown plus the structured JSON payload, status, generator name, source coverage, and confirmation time when applicable.

## Storage

Weekly reports are stored in `weekly_reports` with:

- date range
- title and Markdown content
- structured JSON content
- source labels
- source coverage
- generator and status
- version and optional parent report ID
