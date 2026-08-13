# Web 工作历史

“工作历史”合并读取三种本地来源：

```text
真实 Git Commit
gitplus CommitRecord
Worklog
```

真实 Git 历史通过参数数组执行 `git log`，命令有超时且不使用 Shell。未指定作者
时，作者邮箱来自 `git config --get user.email`，因此项目配置缺失时会自然回退
到 Git 全局配置。

时间线支持日期范围、记录类型、仓库、标签、 Commit 类型和关键字筛选。统计展示
真实 Commit、确认记录、Worklog、记录耗时、仓库和标签；代码增删行仅作为单条
Commit 的事实信息展示，不用于评价工作表现。

CommitRecord 会展示分支、Subject、脱敏 Body、文件和行数统计、AI Provider、
Model、用户编辑标记及安全扫描摘要。API 不返回原始 Diff、API Key、
Authorization Header 或 Secret 配置。历史正文在输出前再次经过本地脱敏。

导出接口：

```text
GET /api/history/export?format=markdown
GET /api/history/export?format=json
GET /api/history/export?format=csv
```

导出沿用当前筛选条件，文件只包含整理后的历史字段。

