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

智能周报功能验证请在 Web 控制台中完成：启动 `gitplus web`，进入“智能周报助手”，选择来源后生成、保存、确认并导出周报。
