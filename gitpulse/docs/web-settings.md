# Web 系统配置

## 配置来源

生效顺序为：默认值、兼容用户配置 `~/.gitpulse/config.yml`、用户配置 `~/.config/gitpulse/config.yml`、项目 `.gitpulse.yml`、环境变量和 CLI 参数。

设置页面会显示每个字段的当前来源。保存时可选择用户级或项目级作用域；只写入明确启用“当前作用域覆盖”的字段，取消覆盖会恢复继承值。

## 验证与保存

所有表单配置复用 `GitPulseConfig` 的 Pydantic 校验。保存前提供字段级 Preview；`web.port` 和 Debug 变更会标记为下次启动生效。

每次保存使用同目录临时文件、`fsync` 和原子替换，并先创建时间戳备份。Revision 包含配置路径、内容和修改时间；页面打开后若文件被编辑器或 CLI 修改，保存返回 `409 Conflict`，不会静默覆盖。

PyYAML 保存会保留未知合法字段和字段顺序，但可能无法完整保留 YAML 注释。

## Secret

Web 默认将以下 Secret 写入 `~/.config/gitpulse/secrets.yml`：

```yaml
ai:
  api_key: "..."
feishu:
  app_secret: "..."
```

文件与备份权限为 `0600`。更新操作区分保持、替换和删除；页面加载、API 响应、Preview 与日志均不返回真实值。

AI 测试使用当前未保存表单参数，只发送固定的最小 JSON 请求。飞书连接测试使用 App ID 和 App Secret 获取租户访问令牌，不发送群消息。存储检查验证 SQLite 与报告目录的可读写性，不执行破坏性迁移。
