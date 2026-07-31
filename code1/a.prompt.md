# GitPulse 本地 Web 控制台第一阶段开发提示词：系统配置中心

你正在继续开发 **GitPulse——代码工作成果助手**。

当前 GitPulse 已经是一个可运行的本地 CLI 项目，已经具备或正在具备：

* Git 仓库识别
* Git Diff 和 Git Log 读取
* 敏感信息扫描
* AI Commit Message 生成
* Commit 工作记录
* Worklog 管理
* 周报生成
* SQLite 数据存储
* 飞书机器人通知
* 配置加载与 Pydantic 校验

现在开始开发 **本地 Web 控制台**。

本阶段只实现：

```text
Web 控制台基础框架
+
系统配置中心
```

不要在本阶段实现 Git Add、Git Commit、Worklog、周报编辑或飞书发送页面。

请直接在现有仓库中继续开发。

不要重新初始化项目，不要重写现有 CLI，不要复制已有 Service 逻辑。

---

# 一、本阶段目标

实现一个只运行在本机的 GitPulse Web 控制台。

用户能够通过浏览器完成：

```text
启动 GitPulse Web 服务
    ↓
安全进入本地控制台
    ↓
查看当前生效配置
    ↓
区分默认、用户级、项目级配置
    ↓
修改系统配置
    ↓
执行配置校验
    ↓
查看配置变更预览
    ↓
确认保存
    ↓
原子写入配置文件
    ↓
重新加载配置
    ↓
测试 AI 或飞书连接
```

本阶段必须完成：

1. FastAPI Web 应用
2. `gitpulse web` CLI 命令
3. 本地访问安全控制
4. 系统配置页面
5. 配置读取 API
6. 配置更新 API
7. 配置来源展示
8. 配置优先级展示
9. Pydantic 配置校验
10. 保存前变更预览
11. 原子写入
12. 自动备份
13. 并发修改检测
14. API Key 和飞书凭证安全处理
15. AI 配置测试
16. 飞书配置基础测试
17. 数据库和目录配置检查
18. Web 单元测试
19. API 集成测试
20. 页面端到端测试

---

# 二、本阶段明确不实现

暂不实现：

* Git 状态页面
* 文件 Diff 页面
* `git add`
* `git restore --staged`
* `git commit`
* 分支切换
* Worklog 页面
* 周报页面
* 飞书正式发送页面
* 通知历史页面
* 任意 Shell 命令输入框
* 用户账号系统
* 云端部署
* 多用户访问
* 外网访问
* 远程仓库管理
* WebSocket
* 后台定时任务
* Git Hook
* IDE 插件

系统配置页面完成并验收后，再开发 Web Git 工作台。

---

# 三、技术方案

后端使用：

```text
FastAPI
Pydantic 2
现有 GitPulse Config Loader
现有 Service 层
现有异常体系
```

页面优先使用：

```text
Jinja2
原生 JavaScript
本地 CSS
```

可以使用 HTMX，但必须将资源打包到本地。

禁止依赖公共 CDN。

本阶段不要引入 React、Vue、Vite 或大型 Node 构建链，除非当前项目已经存在完整前端工程。

首版目标是：

```text
启动简单
离线可用
依赖少
容易调试
```

---

# 四、开始前检查

首先执行：

```bash
git status
```

```bash
gitpulse --help
```

```bash
pytest
```

如果项目配置了质量工具，同时执行：

```bash
ruff check .
```

```bash
mypy src
```

然后检查现有配置代码：

```text
src/gitpulse/config.py
src/gitpulse/models/config.py
src/gitpulse/services/
```

确认：

1. 当前配置模型的真实位置。
2. 当前配置文件路径。
3. 是否支持用户级配置。
4. 是否支持项目级 `.gitpulse.yml`。
5. 当前配置优先级。
6. `AIConfig` 是否已经支持 `api_key`。
7. 飞书配置是否支持 Webhook 和 Secret。
8. 配置加载函数是否有缓存。
9. 配置更新后如何重新加载。
10. 当前异常类型和日志方式。

不要创建第二套与 CLI 不一致的配置模型。

Web 和 CLI 必须共享同一套配置定义。

---

# 五、建议目录结构

新增：

```text
src/gitpulse/web/
├── __init__.py
├── app.py
├── dependencies.py
├── security.py
├── sessions.py
├── errors.py
├── schemas/
│   ├── __init__.py
│   ├── config.py
│   └── common.py
├── routes/
│   ├── __init__.py
│   ├── pages.py
│   ├── config_api.py
│   └── health_api.py
├── services/
│   ├── __init__.py
│   ├── config_web_service.py
│   ├── config_diff_service.py
│   ├── connection_test_service.py
│   └── config_backup_service.py
├── templates/
│   ├── base.html
│   ├── index.html
│   ├── settings.html
│   ├── components/
│   │   ├── alerts.html
│   │   ├── config_source.html
│   │   ├── secret_input.html
│   │   └── validation_errors.html
│   └── errors/
│       ├── 403.html
│       ├── 404.html
│       └── 500.html
└── static/
    ├── css/
    │   └── app.css
    └── js/
        ├── app.js
        └── settings.js
```

CLI 增加：

```text
src/gitpulse/commands/web.py
```

测试：

```text
tests/unit/web/
├── test_web_security.py
├── test_web_sessions.py
├── test_config_web_service.py
├── test_config_diff_service.py
├── test_config_backup_service.py
└── test_connection_test_service.py
```

