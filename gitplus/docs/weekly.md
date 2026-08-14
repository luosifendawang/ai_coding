# 周报

周报页面位于 `/weekly`。

周报流程包括数据预览、来源排除、规则或 AI 整理、草稿编辑、来源追踪、确认、重新打开，以及 Markdown/Text/JSON 导出。

## 规则整理

默认的规则整理不会调用 AI。它会先统一清理标题、空白和重复描述；过滤模板内容与信息不足的记录；仅在同一仓库内合并重复来源；然后按主题归入完成事项、问题解决、测试质量、风险和下周计划。

Low 可信内容不会进入正式周报；Medium 可信内容会保留待确认标记。预览页可取消选择任意来源，生成时只使用保留的来源。

正式周报要求来源覆盖率达到 100%。Medium 内容需要用户确认，Low 内容默认不进入正式周报。

更多细节见 [`web-weekly.md`](web-weekly.md)、[`weekly-report.md`](weekly-report.md) 和 [`weekly-data-model.md`](weekly-data-model.md)。
