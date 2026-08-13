# Data Management

gitplus stores local data in SQLite.

```bash
gitplus data info
gitplus data backup
gitplus data clear --yes
```

Backups include the SQLite database only. They do not include API keys, Feishu App Secrets, access tokens, shell environment variables, or Git repository source files.
