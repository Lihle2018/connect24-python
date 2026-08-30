"""The shapes the API returns.

Dataclasses rather than raw dicts, so an editor can complete ``message.status`` and a typo becomes
an error rather than a silent ``None``. Every one keeps the response it was built from in
:attr:`raw`, so a field added to the API after this version shipped is still reachable without
waiting for an SDK release.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


def _dt(value: Any) -> datetime | None:
    """Parses an API timestamp. Returns None rather than raising on anything unexpected."""
    if not isinstance(value, str) or not value:
        return None
    try:
        # fromisoformat did not accept a trailing Z before 3.11.
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


@dataclass
class _Model:
    raw: dict[str, Any] = field(default_factory=dict, repr=False)


@dataclass
class MessageAccepted(_Model):
    """The API has taken the message. It has not been delivered yet — that is what webhooks say."""

    id: str = ""
    channel: str = ""
    status: str = ""

    @classmethod
    def _parse(cls, data: dict[str, Any]) -> "MessageAccepted":
        return cls(
            raw=data,
            id=data.get("id", ""),
            channel=data.get("channel", ""),
            status=data.get("status", ""),
        )


@dataclass
class Message(_Model):
    """One message and where it got to."""

    id: str = ""
    channel: str = ""
    direction: str = ""
    from_: str = ""
    to: str = ""
    status: str = ""
    failure_reason: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @property
    def is_delivered(self) -> bool:
        return self.status.lower() == "delivered"

    @property
    def is_failed(self) -> bool:
        return self.status.lower() == "failed"

    @property
    def is_in_flight(self) -> bool:
        """Neither delivered nor failed — still on its way, or waiting for a sending window."""
        return not self.is_delivered and not self.is_failed

    @classmethod
    def _parse(cls, data: dict[str, Any]) -> "Message":
        return cls(
            raw=data,
            id=data.get("id", ""),
            channel=data.get("channel", ""),
            direction=data.get("direction", ""),
            # `from` is a keyword, so the attribute carries a trailing underscore, as PEP 8 says.
            from_=data.get("from", ""),
            to=data.get("to", ""),
            status=data.get("status", ""),
            failure_reason=data.get("failureReason"),
            created_at=_dt(data.get("createdAt")),
            updated_at=_dt(data.get("updatedAt")),
        )


@dataclass
class Template(_Model):
    id: str = ""
    name: str = ""
    subject: str | None = None
    html: str | None = None
    text: str | None = None
    version: int = 0

    @classmethod
    def _parse(cls, data: dict[str, Any]) -> "Template":
        return cls(
            raw=data,
            id=data.get("id", ""),
            name=data.get("name", ""),
            subject=data.get("subject"),
            html=data.get("html"),
            text=data.get("text"),
            version=int(data.get("version", 0) or 0),
        )


@dataclass
class Suppression(_Model):
    """An address that will not be sent to, and why."""

    address: str = ""
    reason: str = ""
    channel: str | None = None
    created_at: datetime | None = None

    @property
    def chosen_by_recipient(self) -> bool:
        """Whether the person asked for this.

        A suppression the recipient created cannot be removed by the sender — not through the API,
        not through the portal, not by asking support. Only they can undo it, by opting in again.
        """
        return self.reason.lower() in {"unsubscribed", "complained", "stopreply", "optoutregistry"}

    @classmethod
    def _parse(cls, data: dict[str, Any]) -> "Suppression":
        return cls(
            raw=data,
            address=data.get("address", ""),
            reason=data.get("reason", ""),
            channel=data.get("channel"),
            created_at=_dt(data.get("createdAt")),
        )


@dataclass
class Balance(_Model):
    """Prepaid credit. Every message is charged before it is sent."""

    amount: float = 0.0
    currency: str = "ZAR"

    @classmethod
    def _parse(cls, data: dict[str, Any]) -> "Balance":
        return cls(
            raw=data,
            amount=float(data.get("amount", 0) or 0),
            currency=data.get("currency", "ZAR"),
        )


@dataclass
class LedgerEntry(_Model):
    id: str = ""
    type: str = ""
    amount: float = 0.0
    description: str = ""
    created_at: datetime | None = None

    @classmethod
    def _parse(cls, data: dict[str, Any]) -> "LedgerEntry":
        return cls(
            raw=data,
            id=data.get("id", ""),
            type=data.get("type", ""),
            amount=float(data.get("amount", 0) or 0),
            description=data.get("description", ""),
            created_at=_dt(data.get("createdAt")),
        )


@dataclass
class AccountInfo(_Model):
    id: str = ""
    name: str = ""
    sender_address: str = ""

    @classmethod
    def _parse(cls, data: dict[str, Any]) -> "AccountInfo":
        return cls(
            raw=data,
            id=data.get("id", ""),
            name=data.get("name", ""),
            sender_address=data.get("senderAddress", ""),
        )


@dataclass
class ChannelStatus(_Model):
    """Whether a channel can send right now, and if not, what is missing."""

    channel: str = ""
    available: bool = False
    reason: str | None = None

    @classmethod
    def _parse(cls, data: dict[str, Any]) -> "ChannelStatus":
        return cls(
            raw=data,
            channel=data.get("channel", ""),
            available=bool(data.get("available", False)),
            reason=data.get("reason"),
        )


@dataclass
class SendingDomain(_Model):
    """A domain you are proving you control, so mail can go out as you rather than as us."""

    domain: str = ""
    verified: bool = False
    records: list[dict[str, Any]] = field(default_factory=list)

    @classmethod
    def _parse(cls, data: dict[str, Any]) -> "SendingDomain":
        return cls(
            raw=data,
            domain=data.get("domain", ""),
            verified=bool(data.get("verified", False)),
            records=list(data.get("records") or []),
        )


@dataclass
class WebhookEndpoint(_Model):
    id: str = ""
    url: str = ""
    events: list[str] = field(default_factory=list)
    #: Returned once, when the endpoint is created. Store it; it is not shown again.
    secret: str | None = None

    @classmethod
    def _parse(cls, data: dict[str, Any]) -> "WebhookEndpoint":
        return cls(
            raw=data,
            id=data.get("id", ""),
            url=data.get("url", ""),
            events=list(data.get("events") or []),
            secret=data.get("secret"),
        )


@dataclass
class WebhookDelivery(_Model):
    """One attempt to reach your endpoint. Useful when events are not arriving."""

    id: str = ""
    endpoint_id: str = ""
    event_type: str = ""
    status_code: int | None = None
    succeeded: bool = False
    attempts: int = 0
    created_at: datetime | None = None

    @classmethod
    def _parse(cls, data: dict[str, Any]) -> "WebhookDelivery":
        return cls(
            raw=data,
            id=data.get("id", ""),
            endpoint_id=data.get("endpointId", ""),
            event_type=data.get("eventType", ""),
            status_code=data.get("statusCode"),
            succeeded=bool(data.get("succeeded", False)),
            attempts=int(data.get("attempts", 0) or 0),
            created_at=_dt(data.get("createdAt")),
        )


@dataclass
class WebhookEvent(_Model):
    """A delivery event, parsed from a webhook request body."""

    id: str = ""
    type: str = ""
    message_id: str = ""
    created_at: datetime | None = None

    @classmethod
    def parse(cls, payload: str | bytes | dict[str, Any]) -> "WebhookEvent":
        """Reads an event from a raw webhook body.

        Verify the signature first — :func:`connect24.verify_signature`. Parsing an unverified body
        means acting on something anyone could have posted to your public URL.
        """
        import json as _json

        if isinstance(payload, (str, bytes)):
            data = _json.loads(payload)
        else:
            data = payload

        return cls(
            raw=data,
            id=data.get("id", ""),
            type=data.get("type", ""),
            message_id=data.get("messageId", ""),
            created_at=_dt(data.get("createdAt")),
        )
