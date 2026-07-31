# Web 控制台安全

## 本地边界

- Uvicorn 固定监听 `127.0.0.1`，不提供外部 Host 参数。
- 仅接受 `127.0.0.1`、`localhost` 和 `[::1]` Host Header。
- 不启用 CORS，也不支持远程部署或多用户访问。

## 认证与请求保护

每次启动生成随机一次性 Token。`/auth/local` 验证后设置内存 Session Cookie：

- `HttpOnly=true`
- `SameSite=Strict`
- `Secure=false`，因为当前仅支持本地 HTTP

所有配置 API 要求有效 Session。写操作额外要求 CSRF Header，并校验 Origin 或 Referer 的主机与端口。服务重启会清除全部 Session。

## 配置与 Secret

- API Key 和飞书 App Secret 不进入普通配置响应。
- Preview 只显示“已配置、已替换、已删除”。
- Secret 文件和备份权限固定为 `0600`。
- 配置使用备份、临时文件、`fsync`、原子替换和失败回滚。
- Revision 防止覆盖外部并发修改。
- 日志不得记录 Token、Cookie、CSRF、Authorization Header 或完整配置正文。

当前使用本地 HTTP，不提供 HTTPS；浏览器中的本机恶意扩展仍可能观察页面操作。不要将服务代理到外网。
