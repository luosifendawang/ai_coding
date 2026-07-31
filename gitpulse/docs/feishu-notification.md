# Feishu Notification

GitPulse sends confirmed weekly reports as a Feishu self-built application bot.

## Configuration

Store non-secret values in `.gitpulse.yml`:

```yaml
feishu:
  enabled: true
  app_id: cli_yourappid1234
  receive_id_type: chat_id
  receive_id: oc_your_chat_id
  message_type: interactive
  require_confirmation: true
  allow_duplicate_send: false
  include_sources: false
  max_json_bytes: 28000
```

Store the application credential in `~/.config/gitpulse/secrets.yml`:

```yaml
feishu:
  app_secret: "your-app-secret"
```

Direct `app_secret` values in `.gitpulse.yml` are rejected. Environment overrides
are available through `app_id_env`, `app_secret_env`, and `receive_id_env`.

The Feishu application must:

- enable bot capability
- have permission to send messages as the application bot
- be published and available to the current tenant
- be added to the target group when `receive_id_type` is `chat_id`

## Send A Weekly Report

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

Before sending, GitPulse validates report status and source coverage, scans the
rendered payload, enforces size and duplicate limits, and records the result for
audit. App Secret, access tokens, and full payloads are not stored in the
database.

## Protocol

GitPulse exchanges the App ID and App Secret for a tenant access token, then
sends `text` or `interactive` messages through the Feishu message API. The
message target is selected with `receive_id_type` and `receive_id`.

Report lifecycle status remains independent from notification delivery. A
successful send creates a `NotificationRecord(status="sent")`.
