"""Order-shipped notifications — the shape most Connect24 integrations take.

A store's backend calls ``notify_shipped(order)`` when a parcel leaves the warehouse. The
service emails the customer, texts them when a phone number is on file, and answers the
three questions every real integration has to answer:

* **What if this runs twice for the same order** (a retry, a replayed queue message)?
  Idempotency keys derived from the order id: the API returns the original message instead
  of sending a second copy, so calling this twice is always safe.
* **What if the customer opted out?** The API refuses with a 403. That is not an error in
  your system — it is the suppression list doing its job — so it comes back as a
  ``skipped`` outcome, not an exception.
* **What if the account is out of credit?** A 402 means every further send will also fail,
  so that one raises :class:`OutOfCreditError` for the caller to alert on.
"""

from __future__ import annotations

from dataclasses import dataclass

from connect24 import Connect24
from connect24.errors import Connect24ApiError


class OutOfCreditError(Exception):
    """The Connect24 account cannot cover the send. Top up; retrying will not help."""


@dataclass(frozen=True)
class Order:
    id: str
    customer_name: str
    email: str
    tracking_url: str
    phone: str | None = None


@dataclass(frozen=True)
class Outcome:
    status: str  # "sent" | "skipped"
    detail: str  # the message id, or why it was skipped


class OrderNotifier:
    """Give it a configured :class:`connect24.Connect24` client and call it per order."""

    def __init__(self, client: Connect24) -> None:
        self._client = client

    def notify_shipped(self, order: Order) -> dict[str, Outcome]:
        email = self._deliver(
            lambda: self._client.messages.send_email(
                order.email,
                f"Order {order.id} is on its way",
                html=(
                    f"<p>Hi {order.customer_name},</p>"
                    f"<p>Your order <strong>{order.id}</strong> has shipped. "
                    f'<a href="{order.tracking_url}">Track it here</a>.</p>'
                ),
                text=f"Hi {order.customer_name}, your order {order.id} has shipped. Track it: {order.tracking_url}",
                # Stable and tied to the event — NOT a UUID minted at call time, which would
                # differ on a retry and defeat the point.
                idempotency_key=f"order-{order.id}-shipped-email",
                metadata={"orderId": order.id},
            )
        )

        if order.phone:
            sms = self._deliver(
                lambda: self._client.messages.send_sms(
                    order.phone,
                    # Plain GSM-7 characters only: one emoji or curly quote turns 1 SMS into 3.
                    f"Your order {order.id} has shipped. Track it: {order.tracking_url}",
                    idempotency_key=f"order-{order.id}-shipped-sms",
                    metadata={"orderId": order.id},
                )
            )
        else:
            sms = Outcome("skipped", "no phone number on file")

        return {"email": email, "sms": sms}

    @staticmethod
    def _deliver(send) -> Outcome:
        try:
            accepted = send()
            return Outcome("sent", accepted.id or "")
        except Connect24ApiError as error:
            if error.status_code == 403:
                # Most often the suppression list: the person opted out or hard-bounced
                # before. Retrying will never succeed, and contacting them anyway is the one
                # thing a messaging integration must never do.
                return Outcome("skipped", str(error))
            if error.status_code == 402:
                raise OutOfCreditError(str(error)) from error
            # Everything else (bad request, 5xx) surfaces. A connection error is safe to
            # retry with the SAME order — the idempotency keys make the retry return the
            # original message instead of sending twice.
            raise
