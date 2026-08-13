# Git 工作台

Git 工作台位于 `/repository`。

它支持查看仓库状态、按需加载 Diff、暂存或取消暂存文件、安全扫描、Mock 或 OpenAI-compatible Commit Message 生成，以及用户确认后的本地 Commit。

安全边界：

- 不提供 Push、Pull、Reset、Rebase。
- 所有 Git 写操作都需要仓库 Revision 校验。
- 文件路径必须来自当前仓库状态，禁止路径逃逸和 Git 参数注入。
- High 和 Critical 风险会阻止远程 AI。

更多实现细节见 [`web-repository.md`](web-repository.md) 和 [`web-commit-assistant.md`](web-commit-assistant.md)。