```text
tests/integration/web/
├── test_web_app.py
├── test_config_api.py
├── test_config_update_api.py
├── test_secret_api.py
├── test_ai_test_api.py
└── test_feishu_test_api.py
```

```text
tests/e2e/web/
└── test_settings_page.py
```

---

# 六、Web 服务启动命令

实现：

```bash
gitpulse web
```

支持：

```bash
gitpulse web --port 8765
gitpulse web --no-open
gitpulse web --project /path/to/repository
gitpulse web --debug
```

默认行为：

```text
Host：127.0.0.1
Port：8765
自动打开浏览器：是
允许外部访问：否
```

启动输出：

```text
GitPulse Web 控制台已启动

当前项目：
/home/user/projects/example

访问地址：
http://127.0.0.1:8765

按 Ctrl+C 停止服务。
```

必须使用：

```python
uvicorn.run(
    app,
    host="127.0.0.1",
    port=port,
)
```

禁止默认监听：

```text
0.0.0.0
```

如果用户尝试传入其他 Host，本阶段直接拒绝。

不要提供：

```bash
gitpulse web --host 0.0.0.0
```

---

# 七、本地访问安全

即使服务只监听本机，也不能假设绝对安全。

至少实现：

1. 随机启动令牌
2. 安全 Session Cookie
3. CSRF 防护
4. Host Header 校验
5. 禁止跨域请求
6. SameSite Cookie
7. 来源校验
8. API 写操作鉴权

推荐启动流程：

```text
启动 Web 服务
    ↓
生成随机一次性访问 Token
    ↓
浏览器访问 /auth/local?token=...
    ↓
服务校验 Token
    ↓
设置 HttpOnly Session Cookie
    ↓
重定向到 /
```

令牌生成：

```python
import secrets

token = secrets.token_urlsafe(32)
```

Session Cookie 建议：

```text
HttpOnly=true
SameSite=Strict
Secure=false
```

因为默认是本地 HTTP，所以 `Secure=false`。

如果未来支持 HTTPS，再启用 Secure。

Session 不得写入数据库。

服务重启后 Session 失效是可以接受的。

---

# 八、禁止直接开放配置 API

以下请求必须验证 Session：

```text
GET    /api/config
GET    /api/config/effective
GET    /api/config/sources
POST   /api/config/validate
POST   /api/config/preview
PUT    /api/config
POST   /api/config/test-ai
POST   /api/config/test-feishu
```

未授权请求返回：

```http
403 Forbidden
```

不要在错误中返回本地文件内容。

---

# 九、Host 和 Origin 校验

允许的 Host：

```text
127.0.0.1
localhost
[::1]
```

允许带当前实际端口。

拒绝：

```text
example.com
192.168.x.x
任意外部 Host
```

写操作同时检查：

```text
Origin
Referer
CSRF Token
```

禁止配置宽松 CORS：

```python
allow_origins=["*"]
```

推荐本阶段不启用 CORS。

---

# 十、系统配置页面结构

系统配置页面路径：

```text
/settings
```

页面分组：

```text
常规设置
AI 设置
安全设置
Git 设置
存储设置
周报设置
飞书设置
Web 设置
配置来源
```

页面顶部展示：

```text
当前项目：ai_coding
项目配置：/path/to/project/.gitpulse.yml
用户配置：~/.config/gitpulse/config.yml
最后加载时间：...
配置状态：有效
```

按钮：

```text
重新加载
验证配置
预览变更
保存配置
恢复上次备份
```

---

# 十一、配置作用域

支持三类来源：

```text
默认配置
用户级配置
项目级配置
```

环境变量和 CLI 参数只展示为覆盖来源，不通过页面直接修改。

配置优先级：

```text
默认值
    ↓
用户级配置
    ↓
项目级配置
    ↓
环境变量
    ↓
CLI 参数
```

页面需要显示每个字段的当前来源。

示例：

```text
AI 模型
当前值：deepseek-chat
来源：项目配置

API Key
状态：已配置
来源：项目配置中的本地凭证

数据库路径
当前值：~/.gitpulse/data.db
来源：用户配置
```

不要向页面返回完整 Secret。

---

# 十二、配置保存范围

页面顶部必须允许用户选择保存范围：

```text
保存到用户级配置
保存到当前项目配置
```

默认推荐：

```text
普通偏好 → 用户级配置
项目特有设置 → 项目级配置
```

项目级配置路径：

```text
<repository>/.gitpulse.yml
```

用户级配置路径建议使用系统配置目录：

```text
~/.config/gitpulse/config.yml
```

Windows 路径由平台目录库处理。

本阶段 Ubuntu 优先，但代码不得写死 `/home/...`。

推荐使用：

```text
platformdirs
```

或项目已有目录策略。

---

# 十三、常规设置

常规设置至少包括：

```yaml
app:
  language: zh-CN
  timezone: Asia/Shanghai
  log_level: INFO
```

支持字段：

* 显示语言
* 时区
* 日志级别
* 是否显示详细错误
* 是否自动打开浏览器

要求：

* 时区必须校验
* 日志级别使用枚举
* Debug 模式需要显著警告
* 页面修改日志级别不能泄露 Secret
* 语言首版可以只支持 `zh-CN`

---

# 十四、AI 设置

AI 设置至少包括：

