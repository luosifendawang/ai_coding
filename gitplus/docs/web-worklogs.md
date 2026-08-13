# Web 工作日志

运行 `gitplus web --project /path/to/repository`，通过本地访问链接进入控制台，
然后打开“工作日志”。

页面支持新增、查看、编辑、复制和删除 Worklog。记录包含发生时间、类型、标题、
描述、结果、耗时、标签、关联 Commit 与来源。删除需要浏览器二次确认，后端还会
验证 `confirmed=true`；所有新增、编辑和删除请求都需要有效 Session 与 CSRF。

列表支持日期、类型、标签、仓库和关键字筛选，`page_size` 最大为 100。Web
控制台固定绑定启动时指定的仓库，客户端不能通过查询参数切换到其他仓库路径。

Worklog 写入前会复用现有敏感信息扫描。检测到高风险或严重敏感内容时拒绝保存。
数据库升级到 schema v4 时只为 `worklogs` 增加发生时间、关联 Commit 和来源列，
不会重建已有表。

API：

```text
GET    /api/worklogs
POST   /api/worklogs
GET    /api/worklogs/{id}
PUT    /api/worklogs/{id}
DELETE /api/worklogs/{id}?confirmed=true
```

