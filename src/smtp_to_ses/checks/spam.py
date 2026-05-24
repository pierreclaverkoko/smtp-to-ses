"""Spam screening via DNS blocklists and optional SpamAssassin."""

import logging
import socket
from ipaddress import ip_address

import dns.resolver

logger = logging.getLogger(__name__)


class SpamChecker:
    """Reject mail from listed IPs or messages that exceed a spam score."""

    def __init__(
        self,
        *,
        enabled: bool,
        dnsbl_enabled: bool,
        dnsbl_zones: tuple[str, ...],
        spamassassin_host: str | None,
        spam_score_threshold: float,
    ) -> None:
        self.enabled = enabled
        self.dnsbl_enabled = dnsbl_enabled
        self.dnsbl_zones = dnsbl_zones
        self.spamassassin_host = spamassassin_host
        self.spam_score_threshold = spam_score_threshold

    def check_connection(self, peer_ip: str) -> str | None:
        """Return an SMTP error if the client IP appears on a DNS blocklist."""
        if not self.enabled or not self.dnsbl_enabled or not self.dnsbl_zones:
            return None

        try:
            ip = ip_address(peer_ip)
        except ValueError:
            logger.warning("Could not parse client IP for DNSBL lookup: %s", peer_ip)
            return None

        if ip.is_private or ip.is_loopback:
            return None

        reversed_ip = _reverse_ip_for_dnsbl(ip)
        if reversed_ip is None:
            return None

        for zone in self.dnsbl_zones:
            query = f"{reversed_ip}.{zone}"
            try:
                answers = dns.resolver.resolve(query, "A")
            except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer, dns.resolver.NoNameservers):
                continue
            except dns.exception.Timeout:
                logger.warning("DNSBL lookup timed out for %s", query)
                continue

            if answers:
                logger.warning("Client IP %s listed on DNSBL zone %s", peer_ip, zone)
                return f"Client IP blocked by DNSBL ({zone})"

        return None

    def check_message(self, raw_message: bytes) -> str | None:
        """Return an SMTP error if SpamAssassin scores the message as spam."""
        if not self.enabled or not self.spamassassin_host:
            return None

        host, _, port = self.spamassassin_host.partition(":")
        port_num = int(port or "783")

        request_header = (
            f"CONTENT scan\r\n"
            f"Content-length: {len(raw_message)}\r\n"
            f"\r\n"
        ).encode("ascii")
        payload = request_header + raw_message

        try:
            with socket.create_connection((host, port_num), timeout=10) as sock:
                sock.sendall(payload)
                response = sock.recv(4096)
        except OSError as exc:
            logger.error("SpamAssassin unavailable at %s: %s", self.spamassassin_host, exc)
            return None

        score = self._parse_spam_score(response)
        if score is None:
            logger.warning("Could not parse SpamAssassin response")
            return None

        if score >= self.spam_score_threshold:
            logger.warning(
                "Rejected message with spam score %.1f (threshold %.1f)",
                score,
                self.spam_score_threshold,
            )
            return f"Message rejected as spam (score {score:.1f})"

        logger.debug("SpamAssassin score %.1f below threshold %.1f", score, self.spam_score_threshold)
        return None

    @staticmethod
    def _parse_spam_score(response: bytes) -> float | None:
        """Extract the spam score from a SpamAssassin spamd/spamc response."""
        text = response.decode("utf-8", errors="replace")
        for line in text.splitlines():
            if line.startswith("Spam:"):
                # Example: Spam: True ; 12.3 / 5.0
                parts = line.split(";")
                if len(parts) >= 2:
                    score_part = parts[1].strip().split("/")[0].strip()
                    try:
                        return float(score_part)
                    except ValueError:
                        return None
        return None


def _reverse_ip_for_dnsbl(ip: ip_address) -> str | None:
    """Build a DNSBL query prefix for IPv4 or IPv6 addresses."""
    if ip.version == 4:
        return ".".join(reversed(str(ip).split(".")))

    if ip.version == 6:
        hex_nibbles = ip.exploded.replace(":", "")
        return ".".join(reversed(list(hex_nibbles)))

    return None