```yaml
ai:
  provider: openai-compatible
  model: deepseek-chat
  base_url: https://api.example.com/v1
  api_key_env: GITPULSE_API_KEY
  is_local: false
  temperature: 0.2
  top_p: 0.8
  timeout_seconds: 60
  max_retries: 2
  max_output_tokens: 8192
```

页面字段：

* Provider
* Base URL
* Model
* 本地模型开关
* Temperature
* Top P
* Timeout
* Retry
* Max Output Tokens
* Thinking 模式配置
* API Key 保存方式

---

# 十五、AI 凭证模式

为兼顾方便和安全，提供两种方式：

```text
环境变量模式
本地配置模式
```

## 环境变量模式

保存：

```yaml
api_key_env: GITPULSE_API_KEY
```

页面只显示：

```text
环境变量名称：GITPULSE_API_KEY
状态：已设置 / 未设置
```

不得显示环境变量值。

## 本地配置模式

允许用户在 Web 页面输入 API Key。

但必须满足：

1. 默认密码输入框。
2. 页面加载时不返回已有 Key。
3. 已存在时只显示“已配置”。
4. 用户不修改时保留原值。
5. 用户明确选择“删除凭证”才清空。
6. 日志中不输出 Key。
7. API 响应中不输出 Key。
8. 配置 Diff 中显示 `********`。
9. 配置文件权限设置为 `600`。
10. 项目级明文 Key 保存前必须显示风险警告。
11. 默认建议保存到用户级凭证文件。
12. `.gitpulse.yml` 被 Git 跟踪时阻止保存明文 Key。

推荐将本地 Secret 存入：

```text
~/.config/gitpulse/secrets.yml
```

而不是项目 `.gitpulse.yml`。

结构：

```yaml
ai:
  api_key: "..."
```

飞书凭证：

```yaml
feishu:
  webhook: "..."
  secret: "..."
```

文件权限：

```text
0600
```

如果现有项目已经直接支持 `.gitpulse.yml` 中的 `ai.api_key`，保持兼容，但 Web 页面默认使用用户级 Secret 文件。

---

# 十六、Secret 更新语义

前端不能通过普通空字符串误删 Secret。

请求模型需要区分：

```text
不修改
设置新值
删除
```

建议：

```python
class SecretUpdateAction(str, Enum):
    KEEP = "keep"
    REPLACE = "replace"
    DELETE = "delete"


class SecretUpdate(BaseModel):
    action: SecretUpdateAction
    value: SecretStr | None = None
```

规则：

* `keep`：不读取 `value`
* `replace`：`value` 必填
* `delete`：清除当前 Secret
* 不允许 `replace` 但值为空
* 响应永远不返回真实值

---

# 十七、安全设置

页面支持：

```yaml
security:
  enabled: true
  block_remote_on_high_risk: true
  block_remote_on_scan_failure: true
  mask_medium_risk: true
```

至少包括：

* 是否启用扫描
* High 是否阻止远程 AI
* Critical 是否阻止所有 AI
* 扫描失败是否阻止 AI
* 是否扫描删除行
* 是否扫描 Worklog
* 是否扫描周报
* 自定义忽略路径
* 自定义规则开关

禁止用户通过普通页面关闭所有 Critical 规则。

如果允许关闭安全扫描，必须显示强警告：

```text
关闭安全扫描可能将 Token、密码或私钥发送到远程模型。
```

并要求二次确认。

推荐 MVP 中：

```text
Critical 规则不可关闭
```

---

# 十八、Git 设置

本阶段只配置，不执行 Git 写操作。

页面展示：

```yaml
git:
  default_diff_source: staged
  include_merge_commits: false
  max_file_chars: 20000
  max_total_chars: 60000
  ignore_patterns: []
```

字段：

* 默认分析 Staged 或 Unstaged
* 是否包含 Merge Commit
* 单文件最大字符数
* 总 Diff 最大字符数
* 忽略文件模式
* 默认 Commit 语言
* Subject 最大长度
* 是否生成 Body
* 是否启用拆分建议

所有数值必须有边界校验。

---

# 十九、存储设置

页面展示：

```yaml
storage:
  database: ~/.gitpulse/data.db
  report_dir: ./reports
  auto_initialize: true
  store_raw_diff: false
  retention_days: null
```

字段：

* SQLite 路径
* 周报输出目录
* 是否自动初始化
* 是否保存文件列表
* 是否保存 Diff 摘要
* 是否保存原始 Diff
* 数据保留天数

要求：

* 默认不保存原始 Diff
* 开启原始 Diff 存储时必须警告
* 只能保存脱敏后的 Diff
* 数据库路径必须可写
* 报告目录必须可创建
* 路径预览显示解析后的绝对路径
* 不允许数据库路径指向目录
* 不允许报告目录位于 `.git` 中
* 不允许通过 `../` 逃逸项目限制，除非是用户级合法绝对路径

---

# 二十、周报设置

页面支持：

```yaml
weekly:
  week_start: monday
  timezone: Asia/Shanghai
  include_uncommitted: false
  include_merge_commits: false
  output_language: zh-CN
  include_sources: true
  exclude_low_confidence: true
  require_medium_confirmation: true
```

字段：

* 一周开始日
* 时区
* 是否包含未提交变更
* 是否包含 Merge Commit
* 输出语言
* 是否显示来源
* 是否排除 Low
* Medium 是否需要确认
* 最大 Commit 数
* 最大 Worklog 数
* 最大 Topic 数

