"""Start the local gitplus Web console."""

from __future__ import annotations

import threading
import webbrowser
from pathlib import Path

from rich.console import Console

from gitplus.config import load_config


def run_web(
    *,
    project: Path,
    port: int | None,
    open_browser: bool,
    debug: bool,
    console: Console,
) -> None:
    """Create and serve the Web app on the loopback interface only."""
    try:
        import uvicorn
    except ImportError as exc:
        raise RuntimeError("Web 依赖未安装，请重新安装 gitplus。") from exc

    from gitplus.web.app import create_app

    root = project.expanduser().resolve()
    if not root.exists() or not root.is_dir():
        raise ValueError(f"项目目录不存在：{root}")
    config = load_config(root)
    selected_port = port if port is not None else config.web.port
    if not 1024 <= selected_port <= 65535:
        raise ValueError("端口必须在 1024 到 65535 之间")
    app = create_app(root)
    token = app.state.sessions.access_token
    address = f"http://127.0.0.1:{selected_port}"
    auth_address = f"{address}/auth/local?token={token}"

    console.print("[bold]gitplus Web 控制台已启动[/bold]\n")
    console.print(f"当前项目：\n{root}\n")
    console.print(f"访问地址：\n{address}\n")
    console.print(f"一次性访问链接：\n{auth_address}\n")
    console.print("按 Ctrl+C 停止服务。")
    if open_browser:
        threading.Timer(0.5, lambda: webbrowser.open(auth_address)).start()
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=selected_port,
        log_level="debug" if debug else config.app.log_level.lower(),
    )
