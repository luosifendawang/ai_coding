# 安装

推荐使用 pipx 全局安装：

```bash
pipx install gitplus
cd your-project
gitplus init
gitplus web
```

开发模式：

```bash
pipx install --editable .
```

gitplus 会根据当前目录通过 `git rev-parse --show-toplevel` 自动识别仓库，不依赖源码目录。

Web 控制台只监听 `127.0.0.1`，启动后终端会显示一次性访问链接。

发布前本地验证：

```bash
pytest
ruff check .
mypy src
python -m build
gitplus release-check
```