不得允许关闭正式周报来源校验。

---

# 二十一、飞书设置

页面支持：

```yaml
feishu:
  enabled: false
  message_type: interactive
  require_confirmation: true
  allow_duplicate_send: false
  include_sources: false
  duplicate_window_hours: 168
```

字段：

* 是否启用
* 消息类型
* 是否发送前确认
* 是否允许重复
* 是否显示来源
* 重复检查时间窗口
* Webhook
* Secret

Webhook 和 Secret 使用与 API Key 相同的 Secret 更新模型。

页面加载时：

```text
Webhook：已配置
Secret：已配置
```

不得返回部分真实 Webhook Token。

可以显示 Host：

```text
open.feishu.cn
```

---

# 二十二、Web 设置

页面支持：

```yaml
web:
  port: 8765
  auto_open_browser: true
  session_timeout_minutes: 120
```

Host 本阶段固定：

```text
127.0.0.1
```

页面可以显示但不能修改。

字段：

* 默认端口
* 是否自动打开浏览器
* Session 超时
* 是否显示高级配置
* 是否启用调试模式

修改端口后提示：

```text
配置将在下次启动 Web 服务时生效。
```

---

# 二十三、配置读取 API

实现：

```http
GET /api/config/effective
```

返回：

```json
{
  "config": {
    "app": {},
    "ai": {},
    "security": {},
    "git": {},
    "storage": {},
    "weekly": {},
    "feishu": {},
    "web": {}
  },
  "sources": {
    "ai.model": "project",
    "weekly.timezone": "user",
    "storage.database": "default"
  },
  "secrets": {
    "ai.api_key": {
      "configured": true,
      "source": "user_secret"
    },
    "feishu.webhook": {
      "configured": false,
      "source": null
    }
  },
  "revision": "sha256:..."
}
```

响应不得包含：

* API Key
* 飞书 Webhook 完整值
* 飞书 Secret
* 环境变量真实值
* 完整数据库连接 Secret
* Authorization Header

---

# 二十四、配置来源 API

实现：

```http
GET /api/config/sources
```

返回：

```json
{
  "default": {
    "exists": true
  },
  "user": {
    "path": "~/.config/gitpulse/config.yml",
    "exists": true,
    "writable": true
  },
  "project": {
    "path": "/project/.gitpulse.yml",
    "exists": true,
    "writable": true,
    "tracked_by_git": false
  },
  "secrets": {
    "path": "~/.config/gitpulse/secrets.yml",
    "exists": true,
    "permission_secure": true
  }
}
```

路径可以展示给本地用户，但日志中仍需谨慎。

---

# 二十五、配置验证 API

实现：

```http
POST /api/config/validate
```

请求：

```json
{
  "scope": "project",
  "config": {},
  "secret_updates": {}
}
```

响应成功：

```json
{
  "valid": true,
  "warnings": [],
  "normalized_config": {}
}
```

响应失败：

```json
{
  "valid": false,
  "errors": [
    {
      "path": "ai.timeout_seconds",
      "message": "必须大于 0"
    }
  ]
}
```

验证必须复用现有 Pydantic Config 模型。

不要在 Web 路由中手写第二套字段校验。

---

# 二十六、配置变更预览

实现：

```http
POST /api/config/preview
```

返回字段级 Diff：

```json
{
  "changes": [
    {
      "path": "ai.model",
      "old": "old-model",
      "new": "new-model",
      "source": "project"
    },
    {
      "path": "ai.api_key",
      "old": "********",
      "new": "********",
      "source": "user_secret"
    }
  ],
  "warnings": [
    "修改 AI Base URL 后需要重新测试连接"
  ],
  "restart_required": [
    "web.port"
  ]
}
```

Secret 变更只能显示：

```text
未配置 → 已配置
已配置 → 已替换
已配置 → 已删除
```

禁止显示 Secret 长度、前缀或后缀。

---

# 二十七、配置保存 API

实现：

```http
PUT /api/config
```

请求必须包含：

```json
{
  "scope": "project",
  "config": {},
  "secret_updates": {},
  "revision": "sha256:...",
  "confirmed": true
}
```

处理顺序：

```text
验证 Session
    ↓
验证 CSRF
    ↓
检查 Revision
    ↓
读取最新配置
    ↓
合并本次修改
    ↓
Pydantic 校验
    ↓
安全规则校验
    ↓
生成备份
    ↓
写入临时文件
    ↓
重新读取并校验
    ↓
原子替换
    ↓
设置文件权限
    ↓
清除配置缓存
    ↓
重新加载配置
    ↓
返回新 Revision
```

任何一步失败：

* 原配置保持不变
* Secret 文件保持一致
* 返回可理解错误
* 不留下不完整临时文件

---

# 二十八、原子写入

推荐：

```text
config.yml.tmp
    ↓
写入
    ↓
flush
    ↓
fsync
    ↓
重新解析验证
    ↓
os.replace
```

配置和 Secret 是两个文件时，需要处理一致性。

推荐顺序：

1. 创建两个文件的备份
2. 写入两个临时文件
3. 验证两个临时文件
4. 替换 Secret
5. 替换 Config
6. 重新加载
7. 失败时恢复备份

需要测试中途失败场景。

---

# 二十九、自动备份

每次保存前备份：

