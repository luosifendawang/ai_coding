# History

History 用于查看 GitPulse 保存的 Commit 工作记录。

## Commit 工作记录

`gitpulse commit --save` 会在生成 Commit Message 后保存用户选择的标准候选。

```bash
gitpulse commit --provider mock --save
```

GitPulse 只保存工作记录，不执行 `git commit`。

## 查询

```bash
gitpulse history
gitpulse history list --type fix --confidence high
gitpulse history list --search usb
gitpulse history list --json
```

## 详情

```bash
gitpulse history show <id>
```

## 隐私

History 不展示原始完整 Diff、原始 Secret、Provider 请求头或完整 AI 原始响应。

## Commit Hash 关联

本阶段保存记录时 `commit_hash` 可以为空。后续可增加关联已有 Git Commit 的命令。

## 当前限制

当前搜索使用 SQL `LIKE`，尚未启用 SQLite FTS。删除 Commit 工作记录 CLI 留到后续增强。

