# GitPulse AI 编程开发提示词

你是一名资深 Python 架构师、CLI 工具开发工程师和 AI 应用工程师。

请根据以下要求，设计并开发一个名为 **GitPulse** 的项目。

GitPulse 是一款基于 Git Diff、Git Log 和开发人员手动工作记录的 AI 开发工作成果助手。它能够生成规范的 Git Commit Message，将一周内的代码提交与非代码工作聚合为开发周报，并通过飞书机器人发送给用户。

请直接参与项目设计、编码、测试和文档编写，不要只给出概念性方案。

---

# 一、项目目标

实现以下完整工作链路：

```text
读取 Git Diff
    ↓
扫描敏感信息
    ↓
分析代码修改目的
    ↓
判断是否需要拆分提交
    ↓
生成 Commit Message
    ↓
用户确认
    ↓
保存结构化工作记录
    ↓
读取指定日期范围内的 Git Log
    ↓
合并相同工作主题
    ↓
加入手动 Worklog
    ↓
生成可追溯的 Markdown 周报
    ↓
用户确认
    ↓
通过飞书机器人发送周报
```

项目必须遵循以下原则：

1. 事实优先。
2. 本地优先。
3. 用户确认。
4. 结果可追溯。
5. 禁止 AI 编造工作成果。
6. 禁止将代码量作为工作价值评价依据。
7. 禁止未经确认自动执行高风险 Git 操作。
8. 高风险敏感信息不得发送到远程模型。
9. 飞书只发送用户已经确认的周报。
10. 所有核心模块必须具有自动化测试。

---

# 二、技术栈

使用以下技术栈：

```text
Python 3.11+
Typer
Pydantic 2.x
SQLAlchemy 2.x
SQLite
PyYAML
httpx
Rich
loguru
pytest
pytest-mock
```

Git 操作优先使用：

```text
subprocess
```

不要在核心模块中强依赖 GitPython。

AI 模型接口使用 OpenAI Compatible API，同时保留以下扩展能力：

* OpenAI 兼容服务
* Ollama
* 企业内部大模型
* Mock 模型，用于自动化测试

飞书机器人使用：

```text
飞书群自定义机器人 Webhook
```

HTTP 请求使用：

```text
httpx
```

---

# 三、项目交付形式

项目必须实现为一个可以安装和运行的 Python CLI 工具。

安装后应支持：

```bash
gitpulse --help
```

项目必须包含：

```text
gitpulse/
├── README.md
├── pyproject.toml
├── .gitignore
├── src/
│   └── gitpulse/
├── tests/
├── examples/
└── docs/
```

使用 `src` 目录布局。

必须支持：

```bash
pip install -e .
```

或：

```bash
uv sync
```

安装完成后，必须能够直接执行：

```bash
gitpulse
```

---

# 四、项目目录结构

请按照以下目录进行开发：

```text
gitpulse/
├── README.md
├── pyproject.toml
├── .gitignore
├── src/
│   └── gitpulse/
│       ├── __init__.py
│       ├── cli.py
│       ├── config.py
│       ├── constants.py
│       ├── exceptions.py
│       ├── models/
│       │   ├── __init__.py
│       │   ├── commit.py
│       │   ├── diff.py
│       │   ├── worklog.py
│       │   ├── report.py
│       │   ├── risk.py
│       │   └── feishu.py
│       ├── git/
│       │   ├── __init__.py
│       │   ├── repository.py
│       │   ├── diff_reader.py
│       │   ├── log_reader.py
│       │   └── parser.py
│       ├── security/
│       │   ├── __init__.py
│       │   ├── secret_scanner.py
│       │   ├── privacy_masker.py
│       │   ├── file_filter.py
│       │   └── diff_truncator.py
│       ├── ai/
│       │   ├── __init__.py
│       │   ├── provider.py
│       │   ├── openai_provider.py
│       │   ├── mock_provider.py
│       │   ├── commit_generator.py
│       │   ├── topic_detector.py
│       │   ├── weekly_generator.py
│       │   └── response_parser.py
│       ├── services/
│       │   ├── __init__.py
│       │   ├── commit_service.py
│       │   ├── check_service.py
│       │   ├── worklog_service.py
│       │   ├── weekly_service.py
│       │   └── notification_service.py
│       ├── storage/
│       │   ├── __init__.py
│       │   ├── database.py
│       │   ├── orm_models.py
│       │   ├── repositories.py
│       │   └── migrations/
│       ├── prompts/
│       │   ├── commit_system.txt
│       │   ├── topic_system.txt
│       │   └── weekly_system.txt
│       ├── exporters/
│       │   ├── __init__.py
│       │   ├── markdown.py
│       │   ├── json_exporter.py
│       │   └── text.py
│       └── integrations/
│           ├── __init__.py
│           └── feishu.py
├── tests/
│   ├── unit/
│   ├── integration/
│   └── fixtures/
├── examples/
│   ├── sample_diff.txt
│   ├── sample_commit.json
│   └── sample_weekly_report.md
└── docs/
    ├── architecture.md
    ├── configuration.md
    └── development.md
```

