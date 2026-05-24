"""SMTP server lifecycle helpers."""

import logging
import signal
import sys
from types import FrameType

from aiosmtpd.controller import Controller

from smtp_to_ses.config import LISTEN_HOST, LISTEN_PORT
from smtp_to_ses.handler import SESForwarderHandler

logger = logging.getLogger(__name__)


def configure_logging(level: str = "INFO") -> None:
    """Configure root logging for CLI and service use."""
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )


def run_server() -> None:
    """Start the SMTP listener and block until interrupted."""
    handler = SESForwarderHandler()
    controller = Controller(handler, hostname=LISTEN_HOST, port=LISTEN_PORT)

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
