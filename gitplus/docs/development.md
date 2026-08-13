# Development

Install locally:

```bash
pip install -e ".[dev]"
```

Run checks:

```bash
gitplus --help
pytest
```

第二阶段 Git 能力验证：

```bash
gitplus check
pytest tests/unit/git
```

第三阶段安全能力验证：

```bash
gitplus check --format json
pytest tests/unit/security tests/integration/test_check_command.py
```

第四阶段 AI Commit 能力验证：

```bash
gitplus commit --provider mock
gitplus commit --json --provider mock
pytest tests/unit/ai tests/unit/test_commit_service.py tests/integration/test_commit_command.py
```

第五阶段存储能力验证：

```bash
gitplus init
gitplus worklog add --yes --type debug --title "排查问题"
gitplus worklog list
gitplus history
pytest tests/unit/storage tests/unit/services tests/integration/test_storage_cli.py
```

第六阶段周报能力验证：

```bash
gitplus weekly --current --no-ai
gitplus weekly --from 2026-07-27 --to 2026-08-02 --format json
pytest tests/unit/weekly tests/integration/test_weekly_cli.py
```

第七阶段飞书通知能力验证：

```bash
gitplus notify weekly <report-id> --preview
gitplus notify test-feishu --yes
pytest tests/unit/integrations tests/unit/notifications tests/unit/services/test_notification_service.py
pytest tests/integration/test_feishu_cli.py
```
