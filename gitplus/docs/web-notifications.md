# gitplus Web 飞书通知中心

飞书通知中心用于把已确认周报发送到飞书，并保留发送记录。入口：

- `/notifications`
- `/notifications/{notification_id}`

## 机器人模式

Webhook 机器人：

```yaml
feishu:
  enabled: true
  mode: webhook
  webhook: "https://open.feishu.cn/open-apis/bot/v2/hook/..."
  secret: "..."
```

应用机器人：

```yaml
feishu:
  enabled: true
  mode: app
  app_id: "cli_xxx"
  app_secret: "..."
  receive_id_type: chat_id
  receive_id: "oc_xxx"
```

`webhook`、`secret`、`app_secret`、`tenant_access_token` 不会返回给前端，也不会写入发送记录。前端只显示脱敏目标和目标摘要。

## 发送流程

发送正式周报前必须满足：

- 本地 Session 与 CSRF 校验通过
- 飞书配置已启用且完整
- 周报已确认
- 消息大小未超过 `feishu.max_json_bytes`
- 最终敏感信息扫描未发现高风险内容
- 用户明确确认发送

同一周报版本、同一目标、同一消息类型、同一消息正文会生成 SHA-256 指纹。默认禁止重复发送，并返回：

```text
该版本周报已发送到相同目标。
```

只有用户勾选允许重复发送并再次确认后，才会继续发送。

## 发送记录

记录会保存通知 ID、周报 ID、报告版本、机器人模式、消息类型、目标摘要、内容指纹、状态、尝试次数、HTTP 状态摘要、飞书消息 ID、创建时间和更新时间。

失败或未知状态的记录可以在详情页重试。重试会复用原消息类型并重新生成当前周报消息。
