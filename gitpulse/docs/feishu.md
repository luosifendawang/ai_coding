# Feishu

GitPulse uses a Feishu self-built application bot. Enable the bot capability in
the Feishu developer console, grant the application permission to send messages,
and add the bot to the target group.

Configure the non-secret application and target identifiers in `.gitpulse.yml`:

```yaml
feishu:
  enabled: true
  app_id: cli_yourappid1234
  receive_id_type: chat_id
  receive_id: oc_your_chat_id
```

Store the App Secret in `~/.config/gitpulse/secrets.yml`:

```yaml
feishu:
  app_secret: "your-app-secret"
```

The secret file must have `0600` permissions. `GITPULSE_FEISHU_APP_ID`,
`GITPULSE_FEISHU_APP_SECRET`, and `GITPULSE_FEISHU_RECEIVE_ID` are supported as
optional environment overrides.

Preview before sending:

```bash
gitpulse notify weekly <report-id> --preview
```

Send after confirmation:

```bash
gitpulse notify weekly <report-id> --yes
```

Only confirmed weekly reports with full source coverage can be sent.
