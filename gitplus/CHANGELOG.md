# Changelog

## 0.1.0

### Added

- Git repository detection and Diff reading.
- Sensitive content scanning and privacy masking.
- AI Commit Message generation with mock and OpenAI-compatible providers.
- Multi-topic commit detection.
- Commit work records, Worklog management, and history queries.
- Source-backed weekly reports with Markdown, text, and JSON export.
- Feishu custom bot notification with preview, signing, audit records, and duplicate protection.
- Setup wizard, doctor diagnostics, data backup, and release checks.

### Security

- High risk sensitive content blocks remote model calls.
- API keys and Feishu credentials use environment variables.
- Final Feishu payload is scanned before sending.

### Limitations

- AI output still requires user review.
- gitplus does not execute Git commits or pushes.
- Team management, rankings, and performance evaluation are not implemented.
