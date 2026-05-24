# smtp-to-ses

Lightweight SMTP server that receives mail from local applications and forwards it to [Amazon SES](https://aws.amazon.com/ses/). Built for running on a Linux server as a systemd service.

## Features

- Accepts standard SMTP on a configurable host and port
- Forwards the raw RFC 822 message to SES without rewriting headers
- **Domain and email validation** — syntax checks, optional domain allowlists, optional MX verification
- **Spam screening** — DNS blocklist (DNSBL) checks on client IP, optional SpamAssassin scoring
- Configuration via `.env` or environment variables
- Works with boto3's default AWS credential chain (env vars, shared config, IAM roles)

## Requirements

- Linux server (systemd)
- Python 3.10+
- [uv](https://docs.astral.sh/uv/) for installation
- AWS account with SES configured in your target region
- Verified SES identities for senders you relay

## Server deployment

### 1. Create a system user

```bash
sudo useradd --system --home /opt/smtp-to-ses --shell /usr/sbin/nologin smtp-to-ses
```

### 2. Install the application

```bash
sudo mkdir -p /opt/smtp-to-ses
sudo chown smtp-to-ses:smtp-to-ses /opt/smtp-to-ses

sudo -u smtp-to-ses git clone https://github.com/your-org/smtp-to-ses.git /opt/smtp-to-ses
cd /opt/smtp-to-ses
sudo -u smtp-to-ses uv sync
```

### 3. Configure environment

```bash
sudo mkdir -p /etc/smtp-to-ses
sudo cp /opt/smtp-to-ses/.env.example /etc/smtp-to-ses/.env
sudo chmod 600 /etc/smtp-to-ses/.env
sudo nano /etc/smtp-to-ses/.env
```

Minimum configuration:

```env
AWS_REGION=us-east-1
LISTEN_HOST=127.0.0.1
LISTEN_PORT=1025
ALLOWED_SENDER_DOMAINS=yourdomain.com
```

Set `ALLOWED_SENDER_DOMAINS` to the SES-verified domains you trust local apps to send as. Use `127.0.0.1` for `LISTEN_HOST` when only local services should connect.

AWS credentials can be supplied in `/etc/smtp-to-ses/.env`, via `~/.aws/credentials` on the service user, or through an IAM instance role.

### 4. Install and start systemd service

```bash
sudo cp /opt/smtp-to-ses/deploy/smtp-to-ses.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now smtp-to-ses
sudo systemctl status smtp-to-ses
```

View logs:

```bash
journalctl -u smtp-to-ses -f
```

### 5. Point applications at the bridge

Configure your app's SMTP settings:

| Setting | Value |
|---------|-------|
| Host | `127.0.0.1` (or your `LISTEN_HOST`) |
| Port | `1025` (or your `LISTEN_PORT`) |
| TLS | Usually not needed for localhost |
| Auth | None by default |

## Security recommendations

- Bind to `127.0.0.1` unless remote clients on a trusted network must connect
- Set `ALLOWED_SENDER_DOMAINS` to match your SES verified identities
- Optionally set `ALLOWED_RECIPIENT_DOMAINS` to restrict outbound recipient domains
- Keep `SPAM_CHECK_ENABLED=true` and review `SPAM_DNSBL_ZONES` for your policy
- Run the service as a dedicated unprivileged user (the unit file does this)
- Protect `/etc/smtp-to-ses/.env` with mode `600`

## Configuration reference

| Variable | Default | Description |
|----------|---------|-------------|
| `AWS_REGION` | `us-east-1` | AWS region where SES is enabled |
| `AWS_ACCESS_KEY_ID` | — | Optional explicit AWS access key |
| `AWS_SECRET_ACCESS_KEY` | — | Optional explicit AWS secret key |
| `AWS_SESSION_TOKEN` | — | Optional session token for temporary credentials |
| `LISTEN_HOST` | `0.0.0.0` | SMTP bind address (`127.0.0.1` recommended on servers) |
| `LISTEN_PORT` | `1025` | SMTP listen port |
| `ENV_FILE` | — | Path to env file (set to `/etc/smtp-to-ses/.env` in systemd) |
| `LOG_LEVEL` | `INFO` | Logging verbosity |
| `ALLOWED_SENDER_DOMAINS` | — | Comma-separated allowed sender domains (empty = allow all) |
| `ALLOWED_RECIPIENT_DOMAINS` | — | Comma-separated allowed recipient domains (empty = allow all) |
| `REQUIRE_MX_RECORD` | `false` | Verify domains have MX or A/AAAA records |
| `SPAM_CHECK_ENABLED` | `true` | Enable spam checks |
| `SPAM_DNSBL_ENABLED` | `true` | Block DNS blocklisted client IPs |
| `SPAM_DNSBL_ZONES` | see `.env.example` | Comma-separated DNSBL zones |
| `SPAMASSASSIN_HOST` | — | Optional SpamAssassin spamd host (`127.0.0.1:783`) |
| `SPAM_SCORE_THRESHOLD` | `5.0` | Reject at or above this SpamAssassin score |

## Optional: SpamAssassin

For content-based spam scoring, install SpamAssassin and point the bridge at a local `spamd`:

```bash
# Debian/Ubuntu example
sudo apt install spamassassin

# In /etc/smtp-to-ses/.env
SPAMASSASSIN_HOST=127.0.0.1:783
SPAM_SCORE_THRESHOLD=5.0
```

If `spamd` is unavailable, the bridge logs an error and continues without content scoring (DNSBL checks still apply when enabled).

## AWS SES notes

- Verify sender domains or addresses in SES before sending.
- If your account is in the SES sandbox, recipient addresses must also be verified.
- Ensure the IAM principal has `ses:SendRawEmail` for your identities.

## Upgrading

```bash
cd /opt/smtp-to-ses
sudo -u smtp-to-ses git pull
sudo -u smtp-to-ses uv sync
sudo systemctl restart smtp-to-ses
```

## Development

See [DEVELOPMENT.md](DEVELOPMENT.md) for local development and PyPI publishing.

## License

MIT — see [LICENSE](LICENSE).
