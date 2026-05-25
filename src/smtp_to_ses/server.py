"""SMTP server lifecycle helpers."""

import logging
import signal
import sys
from types import FrameType

from aiosmtpd.controller import Controller

from smtp_to_ses.auth import make_auth_callback
from smtp_to_ses.config import (
    LISTEN_HOST,
    LISTEN_PORT,
    SMTP_AUTH_PASSWORD,
    SMTP_AUTH_USERNAME,
    smtp_auth_enabled,
)
from smtp_to_ses.handler import SESForwarderHandler

logger = logging.getLogger(__name__)


def configure_logging(level: str = "INFO") -> None:
    """Configure root logging for CLI and service use."""
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )


def _smtp_controller_kwargs() -> dict:
    """Build optional aiosmtpd kwargs when SMTP AUTH is configured."""
    if smtp_auth_enabled():
        assert SMTP_AUTH_USERNAME is not None
        assert SMTP_AUTH_PASSWORD is not None
        logger.info("SMTP AUTH enabled for user %r", SMTP_AUTH_USERNAME)
        return {
            "auth_required": True,
            # Allow AUTH on plain connections (typical for Docker/host relay).
            "auth_require_tls": False,
            "auth_callback": make_auth_callback(SMTP_AUTH_USERNAME, SMTP_AUTH_PASSWORD),
        }

    if SMTP_AUTH_USERNAME or SMTP_AUTH_PASSWORD:
        logger.warning(
            "SMTP AUTH disabled: set both SMTP_AUTH_USERNAME and SMTP_AUTH_PASSWORD"
        )

    return {}


def run_server() -> None:
    """Start the SMTP listener and block until interrupted."""
    handler = SESForwarderHandler()
    controller = Controller(
        handler,
        hostname=LISTEN_HOST,
        port=LISTEN_PORT,
        **_smtp_controller_kwargs(),
    )

    def shutdown(signum: int, _frame: FrameType | None) -> None:
        logger.info("Received signal %s, stopping SMTP server", signum)
        controller.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    controller.start()
    logger.info("SMTP to SES bridge listening on %s:%s", LISTEN_HOST, LISTEN_PORT)

    try:
        signal.pause()
    except AttributeError:
        # signal.pause() is unavailable on Windows; fall back to a blocking read.
        input("Press Enter to stop the server...\n")
    finally:
        controller.stop()
