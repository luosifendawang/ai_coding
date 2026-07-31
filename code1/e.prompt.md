# GitPulse Web 控制台第五阶段：飞书通知中心

继续开发现有 GitPulse 项目。

当前已经完成：

* Web 系统配置中心
* Git 工作台与 Commit 助手
* Worklog 与工作历史
* 周报生成、编辑、确认与导出

本阶段只开发：

```text
飞书配置状态
消息预览
Webhook 机器人
应用机器人
周报发送
发送记录
失败重试
重复发送保护
```

不要重新初始化项目，不要重写现有周报、数据库和飞书 Webhook Service。

## 一、目标

用户能够在 Web 页面中：

1. 查看飞书配置状态
2. 选择 Webhook 或应用机器人模式
3. 发送测试消息
4. 预览周报消息
5. 选择文本或消息卡片
6. 确认发送正式周报
7. 查看发送结果
8. 查看发送历史
9. 对失败记录执行重试
10. 防止同一周报重复发送

## 二、页面

新增：

```text
/notifications
/notifications/{id}
```

导航增加：

```text
Git 工作台
Worklog
工作历史
周报
飞书通知
系统配置
```

页面显示：

* 飞书连接状态
* 当前机器人模式
* 已确认周报列表
* 消息预览
* 发送确认
* 最近发送记录
* 失败记录

## 三、机器人模式

支持两种模式：

```yaml
feishu:
  mode: webhook
```

或：

```yaml
feishu:
  mode: app
```

### Webhook 模式

配置：

```yaml
feishu:
  mode: webhook
  webhook: "..."
  secret: "..."
```

继续复用现有 Webhook 签名和发送逻辑。

### 应用机器人模式

配置：

```yaml
feishu:
  mode: app
  app_id: "cli_xxx"
  app_secret: "..."
  receive_id_type: chat_id
  receive_id: "oc_xxx"
```

实现：

* 获取 `tenant_access_token`
* Token 缓存
* Token 到期自动刷新
* 使用 `chat_id` 或其他支持的目标 ID 发送消息
* 401 或 Token 失效时刷新后重试一次

App Secret、Webhook 和签名 Secret 不得返回前端或写入日志。

## 四、API

实现：

```http
GET  /api/notifications/config-status
POST /api/notifications/test
POST /api/notifications/preview
POST /api/notifications/send
GET  /api/notifications
GET  /api/notifications/{id}
POST /api/notifications/{id}/retry
```

所有写接口必须验证：

* Session
* CSRF
* 飞书配置有效
* 周报存在
* 周报状态为 `confirmed`
* 用户明确确认发送
* 消息大小未超过限制

## 五、消息预览

预览接口请求：

```json
{
  "report_id": "report_xxx",
  "message_type": "interactive"
}
```

支持：

```text
text
interactive
```

预览页面应显示实际发送内容，但不得显示：

* Webhook
* App Secret
* Access Token
* Authorization Header

消息卡片至少包含：

* 周报标题
* 日期范围
* 本周完成
* 问题与解决
* 下周计划
* 来源覆盖率

内容过长时自动压缩或拆分，并显示提示。

## 六、发送流程

发送正式周报必须经过：

```text
选择已确认周报
    ↓
生成消息预览
    ↓
执行最终敏感信息扫描
    ↓
检查重复发送
    ↓
用户确认
    ↓
调用飞书 Provider
    ↓
保存发送记录
    ↓
更新周报状态
```

发送确认框必须显示：

* 周报标题
* 日期范围
* 机器人模式
* 目标群标识
* 消息类型
* 是否可能重复发送

目标群只显示脱敏标识。

## 七、重复发送保护

为每次发送生成指纹：

```text
report_id
+
报告版本
+
目标标识
+
消息类型
+
消息正文哈希
```

使用 SHA-256。

默认禁止相同内容重复发送。

检测到重复时返回：

```text
该版本周报已发送到相同目标。
```

只有用户明确选择“允许重复发送”并再次确认后才能继续。

## 八、发送记录

记录至少包括：

* Notification ID
* Report ID
* 报告版本
* Provider 模式
* 消息类型
* 目标标识摘要
* 内容指纹
* 状态
* 尝试次数
* HTTP 状态摘要
* 飞书消息 ID
* 创建时间
* 发送时间
* 错误类型

状态支持：

```text
pending
sending
sent
failed
unknown
duplicate_blocked
```

不得保存完整 Access Token 或 Secret。

## 九、错误和重试

可重试错误：

* 网络失败
* 请求超时
* HTTP 429
* HTTP 5xx
* Access Token 失效

不可自动重试：

* 配置错误
* 权限不足
* 消息格式错误
* 目标 ID 错误
* 安全扫描阻断

自动重试最多两次，并采用退避等待。

如果请求超时但无法确认飞书是否收到，状态设为：

```text
unknown
```

不要自动再次发送，避免重复消息。

## 十、安全要求

必须做到：

* 只允许发送已确认周报
* 发送前再次进行敏感信息扫描
* High 或 Critical 风险阻止发送
* 所有凭证在 API 中脱敏
* 日志不记录消息完整正文
* 不记录 Authorization Header
* 不信任前端提供的目标地址
* Webhook Host 必须校验
* App 模式目标 ID 必须来自配置
* 重试操作需要用户确认
* 不允许前端提交任意请求 URL

## 十一、测试

至少覆盖：

* Webhook 签名
* Webhook 成功发送
* App Token 获取
* App Token 缓存和刷新
* App 消息发送
* 测试消息
* 文本预览
* 卡片预览
* 未确认周报阻止发送
* 敏感内容阻止发送
* 重复发送阻止
* 用户确认重复发送
* 429 和 5xx 重试
* 401 刷新 Token
* 超时后的 unknown 状态
* 失败记录重试
* Session 和 CSRF
* Secret 不进入响应和日志

所有外部飞书请求必须使用 Mock。

## 十二、验收标准

完成后必须满足：

1. 支持 Webhook 机器人。
2. 支持 App ID/App Secret 应用机器人。
3. 能发送测试消息。
4. 能预览文本和消息卡片。
5. 只能发送已确认周报。
6. 发送前执行安全扫描。
7. 能防止重复发送。
8. 能查看发送记录。
9. 能重试明确失败的记录。
10. 超时不明确时不会自动重复发送。
11. 不泄露任何飞书凭证。
12. Pytest、Ruff 和 Mypy 通过。

## 十三、开发顺序

```text
1. 检查现有 Feishu Webhook Service
2. 抽象统一 FeishuProvider 接口
3. 保留 WebhookProvider
4. 实现 AppProvider 和 TokenService
5. 实现消息预览
6. 实现发送记录和状态机
7. 实现重复发送指纹
8. 实现正式发送 API
9. 实现失败重试
10. 完成飞书通知页面
11. 编写单元、集成和 E2E 测试
12. 执行全部测试
13. 更新文档
```

本阶段完成前，不要开发 Push、Pull、Reset、Rebase 或远程服务器部署。

完成后输出：

```text
完成内容
支持的机器人模式
新增 API
新增页面
Token 缓存方式
重复发送保护
发送状态设计
测试结果
安全验证
已知限制
下一阶段建议
```

下一阶段为：

```text
Web 控制台集成验收、仪表盘、性能优化和正式发布
```