可以根据实现需要增加文件，但不要随意减少核心模块。

---

# 五、CLI 命令设计

必须实现以下命令。

## 1. 主命令

```bash
gitpulse
```

输出：

```text
GitPulse - AI 开发工作成果助手

Commands:
  init        初始化项目
  commit      生成 Commit Message
  check       检查当前提交风险
  weekly      生成开发周报
  worklog     管理手动工作记录
  history     查看历史记录
  config      管理配置
  notify      发送周报到飞书
```

---

## 2. 初始化

```bash
gitpulse init
```

功能：

* 检测当前目录是否为 Git 仓库
* 获取仓库名称
* 获取仓库根目录
* 获取当前分支
* 获取 Git 用户名和邮箱
* 创建 `.gitpulse.yml`
* 初始化 SQLite 数据库
* 创建报告目录
* 检查 AI 配置
* 检查飞书配置

初始化过程不得覆盖已经存在的配置文件，除非用户明确确认。

---

## 3. 生成 Commit Message

```bash
gitpulse commit
```

支持：

```bash
gitpulse commit --staged
gitpulse commit --unstaged
gitpulse commit --lang zh-CN
gitpulse commit --format conventional
gitpulse commit --no-body
gitpulse commit --copy
```

默认读取：

```bash
git diff --cached
```

处理顺序：

```text
读取 Diff
→ 文件过滤
→ Diff 截断
→ 敏感信息扫描
→ 路径与隐私信息脱敏
→ 多主题分析
→ AI 生成 Commit Message
→ 展示候选结果
→ 用户选择或编辑
→ 保存结构化记录
```

至少生成三个候选：

1. 简洁版
2. 标准版
3. 详细版

输出格式遵循 Conventional Commits：

```text
<type>(<scope>): <subject>

<body>
```

允许的 type：

```text
feat
fix
refactor
perf
test
docs
style
build
ci
chore
revert
```

不得自动执行：

```bash
git add
git commit
git push
git reset
git restore
git checkout
```

只能生成建议并由用户确认。

---

## 4. 提交风险检查

```bash
gitpulse check
```

检查：

* API Key
* Access Token
* Secret
* Password
* 私钥
* 数据库连接字符串
* 云服务凭证
* 内网 IP
* 内网域名
* 邮箱地址
* 本地用户路径
* 调试日志
* TODO
* FIXME
* 临时代码
* 注释掉的大段代码
* 大文件
* 二进制文件
* 构建产物
* 生成文件
* 依赖锁文件
* 多主题混合提交
* 配置文件误修改
* 功能修改未发现测试文件变化

风险等级：

```text
low
medium
high
critical
```

当检测到 high 或 critical 级别敏感信息时：

```text
block_remote_model = true
```

禁止把 Diff 发送到远程 AI。

---

## 5. Worklog 管理

支持：

```bash
gitpulse worklog add
gitpulse worklog list
gitpulse worklog show <id>
gitpulse worklog edit <id>
gitpulse worklog delete <id>
```

Worklog 类型：

```text
debug
research
meeting
support
setup
test
learning
document
other
```

数据字段：

```text
id
repository_id
work_date
work_type
title
description
result
duration_minutes
tags
confirmed_by_user
created_at
updated_at
```

删除操作必须确认。

---

## 6. 周报生成

