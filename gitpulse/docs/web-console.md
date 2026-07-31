# 本地 Web 控制台

## 启动

```bash
gitpulse web
gitpulse web --port 8765
gitpulse web --no-open
gitpulse web --project /path/to/repository
```

服务固定监听 `127.0.0.1`，默认端口为 `8765`。默认启动浏览器，并通过一次性本地 Token 建立 Session；使用 `--no-open` 时请手动打开终端显示的一次性访问链接。

按 `Ctrl+C` 停止服务。服务重启后旧 Session 自动失效。

## 当前页面

- 仪表盘：显示版本、项目、配置、AI、飞书和存储状态。
- 系统配置：查看来源、验证、预览、保存、恢复备份和执行连接检查。

当前不提供 Git 状态、Diff、暂存、Commit、Worklog、周报编辑或飞书正式发送页面。
