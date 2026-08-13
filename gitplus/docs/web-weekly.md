# Web 周报管理中心

运行 `gitplus web --project /path/to/repository`，通过本地访问链接进入控制台，
然后打开“周报”。

## 预览与生成

周报页支持本周、上周和自定义周期。作者邮箱留空时使用
`git config --get user.email` 的有效配置，项目未配置时会自然回退到 Git 全局
邮箱。数据预览合并真实 Git Commit、确认后的 CommitRecord 和 Worklog，并显示
重复来源、模板记录和低信息记录。

生成前会执行以下清理：

- 关联相同 Commit Hash 的真实 Commit 与 CommitRecord，并保留两类来源。
- 在同一仓库和分类内合并标题完全相同的记录。
- 删除与标题重复的正文。
- 过滤 `init`、`test` 和预置英文模板等无意义记录。
- 不跨仓库合并仅仅标题相似的工作。

规则整理始终可用。选择 AI 整理时，输入会先经过本地敏感信息扫描和脱敏；
High 或 Critical 内容不会发送给远程模型。AI 超时、非法 JSON、来源校验失败或
其他 Provider 错误都会自动回退到规则整理，并在页面显示警告。

## 编辑与来源

编辑页支持修改周报和分组标题、工作项标题/描述/结果，调整顺序、移动分组、
删除和恢复工作项，以及新增用户补充项。手动新增内容的来源由服务端写为
`user_note`，客户端不能伪造 Commit、CommitRecord 或 Worklog 来源。

保存使用版本号进行乐观并发控制。版本不一致返回
`409 weekly_version_conflict`。修改已确认周报会重新进入 `draft`；中可信内容
需要明确确认，低可信内容不能进入正式周报，每个正式工作项必须有有效来源。

## API

```text
POST   /api/weekly/preview
POST   /api/weekly/generate
GET    /api/weekly
GET    /api/weekly/{id}
PUT    /api/weekly/{id}
DELETE /api/weekly/{id}
POST   /api/weekly/{id}/confirm
POST   /api/weekly/{id}/reopen
GET    /api/weekly/{id}/export
```

所有写接口要求有效 Session 和 CSRF。导出支持 Markdown、Text 和 JSON，文件名
由服务端按周报周期生成，不接受任意输出路径。已确认周报导出后状态变为
`exported`，草稿导出仍保持 `draft`；两者都不会被标记为已发送。