```text
.gitpulse.yml.bak.20260729-103000
config.yml.bak.20260729-103000
secrets.yml.bak.20260729-103000
```

配置：

```yaml
web:
  config_backup_count: 10
```

只保留最近 N 个备份。

Secret 备份必须保持：

```text
0600
```

不要将 Secret 备份放入项目仓库。

项目级 Config 备份是否加入 `.gitignore`，需要在初始化时处理。

---

# 三十、并发修改检测

用户打开页面后，配置文件可能被 CLI 或编辑器修改。

使用 Revision：

```text
文件内容
+
文件路径
+
修改时间
```

生成 SHA-256。

保存时 Revision 不一致：

```http
409 Conflict
```

响应：

```json
{
  "error": "config_changed",
  "message": "配置文件已被其他程序修改，请重新加载后再保存。"
}
```

禁止静默覆盖外部修改。

---

# 三十一、YAML 注释与未知字段

优先保留：

* YAML 注释
* 字段顺序
* 当前版本未知字段

可以使用：

```text
ruamel.yaml
```

如果项目当前使用 PyYAML 且切换成本过高，至少做到：

1. 保留未知合法字段。
2. 不删除尚未被 Web 页面识别的配置。
3. 保存前展示完整变更。
4. 在文档中说明注释可能无法完全保留。

不要直接执行：

```python
yaml.safe_dump(config.model_dump())
```

覆盖整个文件并丢失所有未知配置。

---

# 三十二、AI 连接测试

实现：

```http
POST /api/config/test-ai
```

测试使用当前表单中尚未保存的配置。

处理：

1. 验证配置
2. 解析临时 Secret
3. 判断本地或远程 Provider
4. 发起最小测试
5. 限制超时
6. 返回脱敏结果

推荐测试内容：

```text
返回一个包含 status 字段的简短 JSON。
```

或者复用 Provider 的真实 `health_check()`。

不得发送：

* Git Diff
* 用户代码
* Worklog
* 周报
* 本地路径
* 配置文件正文

响应：

```json
{
  "success": true,
  "provider": "openai-compatible",
  "model": "deepseek-chat",
  "latency_ms": 532,
  "message": "连接成功"
}
```

失败：

```json
{
  "success": false,
  "error_type": "authentication",
  "message": "AI Provider 鉴权失败"
}
```

不要返回云服务原始完整响应。

---

# 三十三、Thinking 模式配置

部分云端模型会返回：

```text
reasoning_content
```

并可能在生成最终 JSON 前达到长度上限。

AI 高级配置可以支持：

```yaml
ai:
  thinking:
    enabled: false
    provider_parameter: enable_thinking
```

但不同平台参数不同。

更安全的设计：

```yaml
ai:
  extra_body:
    enable_thinking: false
```

页面将其放入“高级配置”。

要求：

* `extra_body` 只允许 JSON 对象
* 禁止覆盖 `model`
* 禁止覆盖 `messages`
* 禁止覆盖认证 Header
* 禁止设置 URL
* 禁止设置任意 Header
* 保存前显示高级风险提示
* 默认关闭

首版也可以只支持一个通用开关，并由具体 Provider Adapter 解释。

---

# 三十四、飞书连接测试

实现：

```http
POST /api/config/test-feishu
```

分为两种模式：

## 基础校验

只检查：

* Webhook URL 格式
* Host
* HTTPS
* Secret 是否存在
* 签名能否生成

不发送消息。

## 真实测试

发送飞书测试消息。

必须满足：

* 用户明确点击“发送测试消息”
* 显示确认对话框
* 不自动执行
* 测试内容不包含项目数据
* 保存测试通知记录
* 不在日志输出 Webhook

测试消息：

```text
GitPulse Web 控制台连接测试
```

---

# 三十五、数据库和目录检查

系统配置页面提供：

```text
测试数据库
测试报告目录
```

数据库测试：

* 路径能否解析
* 父目录能否创建
* 文件是否可读写
* SQLite 能否连接
* Schema Version 是否兼容
* 不执行破坏性迁移

报告目录测试：

* 能否创建
* 能否写入临时文件
* 能否删除临时文件
* 是否在 `.git` 内
* 是否存在路径权限问题

不要在测试中删除用户已有文件。

---

# 三十六、页面交互要求

页面加载：

```text
加载当前配置
    ↓
展示各分组
    ↓
Secret 显示已配置状态
    ↓
记录当前 Revision
```

用户修改后：

* 页面显示“有未保存修改”
* 离开页面前提醒
* 保存按钮启用
* 可以恢复当前分组
* 可以恢复全部表单
* 不自动保存

点击保存：

```text
验证
    ↓
显示变更预览
    ↓
用户确认
    ↓
保存
```

保存成功：

```text
配置保存成功
已重新加载
```

保存失败：

```text
配置未保存
原文件未被修改
```

---

# 三十七、界面设计

页面采用简洁本地管理界面。

布局：

```text
顶部栏
├── GitPulse
├── 当前项目
├── 配置状态
└── 服务状态

左侧导航
├── 仪表盘
└── 系统配置

主区域
├── 配置分组
├── 表单字段
├── 字段来源
├── 验证提示
└── 保存工具栏
```

本阶段仪表盘只显示：

* GitPulse 版本
* 当前项目
* 配置状态
* 数据库状态
* AI 配置状态
* 飞书配置状态

不要在仪表盘实现 Git 操作。

