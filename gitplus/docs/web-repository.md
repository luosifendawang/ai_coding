# Web Git 工作台

运行 `gitplus web --project /path/to/repository`，通过一次性本地链接进入
控制台，然后打开“Git 工作台”。

工作台按冲突、已暂存、未暂存和未跟踪显示文件。部分暂存文件会同时出现在
已暂存与未暂存分组，并显示 Index/Worktree 双状态。文件列表按需加载暂存或
未暂存 Diff；未跟踪文本文件使用受限只读预览，二进制文件不返回原始内容，
大文件和大 Diff 会截断。

暂存和取消暂存支持单文件及批量文件。前端发送明确的相对路径数组，后端不会
执行 `git add .`。每次写操作都携带仓库 Revision；HEAD、分支或状态变化后，
旧 Revision 会收到 `409 repository_changed`，需要刷新后重试。

无初始 Commit 的仓库可以安全取消暂存，工作区文件不会被删除。Detached HEAD
可以查看 Diff 和暂存，但默认禁止 Web Commit。存在冲突时允许查看状态和 Diff，
但禁止生成 Message 和 Commit。

当前不支持 Push、Pull、Fetch、Reset、Clean、Rebase、合并、分支管理或冲突
自动解决。