```bash
gitpulse weekly
```

支持：

```bash
gitpulse weekly --current
gitpulse weekly --last-week
gitpulse weekly --from 2026-07-20 --to 2026-07-26
gitpulse weekly --include-uncommitted
gitpulse weekly --format markdown
gitpulse weekly --send-feishu
```

默认日期范围：

```text
本周周一 00:00 至当前时间
```

数据来源：

* 当前用户 Git Commit
* Commit 结构化记录
* Worklog
* 用户确认的未提交变更
* 用户补充说明
* 用户输入的风险
* 用户输入的下周计划

作者识别优先使用：

```bash
git config user.email
```

读取日志时使用：

```bash
git log --author=<email>
```

必须支持在配置文件中配置多个邮箱。

---

## 7. 飞书发送

支持：

```bash
gitpulse notify weekly
```

也支持：

```bash
gitpulse weekly --send-feishu
```

执行流程：

```text
读取已生成周报
→ 检查周报状态
→ 检查敏感信息
→ 生成飞书消息
→ 展示发送预览
→ 用户确认
→ 调用飞书 Webhook
→ 保存发送结果
```

默认不得自动发送。

只有同时满足以下条件才允许发送：

```text
周报已经生成
周报已经被用户确认
不存在 high 或 critical 敏感信息
飞书 Webhook 已配置
用户明确确认发送
```

---

# 六、Git 数据读取

## 1. 仓库识别

实现以下功能：

* 判断是否位于 Git 仓库
* 获取仓库根目录
* 获取仓库名称
* 获取当前分支
* 获取当前 HEAD
* 获取 Git 用户名
* 获取 Git 用户邮箱
* 获取远程仓库地址
* 判断是否存在暂存区变更
* 判断是否存在未暂存变更
* 判断是否存在冲突文件

所有 Git 命令必须：

* 设置超时
* 捕获标准错误
* 检查返回码
* 使用参数数组调用 subprocess
* 禁止 `shell=True`
* 处理路径中包含空格的情况

---

## 2. Diff 读取

支持：

```bash
git diff --cached
git diff
git show <commit>
git diff <commit1> <commit2>
```

需要采集：

```text
文件路径
文件状态
新增行数
删除行数
Diff 内容
文件扩展名
是否二进制
是否新增
是否删除
是否重命名
是否复制
```

文件状态：

```text
A
M
D
R
C
U
```

---

## 3. Diff 限制

默认配置：

```yaml
diff:
  max_total_chars: 60000
  max_file_chars: 15000
  ignore_binary: true
  ignore_patterns:
    - "*.lock"
    - "dist/**"
    - "build/**"
    - "node_modules/**"
    - "*.min.js"
```

截断时必须记录：

* 原始长度
* 截断后长度
* 被截断文件
* 被忽略文件
* 截断原因

不得静默丢弃内容。

---

# 七、敏感信息扫描

实现一个可扩展的规则扫描器。

至少支持检测：

```text
OpenAI API Key
GitHub Token
GitLab Token
AWS Access Key
Bearer Token
JWT
通用 Password
通用 Secret
PEM 私钥
数据库 URL
Redis URL
MongoDB URL
手机号
身份证号
邮箱
内网 IPv4
本地用户目录
```

敏感值不得完整写入日志、数据库或终端输出。

必须使用脱敏形式：

```text
sk-****9f2a
```

高风险处理规则：

```text
high 或 critical：
- 禁止远程模型调用
- 提示用户移除敏感文件
- 允许继续使用本地模型
- 不允许通过飞书发送相关内容
```

如果敏感信息扫描过程失败，默认视为不安全，并阻止远程调用。

---

# 八、AI Provider 抽象

定义统一接口：

```python
from abc import ABC, abstractmethod

class LLMProvider(ABC):

    @abstractmethod
    def generate_commit(self, request):
        raise NotImplementedError

    @abstractmethod
    def detect_topics(self, request):
        raise NotImplementedError

    @abstractmethod
    def generate_weekly_report(self, request):
        raise NotImplementedError
```

实现：

```text
OpenAICompatibleProvider
MockLLMProvider
```

Provider 需要支持：