---

# 三十八、表单可用性

要求：

* Label 与输入框关联
* 密码框支持临时显示
* 显示按钮默认隐藏
* 错误出现在对应字段旁
* 支持键盘操作
* 颜色不是唯一错误提示
* 数值字段带单位
* 高级设置默认折叠
* 危险设置用警告区域
* 保存按钮固定可见
* 移动宽度下基本可用

---

# 三十九、API 错误格式

统一返回：

```json
{
  "error": {
    "code": "config_validation_failed",
    "message": "配置校验失败",
    "details": [
      {
        "path": "ai.timeout_seconds",
        "message": "必须大于 0"
      }
    ]
  }
}
```

错误码至少包括：

```text
unauthorized
csrf_failed
config_not_found
config_validation_failed
config_changed
config_write_failed
secret_write_failed
ai_test_failed
feishu_test_failed
path_not_writable
internal_error
```

普通响应中不得返回 Python Traceback。

Debug 模式可以在服务端日志记录 Traceback，但仍须脱敏。

---

# 四十、日志要求

允许记录：

```text
Web 服务启动
访问页面
配置读取成功
配置验证成功或失败
配置保存范围
配置字段变更数量
备份文件创建
配置重新加载
连接测试结果
```

禁止记录：

```text
API Key
飞书 Webhook
飞书 Secret
Authorization Header
完整配置文件
完整 Secret 文件
Session Token
CSRF Token
Cookie
表单密码值
```

日志示例：

```text
web config updated scope=project changed_fields=4
```

```text
ai connection test success provider=openai-compatible latency_ms=532
```

禁止：

```text
api_key=sk-xxxx
```

---

# 四十一、Service 设计

实现：

```python
class ConfigWebService:
    def get_effective_config(
        self,
        project_root: Path,
    ) -> EffectiveConfigResponse:
        ...

    def validate_update(
        self,
        request: ConfigUpdateRequest,
    ) -> ConfigValidationResult:
        ...

    def preview_update(
        self,
        request: ConfigUpdateRequest,
    ) -> ConfigPreview:
        ...

    def save_update(
        self,
        request: ConfigUpdateRequest,
    ) -> EffectiveConfigResponse:
        ...
```

实现：

```python
class ConfigBackupService:
    def create_backup(
        self,
        path: Path,
    ) -> Path:
        ...

    def restore_backup(
        self,
        backup_path: Path,
        target_path: Path,
    ) -> None:
        ...

    def cleanup_old_backups(
        self,
        directory: Path,
        keep: int,
    ) -> None:
        ...
```

实现：

```python
class ConnectionTestService:
    def test_ai(
        self,
        config: AIConfig,
        secret: str | None,
    ) -> AIConnectionTestResult:
        ...

    def validate_feishu(
        self,
        config: FeishuConfig,
        webhook: str | None,
        secret: str | None,
    ) -> FeishuConnectionTestResult:
        ...
```

路由不得直接操作文件或调用 `httpx`。

---

# 四十二、配置合并规则

Web 保存某个 Scope 时，只修改该 Scope。

例如有效配置：

```text
默认 + 用户 + 项目
```

用户修改项目级 `ai.model` 时，只写：

```yaml
ai:
  model: new-model
```

不要把所有默认值展开写入项目配置。

否则项目配置会变得冗长，并遮盖用户配置。

需要实现：

```text
最小配置写入
```

即只写用户明确设置的值。

用户点击“恢复继承值”时，从当前 Scope 删除该字段。

---

# 四十三、字段继承控制

每个字段提供：

```text
使用继承值
在当前范围覆盖
```

示例：

```text
AI Timeout

当前生效值：60
来源：用户配置

项目级状态：
○ 使用用户配置
● 在项目中覆盖：120
```

删除覆盖后，重新显示上层来源。

---

# 四十四、配置 Schema 元数据

为了避免页面硬编码所有字段，可为配置模型增加 UI 元数据。

示例：

```python
timeout_seconds: float = Field(
    default=60,
    gt=0,
    json_schema_extra={
        "ui": {
            "group": "ai",
            "label": "请求超时",
            "unit": "秒",
            "advanced": False,
        }
    },
)
```

但不要为了动态表单过度复杂化。

MVP 可以手写表单 Schema，同时继续使用 Pydantic 验证。

---

# 四十五、测试要求

测试不得：

* 读取用户真实 `~/.config/gitpulse`
* 修改用户真实 `.gitpulse.yml`
* 使用真实 API Key
* 使用真实飞书 Webhook
* 调用真实 AI 服务
* 调用真实飞书服务
* 打开真实浏览器
* 监听外部网络接口

所有测试使用：

* `tmp_path`
* 临时项目目录
* 临时配置目录
* FastAPI TestClient
* Mock Provider
* Mock HTTP
* 固定 Session Token
* 固定 Clock

---

# 四十六、Web 安全测试

覆盖：

1. 未认证访问配置 API
2. 错误启动 Token
3. 正确 Token 建立 Session
4. Session Cookie 为 HttpOnly
5. SameSite 为 Strict
6. 缺少 CSRF
7. 错误 CSRF
8. 非法 Host
9. 非法 Origin
10. 跨域请求
11. Session 过期
12. 服务重启后 Session 失效
13. Token 不写入日志
14. Cookie 不写入日志

---

# 四十七、配置读取测试

覆盖：

