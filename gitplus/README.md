# gitplus

gitplus 是一款本地优先的 AI 开发工作成果助手。它从 Git Diff、Git Log、手工工作日志和本地结构化记录中提取事实，协助开发者安全地生成提交信息、沉淀工作记录、查询研发历史并整理智能周报。

完整项目介绍、技术架构、功能说明、部署方式和创新点请阅读 [项目文档](docs/项目文档.md)。

## 核心能力

- Git 工作台：查看状态与受控 Diff，暂存/取消暂存文件，并在用户确认后创建本地 Commit。
- 安全扫描：本地识别凭证、密钥、隐私数据和内网信息，按风险等级处理并支持脱敏。
- AI 提交助手：支持 mock 与 OpenAI-compatible 模型服务，生成可编辑、可审阅的 Commit Message。
- 工作日志：记录开发、排障、测试等工作，并支持查询、编辑、筛选和删除。
- 统一历史：汇聚 Git 提交、确认记录和工作日志，提供检索、统计与多格式导出。
- 智能周报：先选择事实来源，再以规则或 AI 模式生成、编辑、保存、确认和导出周报。
- 本地控制台：只监听本机，提供会话、CSRF、配置预览、备份和并发修改保护。

## 安全原则

- 不会未经确认执行 `git add`、`git commit` 或 `git push`。
- 在远程模型调用前完成本地敏感信息扫描；高风险内容默认阻止远程调用。
- API Key 通过环境变量或本地 Secret 文件管理，不在普通配置响应中返回。
- AI 生成结果和正式周报均由用户确认。

## 安装

要求 Python 3.9+ 和可用的 Git。

```bash
git clone <repository-url>
cd gitplus
python -m venv .venv
pip install -e ".[dev]"
gitplus --version
gitplus doctor
```

也可以安装发行包：

```bash
pip install .
```

## 快速开始

```bash
gitplus init
git add <files>
gitplus check --staged
gitplus commit --provider mock
gitplus worklog add --yes --type development --title "完成核心功能"
gitplus web
```

启动 Web 控制台后，使用浏览器中的本地访问链接进入 Git 工作台、工作日志、历史、智能周报助手和系统配置页面。

## 常用命令

```bash
gitplus check --staged
gitplus check --unstaged
gitplus commit --provider mock
gitplus worklog list
gitplus history list
gitplus data info
gitplus data backup
gitplus web --no-open
```

运行 `gitplus --help` 或具体子命令的 `--help` 查看所有参数。

## 文档导航

- [项目文档](docs/项目文档.md)：大赛提交版完整说明。
- [快速上手](docs/getting-started.md)：本地演示流程。
- [架构说明](docs/architecture.md)：项目分层与模块职责。
- [安全说明](docs/security.md)：扫描、脱敏与安全边界。
- [智能周报](docs/智能周报.md)：事实来源、生成、编辑和导出流程。
- [Web 控制台](docs/web-console.md)：本地控制台功能和访问方式。
- [配置说明](docs/configuration.md)：配置与 Secret 管理。
- [开发说明](docs/development.md)：开发、测试和构建命令。

## 测试与构建

```bash
pytest
pytest tests/e2e tests/performance
python scripts/check_secrets.py
python -m build
```

## 当前边界

- AI 结果仅作为辅助建议，必须人工审阅。
- SQLite 面向个人和小团队的本地使用场景。
- 安全规则可降低风险，但不能保证发现所有敏感内容。
- 系统不提供远程仓库同步、多人协作、IDE 插件和复杂项目管理功能。
