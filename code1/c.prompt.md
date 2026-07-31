# GitPulse Web 控制台第三阶段：Worklog 与工作历史

继续开发现有 GitPulse 项目。

当前已经完成：

* Web 系统配置中心
* Git 仓库状态与 Diff
* 文件暂存与取消暂存
* 安全扫描
* AI Commit Message
* Web 确认执行 Git Commit

本阶段只开发：

```text
Worklog 管理
Commit 历史
工作成果查询
```

不要重新初始化项目，不要重写现有 CLI、数据库模型和 Service。Web API 必须复用现有 Worklog、CommitRecord 和数据库能力。

## 一、目标

用户可以在 Web 页面中：

1. 新增 Worklog
2. 编辑 Worklog
3. 删除 Worklog
4. 查看 Worklog 详情
5. 查看 GitPulse 生成和保存的 CommitRecord
6. 查看真实 Git Commit 历史
7. 按日期、类型、标签和关键字筛选
8. 查看某段时间内的工作统计
9. 导出工作记录
10. 为后续周报生成准备数据

## 二、页面

新增：

```text
/worklogs
/history
```

导航增加：

```text
Git 工作台
Worklog
工作历史
系统配置
```

## 三、Worklog 页面

字段至少包括：

* 日期和时间
* 类型
* 标题
* 工作内容
* 最终结果
* 耗时
* 标签
* 关联仓库
* 关联 Commit
* 来源
* 创建时间
* 更新时间

Worklog 类型可以包括：

```text
development
debug
test
review
meeting
research
document
support
other
```

页面功能：

* 新增
* 编辑
* 删除
* 查看详情
* 复制
* 搜索
* 筛选
* 分页

删除必须二次确认。

## 四、API

实现：

```http
GET    /api/worklogs
POST   /api/worklogs
GET    /api/worklogs/{id}
PUT    /api/worklogs/{id}
DELETE /api/worklogs/{id}
```

查询参数支持：

```text
date_from
date_to
type
tag
repository
keyword
page
page_size
```

所有写接口必须验证：

* Session
* CSRF
* 字段长度
* 日期格式
* 耗时范围
* Worklog 是否存在

## 五、工作历史页面

工作历史页面合并展示：

```text
真实 Git Commit
GitPulse CommitRecord
Worklog
```

统一时间轴示例：

```text
2026-07-29

10:30  Commit
feat(web): 增加 Git 工作台

11:20  Worklog
完成 Web 暂存接口测试

14:00  Debug
修复 AI JSON 响应解析问题
```

支持筛选：

* 时间范围
* 记录类型
* 仓库
* 标签
* Commit 类型
* 关键字

## 六、CommitRecord

展示：

* Commit Hash
* Branch
* Subject
* Body
* 文件数量
* 新增行
* 删除行
* AI Provider
* AI Model
* AI 是否调用
* 用户是否修改 Message
* 安全扫描结果
* 创建时间

不得展示：

* API Key
* 完整敏感信息
* Authorization Header
* 未脱敏 Diff

## 七、真实 Git 历史

读取：

```bash
git log
```

必须使用参数数组，不使用 `shell=True`。

支持：

* 日期范围
* 作者邮箱
* 最大数量
* Commit Hash
* Subject
* Body
* Author
* Date

作者邮箱必须读取 Git 的有效配置：

```bash
git config --get user.email
```

不要只读取 `--local`。

## 八、工作统计

页面顶部显示：

```text
Commit 数量
Worklog 数量
开发耗时
涉及仓库
标签数量
```

统计必须基于真实记录，不使用代码行数评价工作表现。

## 九、数据导出

支持导出：

```text
Markdown
JSON
CSV
```

导出内容可以包含：

* Commit
* CommitRecord
* Worklog
* 日期范围
* 标签
* 来源信息

文件名示例：

```text
gitpulse-history-2026-07-01-2026-07-29.md
```

## 十、安全要求

必须做到：

* 写接口需要 Session 和 CSRF
* 不允许访问其他仓库路径
* 删除操作需要确认
* 日志不保存完整 Worklog 敏感内容
* 页面输出进行 HTML 转义
* 查询参数限制长度
* 分页大小限制在 100 以内
* 不直接拼接 SQL
* 外部 Git 命令有超时
* 不允许任意 Shell 命令

## 十一、测试

至少覆盖：

* 新增 Worklog
* 编辑 Worklog
* 删除 Worklog
* 非法字段
* 日期筛选
* 标签筛选
* 关键字搜索
* 分页
* CommitRecord 展示
* Git Commit 读取
* Git 全局邮箱读取
* 非 Git 仓库
* 导出 Markdown
* 导出 JSON
* 导出 CSV
* Session 和 CSRF
* HTML 转义
* 数据库错误

所有测试使用临时数据库、临时 Git 仓库和临时 HOME。

## 十二、验收标准

完成后必须满足：

1. Web 页面可以管理 Worklog。
2. 能查看 GitPulse CommitRecord。
3. 能查看真实 Git Commit。
4. 能统一展示工作时间轴。
5. 能按日期、类型、标签和关键字筛选。
6. 能导出 Markdown、JSON 和 CSV。
7. 原有 CLI 和 Web Git 工作台测试继续通过。
8. 不泄露 Secret。
9. 不执行任何危险 Git 操作。
10. Ruff、Mypy 和 Pytest 通过。

## 十三、开发顺序

```text
1. 检查现有 Worklog 和 CommitRecord 模型
2. 实现 Worklog Service 与 API
3. 编写 Worklog 测试
4. 实现 CommitRecord 查询
5. 实现 Git 历史读取
6. 实现统一时间轴
7. 实现筛选和分页
8. 实现导出
9. 完成 Worklog 页面
10. 完成工作历史页面
11. 编写页面 E2E 测试
12. 执行全部测试
13. 更新文档
```

本阶段完成前，不要开发周报编辑、飞书发送、Push、Pull、Reset 或分支管理。

完成后输出：

```text
完成内容
新增 API
新增页面
数据库改动
测试结果
安全验证
已知限制
下一阶段建议
```

下一阶段为：

```text
Web 周报生成、编辑、来源追踪与导出
```