* 只有默认配置
* 用户级配置
* 项目级配置
* 环境变量覆盖
* 字段来源
* 未知字段
* Secret 已配置状态
* Secret 未配置状态
* 不返回真实 Secret
* 配置文件不存在
* YAML 语法错误
* Pydantic 校验错误

---

# 四十八、配置保存测试

覆盖：

* 保存用户级配置
* 保存项目级配置
* 新建配置文件
* 更新已有配置
* 删除字段覆盖
* 保留未知字段
* 原子写入
* 自动备份
* 写入失败回滚
* 重新加载
* Revision 冲突
* 配置文件无权限
* 父目录不可写
* YAML 再解析失败
* 配置缓存清除

---

# 四十九、Secret 测试

覆盖：

* Keep
* Replace
* Delete
* 空 Replace
* Secret 文件创建
* 文件权限 600
* Secret 文件写入失败
* Config 成功但 Secret 失败时回滚
* 页面不返回 Secret
* Preview 不返回 Secret
* 日志不返回 Secret
* 项目配置被 Git 跟踪时阻止明文保存
* 用户级 Secret 保存成功

---

# 五十、连接测试

AI：

* 成功
* API Key 缺失
* 401
* 403
* 429
* 500
* 超时
* 非法 JSON
* Thinking 模型空 Content
* 本地模型无 Key
* 临时表单配置测试

飞书：

* Webhook 格式合法
* 非 HTTPS
* 非法 Host
* Secret 缺失
* 签名生成
* 基础校验不发送消息
* 真实测试需要确认
* Mock 成功
* Mock 失败

---

# 五十一、页面测试

至少验证：

1. `/settings` 可以打开。
2. 配置正确渲染。
3. Secret 只显示已配置状态。
4. 修改字段后出现未保存提示。
5. Validation Error 出现在对应字段。
6. Preview 显示变更。
7. Secret Preview 被遮盖。
8. 保存成功提示。
9. Revision 冲突提示。
10. AI 测试结果显示。
11. 飞书测试需要确认。
12. 页面刷新后配置保持。

---

# 五十二、性能要求

建议目标：

* 设置页面首次加载低于 1 秒
* 配置读取低于 300 毫秒
* 配置验证低于 300 毫秒
* 配置 Preview 低于 500 毫秒
* 配置保存低于 1 秒
* Secret 文件操作低于 500 毫秒
* 不在每次前端输入时写入磁盘
* AI 测试使用独立超时
* 飞书测试使用独立超时

---

# 五十三、质量要求

必须满足：

1. Web 和 CLI 使用同一 Config 模型。
2. Web 路由不直接读写 YAML。
3. Web 路由不直接调用 httpx。
4. Secret 不进入响应。
5. Secret 不进入日志。
6. 配置保存使用原子写入。
7. 配置保存前创建备份。
8. 支持 Revision 冲突。
9. 只监听 127.0.0.1。
10. 写操作需要 Session 和 CSRF。
11. 不启用宽松 CORS。
12. 不允许任意文件路径。
13. 不允许任意 Shell 命令。
14. 不在本阶段实现 Git 写操作。
15. 测试使用临时目录。
16. 外部请求全部 Mock。
17. 公共函数有类型注解。
18. 核心类有文档字符串。
19. 页面资源本地提供。
20. 不依赖公共 CDN。

---

# 五十四、验收标准

## Web 服务

* `gitpulse web` 可以启动。
* 默认监听 `127.0.0.1`。
* 可以自动打开浏览器。
* 可以通过 Token 建立本地 Session。
* 未授权用户不能访问配置 API。
* Ctrl+C 可以正常退出。

## 设置页面

* 能展示常规设置。
* 能展示 AI 设置。
* 能展示安全设置。
* 能展示 Git 设置。
* 能展示存储设置。
* 能展示周报设置。
* 能展示飞书设置。
* 能展示 Web 设置。
* 能显示字段来源。

## 配置管理

* 能读取有效配置。
* 能区分用户级和项目级配置。
* 能验证配置。
* 能预览配置变更。
* 能保存用户级配置。
* 能保存项目级配置。
* 能恢复字段继承。
* 能处理 Revision 冲突。
* 能原子写入。
* 能自动备份。
* 保存失败不破坏原配置。

## Secret

* API Key 可以通过页面配置。
* 飞书 Webhook 可以通过页面配置。
* 飞书 Secret 可以通过页面配置。
* 页面不返回已有 Secret。
* API 不返回已有 Secret。
* 日志不记录 Secret。
* Secret 文件权限为 600。
* 支持 Keep、Replace 和 Delete。
* 项目级明文 Secret 有安全阻断。

## 连接测试

* 能测试 AI 配置。
* AI 测试不发送代码。
* 能校验飞书配置。
* 真实飞书测试需要用户确认。
* 测试失败不修改正式配置。
* 测试结果经过脱敏。

## 测试

* 原有 CLI 测试继续通过。
* Web 单元测试通过。
* Web API 集成测试通过。
* 页面 E2E 测试通过。
* 外部调用全部 Mock。
* Ruff 通过。
* Mypy 达到项目当前标准。

---

# 五十五、实际开发顺序

严格按照以下顺序执行：

