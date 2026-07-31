# Data Management

GitPulse stores local data in SQLite.

```bash
gitpulse data info
gitpulse data backup
gitpulse data clear --yes
```

Backups include the SQLite database only. They do not include API keys, Feishu App Secrets, access tokens, shell environment variables, or Git repository source files.
