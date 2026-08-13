# Storage

gitplus 使用本地 SQLite 保存仓库、Commit 工作记录、Worklog、风险摘要、周报草稿/正式周报和通知审计记录。

## 文件位置

默认数据库：

```text
~/.gitplus/data.db
```

可以通过配置修改：

```yaml
storage:
  database: ~/.gitplus/data.db
  auto_initialize: true
  store_raw_diff: false
```

## 初始化

```bash
gitplus init
```

初始化会创建数据库目录、执行初始迁移、启用 SQLite 外键约束，并保存当前仓库信息。

## Schema Version

当前使用自定义顺序迁移，迁移记录保存在 `migrations` 表。当前版本为 `1`。

## 表结构

主要表：

- `repositories`
- `commit_records`
- `worklogs`
- `risks`
- `weekly_reports`
- `notification_records`
- `migrations`

## 事务

多表写入通过 Unit of Work 统一提交。Commit 工作记录和风险记录会在同一事务中写入，周报保存通过 `WeeklyReportRepository` 持久化结构化 JSON、Markdown 和来源标签。飞书发送通过 `NotificationRepository` 保存内容指纹、发送状态、响应摘要和错误摘要，不保存 App Secret、访问令牌或完整消息体。

## 隐私

默认不保存完整原始 Diff。风险记录只保存脱敏值，例如 `<API_KEY_1>`，不得保存原始 Secret。

## 备份

SQLite 适合个人本地使用。数据库文件仍需要用户自行备份。

## 测试隔离

测试使用临时 SQLite 文件，不访问 `~/.gitplus/data.db`。
