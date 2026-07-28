# Troubleshooting

- Not a Git repository: enter a Git project directory or run `git init`.
- Git missing: install Git and ensure `git --version` works.
- Git email missing: run `git config user.email you@example.com`.
- Empty staged diff: run `git add <file>` or use `gitpulse commit --unstaged`.
- Diff too large: commit smaller changes or adjust diff limits.
- AI API key missing: set the configured environment variable, usually `GITPULSE_API_KEY`.
- AI timeout or invalid JSON: use `--provider mock` or retry with a lower temperature provider.
- Database locked: close other GitPulse processes and retry.
- Database migration failure: back up the database, then run `gitpulse doctor`.
- Report output denied: choose a writable output path.
- Feishu signature error: check `GITPULSE_FEISHU_SECRET` and system time.
- Feishu rate limit: wait before retrying.
- Duplicate send blocked: inspect notification history and use `--force --yes` only when appropriate.
- Unknown notification state: check the Feishu group before retrying.
