# Security

gitplus 的安全模块在本地分析 Git Diff，不修改源文件，不调用远程服务，也不自动删除敏感内容。

## 扫描范围

- 暂存区 Diff：`gitplus check --staged`
- 未暂存 Diff：`gitplus check --unstaged`
- 文本 Patch 的可见部分
- 已截断 Diff 只扫描保留下来的内容，并产生警告
- 二进制文件不扫描原始内容

## 默认规则

凭证类：

- OpenAI 风格 API Key
- GitHub Token
- GitLab Token
- AWS Access Key
- Bearer Token
- JWT
- 硬编码 password/passwd/pwd
- 硬编码 secret/token/api_key/access_key/client_secret
- PEM 私钥
- 数据库连接字符串
- 云服务连接字符串

隐私类：

- 私有 IPv4
- 内网域名
- 本地用户目录
- 邮箱地址
- 中国大陆手机号
- 中国大陆身份证号

## 风险等级

- `critical`：始终阻止远程模型调用，例如 PEM 私钥。
- `high`：默认阻止远程模型调用，例如 API Key、Token、硬编码密码。
- `medium`：默认脱敏后允许，例如私有 IP、手机号。
- `low`：默认提示或脱敏，例如本地用户路径、邮箱。

## 脱敏占位符

相同值在一次扫描中使用稳定占位符：

- `<API_KEY_1>`
- `<ACCESS_TOKEN_1>`
- `<PRIVATE_KEY>`
- `<DATABASE_URL_1>`
- `<PRIVATE_IP_1>`
- `<INTERNAL_DOMAIN_1>`
- `<EMAIL_1>`
- `<PHONE_1>`
- `<ID_CARD_1>`
- `<USER_HOME_1>`

公开结果只包含占位符和风险定位，不包含原始敏感值。

## 自定义规则

全局 `~/.gitplus/.config/config.yml` 可配置：

```yaml
security:
  custom_patterns:
    - id: custom_demo_token
      name: Custom Demo Token
      pattern: "demo_[A-Za-z0-9]{8,}"
      level: medium
      description: "检测到自定义测试 Token"
      replacement: "<ACCESS_TOKEN>"
```

规则 ID 必须唯一，只能使用小写英文、数字和下划线。正则不能为空，也不能匹配空字符串。

## 禁用规则

```yaml
security:
  ignored_rules:
    - email
```

## 误报处理

规则扫描追求高召回，可能存在误报或漏报。对于误报，可通过 `ignored_rules` 临时禁用，或添加更精确的自定义规则配合后续流程使用。

## 扫描失败

扫描失败时，gitplus 默认阻止远程模型调用：

```yaml
security:
  block_remote_on_scan_failure: true
```

## Git 历史泄露

如果 Diff 中出现删除凭证的内容，说明该凭证可能已经进入 Git 历史。请确认是否需要轮换凭证，并检查历史提交。

## 环境变量原则

API Key 不应写入项目配置或代码，应保存在权限为 `0600` 的用户 Secret 文件中，或通过环境变量提供。
