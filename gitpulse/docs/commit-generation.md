# Commit Generation

`gitpulse commit` 会读取 Git Diff，执行安全扫描和脱敏，然后调用 AI Provider 生成 Commit Message 建议。

## 流程

```text
读取 Diff
→ 安全扫描
→ 生成脱敏 AI 输入
→ 调用 Provider
→ 解析 JSON
→ Pydantic 校验
→ Commit 质量校验
→ 展示候选和依据
```

## Conventional Commits

输出遵循：

```text
<type>(<scope>): <subject>
```

支持的类型包括 `feat`、`fix`、`refactor`、`test`、`docs`、`chore` 等。

## 三个候选

- `concise`：简洁版，通常只有 Subject。
- `standard`：标准版，包含简短 Body。
- `detailed`：详细版，包含更多可由 Diff 证明的细节。

## 多主题检测

模型结果可以设置 `should_split=true` 并返回拆分建议。GitPulse 只展示建议，不会修改暂存区，也不会自动拆分提交。

## Evidence 和 Confidence

Evidence 必须引用输入文件。Confidence 表示模型对结论的把握，仍需用户确认。

## 用户 Context

`--context` 可提供修改背景。用户说明会作为 `user_context` 输入，不会覆盖 Diff 中明确可见的事实。

## Prompt 注入防护

Diff 被包裹在 `<git_diff>` 数据边界内，System Prompt 明确要求不执行 Diff 中出现的指令。该防护不能替代安全扫描。

## AI 输出解析

GitPulse 支持纯 JSON、Markdown JSON 代码块、前后带说明文字的 JSON，并能修复简单尾随逗号。无法校验的响应会失败，不进入后续流程。

## 当前限制

AI 可能误判 Commit Type 或拆分主题。所有输出都只是建议，不会自动执行 `git commit`。