```text
1. 检查当前配置模型和配置加载逻辑
2. 运行现有完整测试
3. 确定用户级、项目级和 Secret 路径
4. 实现 Web App Factory
5. 实现 gitpulse web
6. 实现本地启动 Token
7. 实现 Session Cookie
8. 实现 CSRF
9. 实现 Host 和 Origin 校验
10. 编写 Web 安全测试
11. 定义 Web Config Schema
12. 实现 Effective Config 读取
13. 实现字段来源解析
14. 实现 Secret 状态解析
15. 编写配置读取测试
16. 实现配置验证
17. 实现字段级 Diff
18. 实现变更预览
19. 编写 Preview 测试
20. 实现配置备份
21. 实现原子写入
22. 实现 Revision 冲突
23. 实现配置重新加载
24. 编写配置保存测试
25. 实现用户级 Secret 文件
26. 实现 Keep、Replace 和 Delete
27. 编写 Secret 安全测试
28. 实现 AI 连接测试
29. 编写 AI Mock 测试
30. 实现飞书基础校验和测试
31. 编写飞书 Mock 测试
32. 实现数据库和目录检查
33. 创建基础页面模板
34. 创建系统设置页面
35. 实现表单校验提示
36. 实现变更 Preview 对话框
37. 实现保存成功和失败提示
38. 实现配置来源展示
39. 编写页面 E2E 测试
40. 执行所有测试
41. 执行 Ruff
42. 执行 Mypy
43. 检查日志脱敏
44. 更新 README
45. 新增 Web 系统配置文档
46. 输出阶段总结
```

不要先编写完整页面，再补后端安全和配置事务。

必须先完成安全、配置 Service 和 API，再开发页面。

---

# 五十六、文档要求

新增：

```text
docs/web-console.md
docs/web-settings.md
docs/web-security.md
```

`web-console.md` 至少包含：

1. 如何启动
2. 默认端口
3. 本地访问限制
4. 自动打开浏览器
5. 停止服务
6. 当前支持页面
7. 当前不支持功能

`web-settings.md` 至少包含：

1. 用户级配置
2. 项目级配置
3. 配置优先级
4. 字段来源
5. 配置预览
6. 配置备份
7. Revision 冲突
8. AI 测试
9. 飞书测试
10. Secret 保存模式

`web-security.md` 至少包含：

1. 只监听本机
2. 启动 Token
3. Session Cookie
4. CSRF
5. Host 校验
6. Origin 校验
7. Secret 脱敏
8. 日志脱敏
9. Secret 文件权限
10. 不支持外网部署
11. 已知安全限制

README 增加：

```bash
gitpulse web
```

以及：

```text
打开本地 Web 控制台后，可以配置 AI、存储、周报、安全和飞书参数。
```

---

# 五十七、本阶段完成后的汇报格式

完成后必须按照以下格式输出：

```text
## 本阶段完成内容

- 新增的 Web 模块
- 新增的 API
- 新增的页面
- 新增的配置 Service
- 新增的安全机制

## Web 服务

- 启动方式
- Host
- Port
- 自动打开浏览器
- Session 机制
- CSRF 机制

## 系统配置页面

- 支持的配置分组
- 用户级配置
- 项目级配置
- 字段来源
- 继承和覆盖

## 配置保存

- 配置校验
- Preview
- 原子写入
- 自动备份
- Revision 冲突
- 配置重新加载

## Secret 管理

- API Key
- 飞书 Webhook
- 飞书 Secret
- Secret 文件位置
- 文件权限
- Keep、Replace、Delete
- API 和日志脱敏

## 连接测试

- AI 测试
- 飞书基础校验
- 飞书真实测试
- 数据库检查
- 目录检查

## 测试结果

- Web 单元测试
- API 集成测试
- 页面 E2E 测试
- 原有回归测试
- Ruff
- Mypy

## 安全验证

- 是否只监听 127.0.0.1
- 是否启用 Session
- 是否启用 CSRF
- 是否拒绝非法 Host
- 是否确认 API 不返回 Secret
- 是否确认日志不记录 Secret
- 是否确认配置写入为原子操作
- 是否确认外部请求全部 Mock

## 已知限制

- 当前没有 Git 操作页面
- 当前没有 Worklog 页面
- 当前没有周报页面
- 当前没有多用户登录
- 当前不支持远程部署
- 当前不支持 HTTPS

## 下一阶段建议

下一阶段为：

本地 Web Git 工作台，包括 Git 状态、文件 Diff、文件选择、git add、取消暂存、安全检查和 AI Commit Message。
```

---

# 五十八、立即开始的任务

现在开始本地 Web 控制台第一阶段开发。

首先完成：

1. 检查现有配置模型。
2. 检查现有配置加载和缓存机制。
3. 运行完整测试。
4. 展示计划新增或修改的文件。
5. 创建 FastAPI App Factory。
6. 实现 `gitpulse web`。
7. 实现本地访问 Token、Session 和 CSRF。
8. 实现配置读取和字段来源 API。
9. 实现配置验证和 Preview。
10. 实现原子保存、备份和 Revision 冲突。
11. 实现本地 Secret 文件和脱敏。
12. 实现 AI 连接测试。
13. 实现飞书基础校验和测试。
14. 实现数据库和目录检查。
15. 实现系统设置页面。
16. 编写完整单元测试、集成测试和页面测试。
17. 执行全部测试、Ruff 和 Mypy。
18. 更新 README 和 Web 文档。

本阶段完成前，不要开始 `git add`、`git commit`、分支操作、Worklog 页面或周报页面开发。
