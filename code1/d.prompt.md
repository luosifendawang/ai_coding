# GitPulse Web 控制台第四阶段：周报管理中心

继续开发现有 GitPulse 项目。

当前已经完成：

* Web 系统配置中心
* Git 工作台与 Commit 助手
* Worklog 管理
* CommitRecord 与 Git 历史
* 工作成果查询和导出

本阶段只开发：

```text
周报数据预览
周报生成
内容整理与去重
周报编辑
来源追踪
确认与导出
```

不要重新初始化项目，不要重写现有 `WeeklyService`、数据库模型和 CLI。Web API 必须复用现有周报能力。

## 一、目标

用户可以在 Web 页面中：

1. 选择本周、上周或自定义日期范围
2. 选择作者邮箱
3. 预览 Commit、CommitRecord 和 Worklog
4. 排除无意义或测试记录
5. 生成规则版周报
6. 可选使用 AI 整理周报
7. 编辑标题、工作项和总结
8. 查看每个工作项的来源
9. 处理待确认内容
10. 保存草稿
11. 确认正式周报
12. 导出 Markdown、Text 和 JSON

## 二、页面

新增：

```text
/weekly
/weekly/{report_id}
```

导航增加：

```text
Git 工作台
Worklog
工作历史
周报
系统配置
```

周报页面分为：

```text
周期选择
数据预览
生成设置
周报编辑
来源面板
导出操作
```

## 三、数据预览 API

实现：

```http
POST /api/weekly/preview
```

请求：

```json
{
  "range_kind": "current",
  "date_from": null,
  "date_to": null,
  "authors": ["user@example.com"],
  "include_uncommitted": false
}
```

返回：

* 日期范围
* Git Commit
* CommitRecord
* Worklog
* 数据数量
* 来源覆盖率
* 可能的重复项
* 低信息记录
* 模板或测试记录

作者邮箱默认读取：

```bash
git config --get user.email
```

不能只读取仓库级配置。

## 四、数据清理

生成周报前处理：

* 相同 Commit 去重
* CommitRecord 与真实 Commit 关联
* Subject 和 Body 重复去除
* 过滤明显占位模板
* 过滤过短的无意义记录
* 合并相似主题
* 保留所有有效来源

至少识别类似占位文本：

```text
Module: Brief and clear title
More detailed issue description
Test Result:
init
test
```

不要因为标题相似就错误合并不同仓库或不同工作内容。

## 五、周报生成 API

实现：

```http
POST /api/weekly/generate
```

请求支持：

```json
{
  "range_kind": "current",
  "authors": ["user@example.com"],
  "use_ai": false,
  "include_uncommitted": false,
  "excluded_source_ids": [],
  "user_context": ""
}
```

生成模式：

```text
规则整理
AI 整理
```

规则模式必须始终可用。

AI 失败时自动回退到规则模式，并显示警告，不得丢失已收集数据。

## 六、AI 周报整理

AI 只能基于已收集并脱敏的数据生成内容。

要求：

* 不虚构工作成果
* 不添加不存在的数字
* 不用代码行数评价工作表现
* 每个正式工作项必须有来源
* Low Confidence 内容默认不进入正式周报
* Medium Confidence 内容需要用户确认
* 输出结构化 JSON
* 不输出推理过程

AI 返回非法 JSON 时，应显示可理解错误或回退规则模式。

## 七、周报结构

默认结构：

```text
本周开发周报

周期
状态
来源覆盖率

本周完成
问题与解决
测试与质量
文档与协作
下周计划
待确认事项
```

没有数据的分组可以隐藏。

不要直接把内部分类名显示为：

```text
code
other
unknown
```

应转换成正常中文标题。

## 八、周报编辑

用户可以编辑：

* 周报标题
* 分组标题
* 工作项标题
* 工作项描述
* 工作结果
* 下周计划
* 补充说明

支持：

* 调整工作项顺序
* 移动工作项分组
* 删除工作项
* 恢复已删除项
* 新增手动工作项
* 保存草稿

手动新增内容必须标记来源：

```text
来源：用户补充
```

