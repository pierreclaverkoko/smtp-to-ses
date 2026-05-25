"""Optional SMTP AUTH (PLAIN/LOGIN) for clients connecting to the bridge."""

import hmac
import logging

logger = logging.getLogger(__name__)


def make_auth_callback(username: str, password: str):
    """Return an auth_callback validating a single username/password pair."""
    expected_user = username.encode("utf-8")
    expected_password = password.encode("utf-8")

    def auth_callback(mechanism: str, login: bytes, password: bytes) -> bool:
        ok = hmac.compare_digest(login, expected_user) and hmac.compare_digest(
            password, expected_password
        )
        if not ok:
            logger.warning(
                "SMTP authentication failed for user %r via %s",
                login.decode("utf-8", errors="replace"),
                mechanism,
            )
        return ok

    return auth_callback
