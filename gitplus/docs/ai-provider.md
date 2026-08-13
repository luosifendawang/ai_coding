# AI Provider

gitplus 通过统一 `LLMProvider` 接口调用模型。业务层只依赖 `generate()`，不会直接调用 HTTP。

## Provider

- `openai-compatible`：调用 OpenAI 兼容 `/chat/completions` 接口。
- `mock`：用于测试和离线演示，不调用网络。

## 配置

```yaml
ai:
  provider: openai-compatible
  model: local-model
  base_url: http://localhost:11434/v1
  api_key: your-api-key
  api_key_env: GITPLUS_API_KEY
  temperature: 0.2
  top_p: 0.8
  timeout_seconds: 60
  max_retries: 2
  response_format: json
```

API Key 可以直接写在项目 `.gitplus.yml` 的 `ai.api_key` 中，也可以通过环境变量读取。

```bash
export GITPLUS_API_KEY=...
```

## 本地模型

本地 OpenAI 兼容服务可以使用 `localhost`、`127.0.0.1` 或显式配置 `is_local=true`。即使是本地模型，gitplus 仍会先执行安全扫描，并优先使用脱敏 Diff。

## 超时和重试

Provider 支持请求超时和有限重试。429、网络错误和 5xx 可重试，401/403/400 不重试。

## 安全阻断

当安全扫描发现 high 或 critical 风险时，远程 Provider 不会被调用。critical 风险默认阻止所有 Provider。

## 日志隐私

日志不得记录完整 Prompt、完整 Diff、完整 AI 响应、API Key 或 Authorization Header。
