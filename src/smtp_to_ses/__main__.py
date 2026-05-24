"""CLI entry point: ``python -m smtp_to_ses`` or ``smtp-to-ses`` after install."""

import os

from smtp_to_ses.server import configure_logging, run_server


def main() -> None:
    """Run the SMTP-to-SES bridge."""
    configure_logging(os.getenv("LOG_LEVEL", "INFO"))
    run_server()


if __name__ == "__main__":
    main()