* 自定义 base URL
* 自定义模型
* 从环境变量读取 API Key
* 请求超时
* 最大重试次数
* JSON 响应模式
* 响应 Schema 校验
* 错误分类
* 日志脱敏

禁止把 API Key 写入 `.gitpulse.yml`。

只能配置环境变量名称：

```yaml
ai:
  api_key_env: GITPULSE_API_KEY
```

---

# 九、Commit Message AI 输出模型

使用 Pydantic 定义结构化输出。

参考结构：

```python
class CommitCandidate(BaseModel):
    subject: str
    body: list[str] = []

class CommitEvidence(BaseModel):
    file: str
    reason: str

class SplitTopic(BaseModel):
    title: str
    type: str
    scope: str | None = None
    files: list[str]
    suggested_subject: str

class CommitGenerationResult(BaseModel):
    type: str
    scope: str | None = None
    subject: str
    body: list[str] = []
    confidence: Literal["high", "medium", "low"]
    should_split: bool
    split_confidence: float
    split_suggestions: list[SplitTopic] = []
    evidence: list[CommitEvidence] = []
    needs_confirmation: list[str] = []
    candidates: dict[str, CommitCandidate]
```

AI 输出解析失败时：

1. 尝试一次格式修复。
2. 修复失败后返回可理解的错误。
3. 不得把无效数据写入数据库。
4. 保留脱敏后的原始响应以便调试。
5. 测试环境中必须覆盖错误响应场景。

---

# 十、周报生成逻辑

周报生成不能简单逐条复制 Commit。

必须完成：

1. 按模块聚类。
2. 按工作目的聚类。
3. 合并重复提交。
4. 判断连续多个 Commit 是否属于同一工作主题。
5. 区分功能、修复、重构、测试、文档等类型。
6. 合并 Worklog。
7. 删除重复表达。
8. 保留来源。
9. 标记可信度。
10. 将不确定内容交给用户确认。

周报结构：

```markdown
# 本周工作总结

## 一、本周完成事项

### 1. 工作主题

- 具体工作
- 具体工作

来源：
- commit:a13f2bc
- commit:e72c981

## 二、问题排查与支持

## 三、测试与验证

## 四、当前风险与待处理事项

## 五、下周计划
```

每条内容必须包含：

```text
content
confidence
sources
```

可信度：

```text
high
medium
low
```

规则：

```text
high：
可以直接由 Commit、Diff、Worklog 或用户确认信息证明。

medium：
由多个相关记录合理归纳，需要用户确认。

low：
依赖推断，默认不进入正式周报。
```

不得生成：

```text
系统性能提升 30%
显著提高了稳定性
全面提升开发效率
提前完成所有任务
获得用户一致好评
```

除非输入中存在明确证据。

---

# 十一、飞书机器人集成

## 1. 配置

在 `.gitpulse.yml` 中增加：

```yaml
feishu:
  enabled: false
  webhook_env: GITPULSE_FEISHU_WEBHOOK
  secret_env: GITPULSE_FEISHU_SECRET
  message_type: interactive
  require_confirmation: true
  include_sources: false
  max_content_length: 15000
```

Webhook 和 Secret 必须通过环境变量读取。

禁止将完整 Webhook 地址写入项目配置。

---

## 2. 飞书客户端接口

实现：

```python
class FeishuClient:
    def send_text(self, content: str) -> SendResult:
        ...

    def send_card(self, report: WeeklyReport) -> SendResult:
        ...

    def test_connection(self) -> SendResult:
        ...
```

支持：

```text
text
interactive card
```

需要处理：

* Webhook 不存在
* 请求超时
* 网络错误
* HTTP 非 2xx
* 飞书业务错误码
* 消息过长
* 签名错误
* 发送频率限制
* 重复发送

---

## 3. 飞书签名

如果配置了机器人 Secret，实现签名算法。

签名模块需要：

* 使用当前 Unix 时间戳
* 使用 HMAC-SHA256
* 使用 Base64 编码
* 可通过单元测试验证
* 不在日志中打印 Secret

将签名逻辑封装为独立函数，方便测试。

---

## 4. 飞书消息卡片

消息卡片至少包含：

```text
周报标题
日期范围
本周完成事项
问题排查与支持
测试与验证
风险与待处理事项
下周计划
生成时间
```

