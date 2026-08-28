"""Who you are, and what can send right now."""

from __future__ import annotations

from typing import Any, Iterable

from .._transport import Transport
from ..models import AccountInfo, ChannelStatus


class AccountResource:
    """``client.account``."""

    def __init__(self, transport: Transport) -> None:
        self._transport = transport

    def get(self) -> AccountInfo:
        """Your account, including the sending address assigned to it."""
        return AccountInfo._parse(self._transport.get("v1/account") or {})

    def channels(self) -> list[ChannelStatus]:
        """Which channels can send, and for those that cannot, what is missing.

        Worth calling at start-up in a deployment you did not configure yourself: it answers
        "why is nothing sending" without waiting for a failed message to tell you.
        """
        data: Iterable[Any] = self._transport.get("v1/channels") or []
        return [ChannelStatus._parse(item) for item in data]
