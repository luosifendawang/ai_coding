# Feishu Notification

GitPulse supports Feishu custom bot webhook delivery for confirmed weekly reports.

## Configuration

Real credentials must come from environment variables:

```bash
export GITPULSE_FEISHU_WEBHOOK="https://open.feishu.cn/open-apis/bot/v2/hook/..."
export GITPULSE_FEISHU_SECRET="..."
```

The config only stores environment variable names and behavior flags:

```yaml
feishu:
  enabled: false
  webhook_env: GITPULSE_FEISHU_WEBHOOK
  secret_env: GITPULSE_FEISHU_SECRET
  message_type: interactive
  signature_required: true
  require_confirmation: true
  allow_duplicate_send: false
  include_sources: false
  max_json_bytes: 28000
```

Plain `webhook` or `secret` config keys are rejected.

## Send A Weekly Report

Only confirmed weekly reports with full source coverage can be sent.

```bash
gitpulse notify weekly weekly_xxx --preview
gitpulse notify weekly weekly_xxx --yes
gitpulse notify weekly weekly_xxx --yes --force
```

Generate, confirm, save, and send in one command:

```bash
gitpulse weekly --current --confirm --send-feishu --no-ai
```

`--send-feishu` requires `--confirm`; draft reports are blocked.

## Safety

Before sending, GitPulse:

- validates report status and confidence
- verifies source coverage is 100%
- renders text or interactive card payload
- checks JSON byte size
- scans the final payload for high or critical sensitive data
- checks recent duplicate sends by content hash
- records notification status for audit

Webhook URL, Secret, signatures, and full payloads are not stored in the database.

## Feishu Protocol

GitPulse sends custom bot webhook `POST` requests with:

- `msg_type: text` and `content.text`
- `msg_type: interactive` and `card`
- optional `timestamp` and `sign` when Secret is configured

The signature follows Feishu custom bot signing rules: `timestamp + "\n" + secret` is used as the HMAC-SHA256 key for an empty message, then Base64 encoded.

## Status

Weekly report content status remains independent from notification delivery. A successful send creates a `NotificationRecord(status="sent")`; it does not rewrite a confirmed report as a different lifecycle state.
