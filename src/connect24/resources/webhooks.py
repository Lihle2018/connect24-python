"""Delivery events pushed to you."""

from __future__ import annotations

from typing import Any, Iterable, Sequence

from .._transport import Transport
from ..models import WebhookDelivery, WebhookEndpoint


class Webhooks:
    """``client.webhooks``.

    Registering an endpoint is only half of it — verify every request that arrives with
    :func:`connect24.verify_signature` before acting on it. The URL is public, so without that
    check anyone can tell your system a message bounced.
    """

    def __init__(self, transport: Transport) -> None:
        self._transport = transport

    def list(self) -> list[WebhookEndpoint]:
        data: Iterable[Any] = self._transport.get("v1/webhooks") or []
        return [WebhookEndpoint._parse(item) for item in data]

    def create(self, url: str, events: Sequence[str] | None = None) -> WebhookEndpoint:
        """Registers an endpoint.

        The signing secret is on the returned object and is shown **once**. Store it now; it cannot
        be read back later, only replaced.
        """
        body = {"url": url, "events": list(events) if events else None}
        return WebhookEndpoint._parse(self._transport.post("v1/webhooks", body) or {})

    def delete(self, endpoint_id: str) -> None:
        self._transport.delete(f"v1/webhooks/{endpoint_id}")

    def list_deliveries(self, limit: int = 100) -> list[WebhookDelivery]:
        """Recent attempts to reach your endpoints — the first place to look when events stop."""
        data: Iterable[Any] = self._transport.get(f"v1/webhooks/deliveries?limit={int(limit)}") or []
        return [WebhookDelivery._parse(item) for item in data]
