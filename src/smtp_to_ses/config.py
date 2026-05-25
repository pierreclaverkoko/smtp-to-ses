"""Environment-based configuration loaded from a .env file or process env."""

import os
from pathlib import Path

from dotenv import load_dotenv


def _load_env_files() -> None:
    """Load .env from ENV_FILE or the current working directory."""
    env_file = os.getenv("ENV_FILE")
    if env_file:
        load_dotenv(Path(env_file).expanduser(), override=False)
    else:
        # Existing process environment variables take precedence over .env values.
        load_dotenv()


def _int_env(name: str, default: int) -> int:
    """Parse an integer environment variable with a safe default."""
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer, got {raw!r}") from exc


def _float_env(name: str, default: float) -> float:
    """Parse a float environment variable with a safe default."""
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return float(raw)
    except ValueError as exc:
        raise ValueError(f"{name} must be a number, got {raw!r}") from exc


def _bool_env(name: str, default: bool) -> bool:
    """Parse a boolean environment variable."""
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _csv_domains(name: str) -> frozenset[str]:
    """Parse a comma-separated list of domain names (lowercased)."""
    raw = os.getenv(name, "")
    if not raw.strip():
        return frozenset()
    return frozenset(part.strip().lower() for part in raw.split(",") if part.strip())


def _csv_list(name: str, default: str = "") -> tuple[str, ...]:
    """Parse a comma-separated list of non-empty strings."""
    raw = os.getenv(name, default)
    if not raw.strip():
        return ()
    return tuple(part.strip() for part in raw.split(",") if part.strip())


_load_env_files()

# AWS region where SES is configured (e.g. us-east-1, eu-west-1).
AWS_REGION: str = os.getenv("AWS_REGION", "us-east-1")

# Network interface and port for the local SMTP listener.
LISTEN_HOST: str = os.getenv("LISTEN_HOST", "0.0.0.0")
LISTEN_PORT: int = _int_env("LISTEN_PORT", 1025)

# --- Email / domain validation ---

# Comma-separated sender domains allowed in MAIL FROM (empty = allow all).
ALLOWED_SENDER_DOMAINS: frozenset[str] = _csv_domains("ALLOWED_SENDER_DOMAINS")

# Comma-separated recipient domains allowed in RCPT TO (empty = allow all).
ALLOWED_RECIPIENT_DOMAINS: frozenset[str] = _csv_domains("ALLOWED_RECIPIENT_DOMAINS")

# When true, verify each address domain has MX (or A/AAAA) DNS records.
REQUIRE_MX_RECORD: bool = _bool_env("REQUIRE_MX_RECORD", False)

# --- Spam checking ---

# Master switch for all spam checks.
SPAM_CHECK_ENABLED: bool = _bool_env("SPAM_CHECK_ENABLED", True)

# Query DNS blocklists for the connecting client IP.
SPAM_DNSBL_ENABLED: bool = _bool_env("SPAM_DNSBL_ENABLED", True)

# Comma-separated DNSBL zones (reverse-IP lookup).
SPAM_DNSBL_ZONES: tuple[str, ...] = _csv_list(
    "SPAM_DNSBL_ZONES",
    "zen.spamhaus.org,b.barracudacentral.org,bl.spamcop.net",
)

# Optional SpamAssassin spamd host (e.g. 127.0.0.1:783). Empty = disabled.
SPAMASSASSIN_HOST: str | None = os.getenv("SPAMASSASSIN_HOST") or None

# Reject messages at or above this SpamAssassin score.
SPAM_SCORE_THRESHOLD: float = _float_env("SPAM_SCORE_THRESHOLD", 5.0)

# --- SMTP authentication (optional) ---

# When both are set, clients must AUTH (PLAIN/LOGIN) before MAIL/RCPT/DATA.
SMTP_AUTH_USERNAME: str | None = os.getenv("SMTP_AUTH_USERNAME") or None
SMTP_AUTH_PASSWORD: str | None = os.getenv("SMTP_AUTH_PASSWORD") or None


def smtp_auth_enabled() -> bool:
    """Return True when SMTP AUTH is configured."""
    return bool(SMTP_AUTH_USERNAME and SMTP_AUTH_PASSWORD)
