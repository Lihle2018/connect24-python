"""Addresses that will not be sent to."""

from __future__ import annotations

import urllib.parse
from typing import Any, Iterable

from .._transport import Transport
from ..models import Suppression


class Suppressions:
    """``client.suppressions``.

    Two kinds live here and they behave differently. A suppression the **recipient** created — an
    unsubscribe, a STOP reply, a spam complaint, the National Opt-Out Registry — cannot be removed
    by you, through this API or any other route. Only they can undo it, by opting in again.
    Suppressions created for other reasons, such as a mailbox that permanently rejected mail or an
    address you added by hand, you may remove.
    """

    def __init__(self, transport: Transport) -> None:
        self._transport = transport

    def list(self, limit: int = 100) -> list[Suppression]:
        data: Iterable[Any] = self._transport.get(f"v1/suppressions?limit={int(limit)}") or []
        return [Suppression._parse(item) for item in data]

    def add(self, address: str, reason: str | None = None) -> None:
        """Suppresses an address yourself, for somebody who asked you directly."""
        self._transport.post("v1/suppressions", {"address": address, "reason": reason})

    def remove(self, address: str) -> None:
        """Removes a suppression you are allowed to remove.

        Refused with a 403 when the recipient created it. That is not a bug to work around: acting
        on it would mean messaging somebody who said no.
        """
        self._transport.delete("v1/suppressions/" + urllib.parse.quote(address, safe=""))
