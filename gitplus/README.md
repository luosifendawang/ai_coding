# gitplus

让每一次代码提交，都成为可追溯的工作成果。

gitplus 是一个本地优先的 Git 工作成果助手。它读取 Git Diff、Git Log、手动 Worklog 和确认后的结构化记录，帮助开发者生成安全可审阅的 Commit Message、工作记录、开发周报和飞书通知。

## 核心能力

- Git 仓库识别、暂存区/工作区 Diff 读取、Git Log 读取。
- 本地敏感信息扫描、隐私脱敏和远程模型调用阻断。
- AI Commit Message 生成，支持 mock 和 OpenAI-compatible Provider。
- 多主题提交识别，但不自动拆分暂存区。
- CommitRecord、Worklog、History 本地 SQLite 持久化。
- 来源可追溯的周报生成，支持 Markdown、Text、JSON 导出。
- 飞书 Webhook 与应用机器人通知，支持 Web 预览、发送、重试、重复保护和发送审计。
- 仅监听本机的 Web 控制台，支持安全查看、验证和保存系统配置。
- 本地 Web Git 工作台，支持状态、Diff、暂存、安全扫描、AI Message 和确认 Commit。
- Web 工作日志管理与统一工作历史，支持筛选、统计和 Markdown/JSON/CSV 导出。
- Web 周报管理中心，支持数据预览、规则或 AI 整理、来源追踪、版本化编辑与导出。
- `doctor` 环境诊断、`setup` 配置向导、`data` 备份与清理。

## 安全原则

- 不自动执行 `git commit`、`git add`、`git push`。
- API Key 和飞书 App Secret 可从环境变量或权限为 `0600` 的本地 Secret 文件读取。
- 高风险敏感内容会阻止远程 AI 调用和飞书发送。
- AI 输出、周报和通知都需要用户确认。
- 不基于代码量做绩效评价。

## 安装

推荐全局安装：

```bash
pipx install gitplus
cd your-project
gitplus init
gitplus web
```

尚未发布到包索引时，在源码目录安装：

```bash
pip install .
```

开发安装：

```bash
pip install -e ".[dev]"
pipx install --editable .
```

验证：

```bash
gitplus --version
gitplus doctor
gitplus web
```

## 快速开始

```bash
gitplus setup --user --preview
gitplus init
git add <files>
gitplus check
gitplus commit --provider mock
gitplus worklog add --yes --type debug --title "排查问题"
gitplus weekly --current --no-ai --confirm --output weekly.md
gitplus web
```

## AI 配置

可以在项目 `.gitplus.yml` 中配置 Provider，也可以通过 Web 控制台将 API Key 保存到用户级本地 Secret 文件：

```yaml
ai:
  provider: openai-compatible
  model: your-model
  base_url: https://api.example.com/v1
  api_key_env: gitplus_API_KEY
```

环境变量模式仍然支持：

```bash
export gitplus_API_KEY="..."
```

本地或演示环境可以使用：

```bash
gitplus commit --provider mock
gitplus weekly --no-ai
```

## 本地 Web 控制台

```bash
gitplus web
gitplus web --port 8765 --no-open
gitplus web --project /path/to/repository
```

服务固定监听 `127.0.0.1`。打开一次性访问链接后，可以配置 AI、存储、周报、安全和飞书参数；配置写入带校验、变更预览、备份和并发修改检测。

“Git 工作台”支持查看已暂存、未暂存、未跟踪和冲突文件，按需查看受限 Diff，
暂存或取消暂存文件，执行安全扫描，生成并编辑 Commit Message，最终确认后创建
本地 Commit。gitplus Web 不会自动执行 Push。
gitplus 不会自动 Push，远端同步仍由你在确认后手动执行。

“工作日志”支持新增、编辑、复制、筛选和确认删除；“工作历史”统一展示真实 Git
Commit、gitplus CommitRecord 与 Worklog，并提供时间范围统计和导出。详见
[`docs/web-worklogs.md`](docs/web-worklogs.md) 与
[`docs/web-history.md`](docs/web-history.md)。

“周报”支持周期选择、来源预览与排除、规则或 AI 整理、草稿编辑、来源追踪、
确认、重新打开以及 Markdown/Text/JSON 导出。详见
[`docs/web-weekly.md`](docs/web-weekly.md)。

“飞书通知”支持查看配置状态、选择消息类型、预览已确认周报、发送测试消息、
确认发送正式周报、查看发送记录和重试失败记录。详见
[`docs/web-notifications.md`](docs/web-notifications.md)。

安装和发布验证见 [`docs/installation.md`](docs/installation.md)。Git 工作台、
Worklog、周报文档见 [`docs/git-workbench.md`](docs/git-workbench.md)、
[`docs/worklogs.md`](docs/worklogs.md) 和 [`docs/weekly.md`](docs/weekly.md)。

## 周报

```bash
gitplus weekly --current --no-ai
gitplus weekly --last-week --format markdown --output weekly.md
gitplus weekly --from 2026-07-27 --to 2026-08-02 --author you@example.com --json
```

正式周报要求来源覆盖率达到 100%。Medium 内容需要用户确认，Low 内容默认不进入正式周报。

## 飞书通知

`.gitplus.yml`：

```yaml
feishu:
  enabled: true
  mode: app
  app_id: cli_yourappid1234
  app_secret: "your-app-secret"
  receive_id_type: chat_id
  receive_id: oc_your_chat_id
```

也可以把密钥放在 `~/.config/gitplus/secrets.yml`：

```yaml
feishu:
  app_secret: "your-app-secret"
```

```bash
gitplus notify weekly <report-id> --preview
gitplus notify weekly <report-id> --yes
```

Webhook 机器人可以使用：

```yaml
feishu:
  enabled: true
  mode: webhook
  webhook: "https://open.feishu.cn/open-apis/bot/v2/hook/..."
  secret: "..."
```

飞书应用必须启用机器人能力、具有发消息权限并加入目标群。只有 confirmed 或已发送周报可以进入发送流程，发送前会重新进行安全扫描并检查重复发送。

## 数据管理

```bash
gitplus data info
gitplus data backup
gitplus data clear --yes
```

备份只包含 gitplus SQLite 数据库，不包含环境变量、API Key、App Secret 或 Git 仓库源码。

## 开发与测试

```bash
pytest
pytest tests/e2e tests/performance
python scripts/check_secrets.py
python -m build
```

## 当前限制

- AI 输出不保证完全准确，必须审阅。
- Secret 扫描不能保证发现所有秘密。
- SQLite 适合个人本地使用，不适合高并发团队服务。
- 飞书读取响应超时时会进入 `unknown`，需要人工检查群消息。
- Web 控制台暂不包含 Push、Pull、Reset 或分支管理。
- 当前未实现 Git Hook、IDE 插件、团队管理、定时任务、月报和季度报告。
