"""SMTP session handler that relays raw messages to Amazon SES."""

import logging

import boto3
from aiosmtpd.smtp import MISSING, Session, SMTP
from botocore.exceptions import ClientError

from smtp_to_ses.checks import EmailDomainChecker, SpamChecker
from smtp_to_ses.config import (
    ALLOWED_RECIPIENT_DOMAINS,
    ALLOWED_SENDER_DOMAINS,
    AWS_REGION,
    REQUIRE_MX_RECORD,
    SPAM_CHECK_ENABLED,
    SPAM_DNSBL_ENABLED,
    SPAM_DNSBL_ZONES,
    SPAM_SCORE_THRESHOLD,
    SPAMASSASSIN_HOST,
)

logger = logging.getLogger(__name__)


class SESForwarderHandler:
    """Accept inbound SMTP DATA payloads and send them via SES SendRawEmail."""

    def __init__(self) -> None:
        # boto3 uses the default credential chain: env vars, shared config,
        # or IAM role credentials when running on AWS.
        self.ses_client = boto3.client("ses", region_name=AWS_REGION)
        self.email_checker = EmailDomainChecker(
            allowed_sender_domains=ALLOWED_SENDER_DOMAINS,
            allowed_recipient_domains=ALLOWED_RECIPIENT_DOMAINS,
            require_mx_record=REQUIRE_MX_RECORD,
        )
        self.spam_checker = SpamChecker(
            enabled=SPAM_CHECK_ENABLED,
            dnsbl_enabled=SPAM_DNSBL_ENABLED,
            dnsbl_zones=SPAM_DNSBL_ZONES,
            spamassassin_host=SPAMASSASSIN_HOST,
            spam_score_threshold=SPAM_SCORE_THRESHOLD,
        )

    async def handle_HELO(
        self,
        server: SMTP,
        session: Session,
        envelope,
        hostname: str,
    ) -> str | object:
        """Reject DNS blocklisted clients before accepting HELO."""
        if error := self.spam_checker.check_connection(session.peer[0]):
            return f"550 {error}"
        return MISSING

    async def handle_EHLO(
        self,
        server: SMTP,
        session: Session,
        envelope,
        hostname: str,
        responses: list[str],
    ) -> list[str]:
        """Reject DNS blocklisted clients before accepting EHLO."""
        if error := self.spam_checker.check_connection(session.peer[0]):
            return [f"550 {error}"]
        # aiosmtpd's 5-arg EHLO hook does not set host_name; we must do it here.
        session.host_name = hostname
        return responses

    async def handle_MAIL(
        self,
        server: SMTP,
        session: Session,
        envelope,
        address: str,
        mail_options: list[str],
    ) -> str:
        """Validate the envelope sender before accepting MAIL FROM."""
        if error := self.email_checker.check_sender(address):
            return f"550 {error}"
        return "250 OK"

    async def handle_RCPT(
        self,
        server: SMTP,
        session: Session,
        envelope,
        address: str,
        rcpt_options: list[str],
    ) -> str:
        """Validate each recipient before accepting RCPT TO."""
        if error := self.email_checker.check_recipient(address):
            return f"550 {error}"
        return "250 OK"

    async def handle_DATA(self, server: SMTP, session: Session, envelope) -> str:
        """Screen for spam, then forward the raw RFC 822 message to SES."""
        peer = session.peer
        mail_from = envelope.mail_from
        rcpt_tos = envelope.rcpt_tos
        raw_data = envelope.content

        logger.info("Receiving message from %s", peer)
        logger.info("Forwarding mail from %s to %s", mail_from, rcpt_tos)

        if error := self.spam_checker.check_message(raw_data):
            return f"550 {error}"

        try:
            response = self.ses_client.send_raw_email(
                Source=mail_from,
                Destinations=rcpt_tos,
                RawMessage={"Data": raw_data},
            )
            message_id = response["MessageId"]
            logger.info("Successfully sent via SES. Message ID: %s", message_id)
        except ClientError as exc:
            error_message = exc.response["Error"]["Message"]
            logger.error("SES rejected message: %s", error_message)
            return "550 Error: Message rejected by AWS SES"

        return "250 OK"
