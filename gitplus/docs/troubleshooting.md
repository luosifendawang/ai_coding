# Troubleshooting

- Not a Git repository: enter a Git project directory or run `git init`.
- Git missing: install Git and ensure `git --version` works.
- Git identity missing: configure `git config --global user.name "Your Name"` and `git config --global user.email you@example.com`. Repository-level values still take precedence when present.
- Empty staged diff: run `git add <file>` or use `gitplus commit --unstaged`.
- Diff too large: commit smaller changes or adjust diff limits.
- AI API key missing: set the configured environment variable, usually `GITPLUS_API_KEY`.
- AI timeout or invalid JSON: use `--provider mock` or retry with a lower temperature provider.
- Database locked: close other gitplus processes and retry.
- Database migration failure: back up the database, then run `gitplus doctor`.
- Report output denied: choose a writable output path.