默认不在群消息中展示完整 Commit 来源。

可以配置：

```yaml
feishu:
  include_sources: true
```

内容过长时：

1. 优先保留工作主题标题。
2. 保留风险。
3. 保留下周计划。
4. 压缩过细的技术实现。
5. 在消息末尾提示内容已省略。
6. 完整内容仍保存在本地 Markdown 文件。

---

## 5. 飞书发送记录

建立发送记录表：

```sql
CREATE TABLE notification_records (
    id TEXT PRIMARY KEY,
    report_id TEXT NOT NULL,
    channel TEXT NOT NULL,
    message_type TEXT NOT NULL,
    status TEXT NOT NULL,
    response_code TEXT,
    response_message TEXT,
    content_hash TEXT,
    sent_at TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY(report_id) REFERENCES weekly_reports(id)
);
```

状态：

```text
pending
confirmed
sent
failed
cancelled
```

使用内容哈希防止重复发送。

---

# 十二、SQLite 数据库

至少实现以下数据表。

## repositories

```sql
CREATE TABLE repositories (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    root_path TEXT NOT NULL,
    remote_url TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
```

## commit_records

```sql
CREATE TABLE commit_records (
    id TEXT PRIMARY KEY,
    repository_id TEXT NOT NULL,
    commit_hash TEXT,
    branch TEXT,
    commit_type TEXT,
    scope TEXT,
    subject TEXT NOT NULL,
    body TEXT,
    summary TEXT,
    files_json TEXT,
    insertions INTEGER DEFAULT 0,
    deletions INTEGER DEFAULT 0,
    confidence TEXT,
    confirmed_by_user INTEGER DEFAULT 0,
    created_at TEXT NOT NULL,
    FOREIGN KEY(repository_id) REFERENCES repositories(id)
);
```

## worklogs

```sql
CREATE TABLE worklogs (
    id TEXT PRIMARY KEY,
    repository_id TEXT,
    work_date TEXT NOT NULL,
    work_type TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    result TEXT,
    duration_minutes INTEGER,
    tags_json TEXT,
    confirmed_by_user INTEGER DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
```

## risks

```sql
CREATE TABLE risks (
    id TEXT PRIMARY KEY,
    record_id TEXT NOT NULL,
    risk_level TEXT NOT NULL,
    risk_type TEXT NOT NULL,
    file_path TEXT,
    line_number INTEGER,
    description TEXT NOT NULL,
    suggestion TEXT,
    created_at TEXT NOT NULL
);
```

## weekly_reports

```sql
CREATE TABLE weekly_reports (
    id TEXT PRIMARY KEY,
    date_from TEXT NOT NULL,
    date_to TEXT NOT NULL,
    title TEXT NOT NULL,
    content_markdown TEXT NOT NULL,
    source_json TEXT,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
```

## notification_records

按飞书集成部分定义。

数据库操作必须使用 Repository 模式。

业务服务层不得直接编写 SQL。

---

# 十三、配置文件

初始化生成 `.gitpulse.yml`：

```yaml
project:
  name: device-manager

user:
  name: developer
  git_emails:
    - developer@example.com

commit:
  language: zh-CN
  format: conventional
  include_body: true
  subject_max_length: 50
  allowed_types:
    - feat
    - fix
    - refactor
    - perf
    - test
    - docs
    - style
    - build
    - ci
    - chore
    - revert

diff:
  max_total_chars: 60000
  max_file_chars: 15000
  ignore_binary: true
  ignore_patterns:
    - "*.lock"
    - "dist/**"
    - "build/**"
    - "node_modules/**"
    - "*.min.js"

security:
  scan_secrets: true
  block_remote_on_high_risk: true
  mask_local_paths: true
  mask_internal_domains: true

ai:
  provider: openai-compatible
  model: local-model
  base_url: http://localhost:11434/v1
  api_key_env: GITPULSE_API_KEY
  temperature: 0.2
  timeout_seconds: 60
  max_retries: 2

weekly:
  week_start: monday
  include_uncommitted: false
  include_commit_sources: true
  exclude_low_confidence: true

feishu:
  enabled: false
  webhook_env: GITPULSE_FEISHU_WEBHOOK
  secret_env: GITPULSE_FEISHU_SECRET
  message_type: interactive
  require_confirmation: true
  include_sources: false
  max_content_length: 15000

storage:
  database: ~/.gitpulse/data.db
  report_dir: ./reports
```

