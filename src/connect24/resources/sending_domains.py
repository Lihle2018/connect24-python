"""Proving you control a domain, so mail goes out as you."""

from __future__ import annotations

from typing import Any, Iterable

from .._transport import Transport
from ..models import SendingDomain


class SendingDomains:
    """``client.sending_domains``.

    Until a domain is verified, email leaves from your account's assigned address on
    ``connect24.co.za`` and your address becomes the Reply-To. That address is random and not
    chooseable: if customers could pick it, one could send as ``security@connect24.co.za`` and phish
    under the platform's brand. Sending reputation is shared, so the identity stays ours until you
    have proved a domain of your own.
    """

    def __init__(self, transport: Transport) -> None:
        self._transport = transport

    def list(self) -> list[SendingDomain]:
        data: Iterable[Any] = self._transport.get("v1/sending-domains") or []
        return [SendingDomain._parse(item) for item in data]

    def add(self, domain: str) -> SendingDomain:
        """Registers a domain and returns the DNS records to publish."""
        return SendingDomain._parse(
            self._transport.post("v1/sending-domains", {"domain": domain}) or {}
        )

    def verify(self, domain: str) -> SendingDomain:
        """Checks the DNS records you published.

        DNS propagation is not instant, so a first call that comes back unverified usually means
        "not yet" rather than "wrong" — wait and call again.
        """
        return SendingDomain._parse(
            self._transport.post(f"v1/sending-domains/{domain}/verify") or {}
        )

    def remove(self, domain: str) -> None:
        self._transport.delete(f"v1/sending-domains/{domain}")
