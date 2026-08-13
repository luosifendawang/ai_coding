# Web Git 安全边界

Git 工作台在服务启动时固定唯一仓库根目录，API 不接受 `cwd` 或仓库路径。
所有 Git 命令由后端白名单构造，使用参数数组且不启用 Shell。

文件路径必须满足：

- 非空相对路径，不能以 `-` 开头
- 不包含空字节、`..` 或 `.git`
- 解析后仍位于固定仓库内
- 符号链接不能逃逸仓库
- 必须存在于当前 Git 状态
- 路径参数前始终使用 `--`

所有写 API 需要本地 Session、同源校验和 CSRF Token。Stage、Unstage 和 Commit
使用仓库级进程锁，并在执行前校验 Revision。路径数组最多 500 项，任一非法
路径会使整个请求失败。

Diff 受文件字节和字符上限约束，二进制内容不会进入浏览器。Diff 展示和 AI
调用前复用现有敏感信息扫描与遮盖规则；High 和 Critical 风险阻止远程 AI。
日志和操作审计不保存完整 Diff、Secret、Session、CSRF、Cookie、AI Prompt
或 Authorization Header。

Commit Message 通过仓库外临时文件传递，文件权限为 `0600`，成功或失败后都会
删除。Git Hook 不会被绕过。本阶段明确禁止 Push、Pull、Reset、Clean、Rebase、
任意 Shell 命令和 Web 终端。
