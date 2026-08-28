"""Prepaid credit, and where it went."""

from __future__ import annotations

from typing import Any, Iterable

from .._transport import Transport
from ..models import Balance, LedgerEntry


class BillingResource:
    """``client.billing``."""

    def __init__(self, transport: Transport) -> None:
        self._transport = transport

    def balance(self) -> Balance:
        """Credit remaining.

        Every message is charged before it is sent. When the balance cannot cover one the send is
        refused with a 402 rather than silently dropped, so a low balance surfaces as an error you
        can act on instead of as messages quietly not arriving.
        """
        return Balance._parse(self._transport.get("v1/balance") or {})

    def ledger(self, limit: int = 100) -> list[LedgerEntry]:
        """Every credit and debit, with what caused it."""
        data: Iterable[Any] = self._transport.get(f"v1/ledger?limit={int(limit)}") or []
        return [LedgerEntry._parse(item) for item in data]
