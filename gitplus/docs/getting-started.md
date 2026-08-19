# 快速上手

本指南使用 mock Provider，不需要配置远程模型服务。

```bash
pip install -e ".[dev]"
gitplus --version
gitplus doctor
```

进入一个 Git 仓库后，按以下顺序体验核心流程：

```bash
gitplus init
git add <files>
gitplus check --staged
gitplus commit --provider mock
gitplus worklog add --yes --type development --title "完成核心功能"
gitplus web
```

浏览器打开本地访问链接后，可在 Git 工作台查看改动、管理工作日志、查询历史，并通过“智能周报助手”选择事实来源、生成和导出周报。

gitplus 不会在未经用户明确确认的情况下执行 `git add`、`git commit` 或 `git push`。
