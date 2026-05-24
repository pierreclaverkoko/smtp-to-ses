"""Validate envelope addresses and restrict allowed sender/recipient domains."""

import logging
from email_validator import EmailNotValidError, validate_email

import dns.resolver

logger = logging.getLogger(__name__)


class EmailDomainChecker:
    """Validate email syntax and enforce optional domain allowlists."""

    def __init__(
        self,
        *,
        allowed_sender_domains: frozenset[str],
        allowed_recipient_domains: frozenset[str],
        require_mx_record: bool,
    ) -> None:
        self.allowed_sender_domains = allowed_sender_domains
        self.allowed_recipient_domains = allowed_recipient_domains
        self.require_mx_record = require_mx_record

    def check_sender(self, address: str | None) -> str | None:
        """Return an SMTP error message if the sender is not allowed."""
        if not address:
            return "Sender address required"

        # Null reverse-path used for bounce messages.
        if address in {"<>", ""}:
            return None

        error = self._validate_address(address, "sender")
        if error:
            return error

        domain = self._domain_from_address(address)
        if self.allowed_sender_domains and domain not in self.allowed_sender_domains:
            logger.warning("Rejected sender domain not in allowlist: %s", domain)
            return f"Sender domain not allowed: {domain}"

        if self.require_mx_record:
            mx_error = self._check_mx_record(domain)
            if mx_error:
                return mx_error

        return None

    def check_recipient(self, address: str) -> str | None:
        """Return an SMTP error message if the recipient is not allowed."""
        error = self._validate_address(address, "recipient")
        if error:
            return error

        domain = self._domain_from_address(address)
        if self.allowed_recipient_domains and domain not in self.allowed_recipient_domains:
            logger.warning("Rejected recipient domain not in allowlist: %s", domain)
            return f"Recipient domain not allowed: {domain}"

        if self.require_mx_record:
            mx_error = self._check_mx_record(domain)
            if mx_error:
                return mx_error

        return None

    def _validate_address(self, address: str, role: str) -> str | None:
        try:
            validate_email(address, check_deliverability=False)
        except EmailNotValidError as exc:
            logger.warning("Rejected invalid %s address %r: %s", role, address, exc)
            return f"Invalid {role} address: {address}"
        return None

    @staticmethod
    def _domain_from_address(address: str) -> str:
        return address.rsplit("@", 1)[1].lower()

    def _check_mx_record(self, domain: str) -> str | None:
        """Ensure the domain can receive mail (MX record, or A/AAAA fallback)."""
        try:
            dns.resolver.resolve(domain, "MX")
            return None
        except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN, dns.resolver.NoNameservers):
            pass
        except dns.exception.Timeout:
            logger.warning("MX lookup timed out for domain %s", domain)
            return f"Could not verify mail domain: {domain}"

        # RFC 5321: if no MX exists, an A/AAAA record may be used.
        try:
            dns.resolver.resolve(domain, "A")
            return None
        except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN, dns.resolver.NoNameservers):
            pass
        except dns.exception.Timeout:
            logger.warning("A record lookup timed out for domain %s", domain)
            return f"Could not verify mail domain: {domain}"

        try:
            dns.resolver.resolve(domain, "AAAA")
            return None
        except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN, dns.resolver.NoNameservers):
            logger.warning("No MX or A/AAAA records for domain %s", domain)
            return f"Domain cannot receive mail: {domain}"
        except dns.exception.Timeout:
            logger.warning("AAAA record lookup timed out for domain %s", domain)
            return f"Could not verify mail domain: {domain}"

        return None