配置加载顺序：

```text
默认配置
→ 用户级配置
→ 项目配置
→ 环境变量
→ CLI 参数
```

优先级从低到高。

配置错误时必须指出：

* 错误字段
* 当前值
* 合法值
* 修复示例

---

# 十四、错误处理

定义统一异常类型：

```text
GitPulseError
GitRepositoryError
GitCommandError
ConfigurationError
SecurityScanError
SensitiveContentError
LLMProviderError
LLMResponseError
DatabaseError
ReportGenerationError
NotificationError
FeishuAPIError
```

CLI 捕获业务异常后：

* 使用友好中文提示
* 不显示完整堆栈
* 提供解决方法
* 使用合理退出码

调试模式下才输出完整堆栈。

---

# 十五、日志要求

日志必须满足：

* 不记录完整 Diff
* 不记录 API Key
* 不记录飞书 Webhook
* 不记录飞书 Secret
* 不记录完整敏感值
* 不记录数据库密码
* 路径默认脱敏
* 支持 debug、info、warning、error

可以记录：

```text
Diff 字符数
变更文件数量
风险数量
模型耗时
数据库操作结果
飞书请求状态
```

---

# 十六、测试要求

使用 pytest。

总体测试覆盖率目标：

```text
核心模块不低于 80%
```

必须为以下模块编写单元测试：

1. Git 仓库识别
2. Git 命令失败处理
3. Diff 解析
4. 文件状态解析
5. 二进制文件识别
6. 文件忽略规则
7. Diff 截断
8. 敏感信息检测
9. 敏感内容脱敏
10. Commit Message 响应解析
11. 多主题结果解析
12. 周报聚合
13. 周报 Markdown 导出
14. SQLite 数据写入和查询
15. 配置优先级
16. 飞书签名
17. 飞书文本消息生成
18. 飞书卡片生成
19. 飞书发送成功
20. 飞书发送失败
21. 飞书重复发送阻止
22. Mock AI Provider

准备以下集成测试场景：

```text
单一 Bug 修复
单一功能开发
代码重构
文档修改
多主题混合修改
包含 Token 的配置文件
超大 Diff
二进制文件修改
多个 Commit 属于同一主题
只有 Worklog 没有 Commit
周报生成并发送飞书
飞书服务不可用
```

所有外部 HTTP 请求必须 Mock。

测试不得调用真实 AI 服务或真实飞书 Webhook。

---

# 十七、验收标准

## Commit Message

* 能读取暂存区 Diff。
* 能识别变更文件和统计信息。
* 能生成 Conventional Commits 格式结果。
* 能输出 type、scope、subject 和 body。
* 能生成三个候选。
* 能识别明显的多主题提交。
* 能展示生成依据。
* 存在高风险密钥时阻止远程模型。
* 不自动执行 Git Commit。

## Worklog

* 能新增工作记录。
* 能查看工作记录。
* 能编辑工作记录。
* 能删除工作记录。
* 能按日期查询。
* 能按类型筛选。

## 周报

* 能读取指定日期范围内的个人 Commit。
* 能配置多个 Git 邮箱。
* 能合并同一主题的多个 Commit。
* 能将 Worklog 加入周报。
* 能展示每条内容来源。
* 能区分高、中、低可信度。
* 低可信度内容默认排除。
* 能导出 Markdown。
* 用户可以编辑最终周报。

## 飞书

* 能读取环境变量中的 Webhook。
* 能发送文本消息。
* 能发送消息卡片。
* 能支持签名校验。
* 发送前展示预览。
* 默认要求用户确认。
* 能阻止包含高风险敏感内容的消息。
* 能处理网络错误。
* 能保存发送结果。
* 能避免同一周报重复发送。

---

# 十八、开发阶段

按照以下阶段实施。

## 第一阶段：项目骨架

完成：

* pyproject.toml
* src 目录结构
* Typer CLI
* 配置模型
* 异常体系
* 日志体系
* 基础测试框架

