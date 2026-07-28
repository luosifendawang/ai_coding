# GitPulse

让每一次代码提交，都成为可追溯的工作成果。

GitPulse 是一个本地优先的 Git 工作成果助手。它读取 Git Diff、Git Log、手动 Worklog 和确认后的结构化记录，帮助开发者生成安全可审阅的 Commit Message、工作记录、开发周报和飞书通知。

## 核心能力

- Git 仓库识别、暂存区/工作区 Diff 读取、Git Log 读取。
- 本地敏感信息扫描、隐私脱敏和远程模型调用阻断。
- AI Commit Message 生成，支持 mock 和 OpenAI-compatible Provider。
- 多主题提交识别，但不自动拆分暂存区。
- CommitRecord、Worklog、History 本地 SQLite 持久化。
- 来源可追溯的周报生成，支持 Markdown、Text、JSON 导出。
- 飞书自定义机器人通知，支持预览、签名、重复保护和发送审计。
- `doctor` 环境诊断、`setup` 配置向导、`data` 备份与清理。

## 安全原则

- 不自动执行 `git commit`、`git add`、`git push`。
- API Key、飞书 Webhook、飞书 Secret 只从环境变量读取。
- 高风险敏感内容会阻止远程 AI 调用和飞书发送。
- AI 输出、周报和通知都需要用户确认。
- 不基于代码量做绩效评价。

## 安装

尚未发布到包索引时，在源码目录安装：

```bash
pip install .
```

开发安装：

```bash
pip install -e ".[dev]"
```

验证：

```bash
gitpulse --version
gitpulse doctor
```

## 快速开始

```bash
gitpulse setup --user --preview
gitpulse init
git add <files>
gitpulse check
gitpulse commit --provider mock
gitpulse worklog add --yes --type debug --title "排查问题"
gitpulse weekly --current --no-ai --confirm --output weekly.md
```

## AI 配置

GitPulse 不保存 API Key。请设置环境变量：

```bash
export GITPULSE_API_KEY="..."
```

本地或演示环境可以使用：

```bash
gitpulse commit --provider mock
gitpulse weekly --no-ai
```

## 周报

```bash
gitpulse weekly --current --no-ai
gitpulse weekly --last-week --format markdown --output weekly.md
gitpulse weekly --from 2026-07-27 --to 2026-08-02 --author you@example.com --json
```

正式周报要求来源覆盖率达到 100%。Medium 内容需要用户确认，Low 内容默认不进入正式周报。

## 飞书通知

```bash
export GITPULSE_FEISHU_WEBHOOK="https://open.feishu.cn/open-apis/bot/v2/hook/..."
export GITPULSE_FEISHU_SECRET="..."
gitpulse notify weekly <report-id> --preview
gitpulse notify weekly <report-id> --yes
```

只有 confirmed 周报可以发送。发送前会重新进行安全扫描并检查重复发送。

## 数据管理

```bash
gitpulse data info
gitpulse data backup
gitpulse data clear --yes
```

备份只包含 GitPulse SQLite 数据库，不包含环境变量、API Key、Webhook 或 Git 仓库源码。

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
- 当前未实现 Git Hook、IDE 插件、团队管理、定时任务、Web 管理后台、月报和季度报告。
