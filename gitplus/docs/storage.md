# 本地存储

gitplus 使用 SQLite 保存仓库信息、提交记录、工作日志、风险摘要、智能周报和操作审计数据。所有数据默认存放在本机，不依赖远程数据库。

## 文件位置

默认数据库：

```text
~/.gitplus/data.db
```

可在全局配置中调整：

```yaml
storage:
  database: ~/.gitplus/data.db
  auto_initialize: true
  store_raw_diff: false
```

## 初始化与迁移

执行 `gitplus init` 或首次访问需要数据库的功能时，系统会创建目录、初始化表结构并执行顺序迁移。迁移记录保存在 `migrations` 表；当前兼容的 Schema 版本为 `6`。

## 核心表

- `repositories`：本地仓库信息。
- `commit_records`：用户确认的提交记录。
- `worklogs`：结构化工作日志。
- `risks`：脱敏后的安全风险摘要。
- `weekly_reports`：智能周报草稿与已确认版本。
- `operation_audits`：关键 Web 操作审计。
- `migrations`：数据库迁移记录。

## 隐私与备份

默认不保存完整原始 Diff。风险记录仅保存脱敏值，例如 `<API_KEY_1>`，不保存原始凭证。可使用以下命令维护数据：

```bash
gitplus data info
gitplus data backup
gitplus data clear --yes
```

`data clear` 会清理本地数据，执行前应先使用 `data backup` 创建备份。测试使用临时 SQLite 文件，不会访问用户默认数据库。
