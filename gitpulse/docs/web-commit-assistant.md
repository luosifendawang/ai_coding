# Web Commit 助手

Commit 助手针对当前暂存区执行完整流程：

1. 使用现有 `SecurityService` 扫描暂存 Diff。
2. 将 Scan ID 与仓库 Revision 绑定，有效期为 15 分钟。
3. High 或 Critical 风险阻止远程 AI，页面只显示固定遮盖预览。
4. 使用现有 `CommitService` 生成简洁、标准和详细候选。
5. 用户选择候选并编辑 Subject、Body 和 Footer。
6. 最终确认框展示仓库、分支、暂存文件数和完整 Message。
7. 使用权限为 `0600` 的临时文件执行 `git commit -F`。
8. Commit 成功后保存 CommitRecord、Commit Hash、安全摘要和用户编辑记录。

生成结果同样与 Revision 和 Scan 绑定。仓库发生变化、扫描过期或生成结果过期
后必须重新扫描和生成。有效 Git Identity 使用 Git 自身配置优先级读取：
仓库级优先，其次全局和系统级；完全缺失时阻止 Commit 并提示配置。

Git Hook 会正常执行，GitPulse 不使用 `--no-verify`。Hook 拒绝提交时页面显示
受限错误并刷新状态。Web Commit 只创建本地 Commit，永远不会自动 Push。