## 九、来源追踪

每个工作项至少保存：

```json
{
  "source_type": "commit",
  "source_id": "43e1f1c0",
  "repository": "ai_coding",
  "confidence": "high"
}
```

页面可以点击查看：

* Commit Hash
* Commit Subject
* Worklog
* CommitRecord
* 文件列表摘要

不得展示未脱敏的完整 Diff。

正式周报要求：

```text
每个工作项至少有一个有效来源
```

## 十、周报状态

支持：

```text
draft
confirmed
exported
sent
```

规则：

* 新生成周报为 `draft`
* 用户确认后变为 `confirmed`
* 修改已确认周报后重新变为 `draft`
* 未确认周报不能正式发送飞书
* 导出不自动改变为 `sent`

## 十一、API

实现：

```http
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

所有写接口必须验证：

* Session
* CSRF
* 周报是否存在
* 周报版本
* 当前状态
* 字段长度
* 来源完整性

## 十二、并发修改

周报保存时使用 Revision 或 Version。

请求：

```json
{
  "version": 3,
  "report": {}
}
```

版本不一致返回：

```http
409 Conflict
```

提示：

```text
周报已被其他操作修改，请重新加载。
```

## 十三、导出

支持：

```text
Markdown
Text
JSON
```

文件名示例：

```text
gitpulse-weekly-2026-07-27-2026-08-02.md
```

Markdown 默认包含：

* 日期范围
* 周报内容
* 来源覆盖率
* 可选来源列表

导出文件中不得包含：

* API Key
* 飞书 Secret
* 完整敏感信息
* 未脱敏 Diff

## 十四、安全要求

必须做到：

* 写接口需要 Session 和 CSRF
* 页面输出进行 HTML 转义
* AI 输入先经过敏感信息扫描
* High 和 Critical 风险不能发送到远程 AI
* 日志不记录完整周报正文
* 不允许任意文件导出路径
* 导出文件由服务端生成安全文件名
* 不直接拼接 SQL
* 不信任前端提交的来源 ID

## 十五、测试

至少覆盖：

* 本周、上周和自定义周期
* Git 全局邮箱读取
* 无数据周期
* Commit 和 CommitRecord 去重
* 重复正文清理
* 占位模板过滤
* Worklog 合并
* 规则模式生成
* AI 模式生成
* AI 非法 JSON
* AI 超时回退
* 来源完整性
* Low 和 Medium Confidence
* 草稿保存
* 周报确认
* 已确认后修改
* 并发版本冲突
* Markdown 导出
* Text 导出
* JSON 导出
* Session 和 CSRF
* HTML 转义

所有测试使用临时数据库、临时 Git 仓库和 Mock AI。

## 十六、验收标准

完成后必须满足：

1. 能选择周期并预览数据。
2. 能生成规则版周报。
3. 能选择 AI 整理。
4. 能去除明显重复内容。
5. 能过滤测试和占位记录。
6. 能编辑周报内容。
7. 每个正式工作项都有来源。
8. 能保存、确认和重新打开周报。
9. 能导出 Markdown、Text 和 JSON。
10. 原有 CLI 和 Web 测试继续通过。
11. Pytest、Ruff 和 Mypy 通过。

## 十七、开发顺序

```text
1. 检查现有 WeeklyService 和周报模型
2. 实现数据预览与去重
3. 编写数据清理测试
4. 实现规则周报生成
5. 实现 AI 周报生成和回退
6. 实现周报保存与版本控制
7. 实现来源追踪
8. 实现周报编辑页面
9. 实现确认和重新打开
10. 实现 Markdown、Text、JSON 导出
11. 编写页面 E2E 测试
12. 执行全部测试
13. 更新文档
```

本阶段完成前，不要开发飞书正式发送、应用机器人、Push、Pull、Reset 或分支管理。

完成后输出：

```text
完成内容
新增 API
新增页面
数据清理规则
AI 生成方式
来源追踪方式
测试结果
安全验证
已知限制
下一阶段建议
```

下一阶段为：

```text
Web 飞书通知中心、消息预览与发送记录
```
