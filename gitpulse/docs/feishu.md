# Feishu

Use Feishu custom bot webhooks through environment variables:

```bash
export GITPULSE_FEISHU_WEBHOOK="https://open.feishu.cn/open-apis/bot/v2/hook/..."
export GITPULSE_FEISHU_SECRET="..."
```

Preview before sending:

```bash
gitpulse notify weekly <report-id> --preview
```

Send after confirmation:

```bash
gitpulse notify weekly <report-id> --yes
```

Only confirmed weekly reports with full source coverage can be sent.