完成后运行：

```bash
gitpulse --help
pytest
```

---

## 第二阶段：Git 基础能力

完成：

* 仓库识别
* Diff 读取
* Log 读取
* 文件状态解析
* Diff 统计
* 文件过滤
* Diff 截断

完成相关单元测试。

---

## 第三阶段：安全模块

完成：

* Secret 扫描
* 路径脱敏
* 内网信息脱敏
* 风险等级
* 高风险远程调用阻断

完成相关单元测试。

---

## 第四阶段：Commit Message

完成：

* AI Provider 抽象
* OpenAI Compatible Provider
* Mock Provider
* Commit Prompt
* JSON 解析
* 三种 Commit 候选
* 多主题检测
* Commit 风险展示

完成相关单元测试和集成测试。

---

## 第五阶段：存储和 Worklog

完成：

* SQLite 初始化
* ORM 模型
* Repository 层
* Commit 记录保存
* Worklog 增删改查
* 历史记录查询

完成相关测试。

---

## 第六阶段：周报

完成：

* 日期范围处理
* Git 用户过滤
* 多仓库数据模型预留
* Commit 聚类
* Worklog 聚合
* 周报 AI 生成
* 可信度管理
* 来源追踪
* Markdown 导出

完成相关测试。

---

## 第七阶段：飞书机器人

完成：

* 飞书配置
* Webhook 客户端
* 签名算法
* 文本消息
* 消息卡片
* 发送预览
* 用户确认
* 发送记录
* 重复发送检查

完成相关测试。

---

## 第八阶段：文档和演示

完成：

* README
* 安装指南
* 配置指南
* 使用示例
* 架构文档
* 示例仓库说明
* 演示流程
* 常见错误说明

---

# 十九、AI 编程工作方式

开发过程中必须遵循：

1. 先检查当前仓库结构，再创建文件。
2. 每次只完成一个清晰阶段。
3. 修改前说明本阶段目标。
4. 不得一次生成大量无法验证的代码。
5. 每完成一个模块，立即补充测试。
6. 每完成一个阶段，运行测试。
7. 测试失败时先修复，不继续叠加功能。
8. 不删除已有正确代码。
9. 不随意修改公开接口。
10. 发现需求冲突时，优先保证安全和事实约束。
11. 不实现员工排名、绩效评分或代码量评价功能。
12. 不在代码中硬编码 API Key、Webhook 或 Secret。
13. 重要函数添加类型注解。
14. 公共模块添加必要文档字符串。
15. 避免超大函数和循环依赖。
16. 业务逻辑放在 Service 层。
17. Git 操作放在 Git 数据层。
18. 数据操作放在 Repository 层。
19. 外部服务放在 integrations 或 ai 层。
20. CLI 层只处理参数、展示和用户交互。

---

# 二十、每个阶段的输出格式

每完成一个开发阶段，请输出：

```text
## 本阶段完成内容

- 完成的模块
- 新增的文件
- 修改的文件

## 关键设计

- 主要类和接口
- 数据流
- 安全处理

## 测试结果

- 执行的测试命令
- 通过数量
- 失败数量

## 使用方式

- 可执行命令
- 示例输出

## 尚未完成

- 下一阶段工作
- 当前已知限制
```

不要声称测试通过，除非已经实际执行测试。

---

# 二十一、首次执行任务

现在请开始第一阶段开发。

第一阶段任务：

1. 检查当前工作目录。
2. 创建标准 Python 项目骨架。
3. 创建 `pyproject.toml`。
4. 创建 `src/gitpulse` 目录。
5. 实现 Typer 主 CLI。
6. 实现基础配置模型。
7. 实现基础异常类型。
8. 实现基础日志配置。
9. 创建 pytest 测试框架。
10. 实现以下命令的空壳和帮助信息：

```bash
gitpulse init
gitpulse commit
gitpulse check
gitpulse weekly
gitpulse worklog
gitpulse history
gitpulse config
gitpulse notify
```

11. 编写 README 初始版本。
12. 执行测试。
13. 展示本阶段结果。

暂时不要实现真实 AI 调用、数据库业务、飞书发送或复杂 Git 分析。

第一阶段完成并通过测试后，再继续下一阶段。
