"""Proving a webhook request really came from Connect24.

Your webhook URL is public, so anyone can POST to it. Without verification, anyone could tell your
system that a message bounced, that a customer unsubscribed, or that an invoice was paid.
**Verify every request before acting on it.**

Two things are easy to get wrong and both fail silently:

1. Verify against the **raw request body**, byte for byte as received. Parsing JSON and
   re-serialising it changes whitespace and key order, and the signature will no longer match.
2. Read the body **before** your framework consumes the stream. In Flask that is
   ``request.get_data()``; in Django ``request.body``; in FastAPI ``await request.body()`` — not a
   parsed model.

A Flask receiver, in full::

    from connect24 import WebhookEvent, verify_signature

    @app.post("/hooks/connect24")
    def connect24_hook():
        payload = request.get_data(as_text=True)          # raw body, not request.json
        signature = request.headers.get("X-Connect24-Signature", "")

        if not verify_signature(payload, signature, WEBHOOK_SECRET):
            return "", 401

        event = WebhookEvent.parse(payload)
        # Acknowledge fast and do the work elsewhere; anything not 2xx is retried.
        return "", 200

Delivery is at-least-once, so deduplicate on ``event.id``.
"""

from __future__ import annotations

import hashlib
import hmac
import time

#: How old a delivery may be and still be accepted. Five minutes leaves room for clock drift and a
#: slow network, while stopping a captured request from being replayed hours later.
DEFAULT_TOLERANCE_SECONDS = 300


def verify_signature(
    payload: str | bytes,
    signature_header: str,
    secret: str,
    tolerance_seconds: int = DEFAULT_TOLERANCE_SECONDS,
) -> bool:
    """Whether a webhook request is authentic and recent.

    :param payload: The raw request body, exactly as received.
    :param signature_header: The ``X-Connect24-Signature`` header, ``t=1770000000,v1=abc123…``.
    :param secret: The endpoint's signing secret (``whsec_…``). Keep it out of source control.
    :param tolerance_seconds: How old the delivery may be. Pass ``0`` to skip the age check — only
        sensible when replaying a captured request in a test.
    :returns: True when the signature matches and the timestamp is within tolerance.

    Never raises. A malformed header from an attacker returns False rather than becoming a 500,
    because an exception here would turn a forged request into an outage.
    """
    if not payload or not signature_header or not secret:
        return False

    parsed = _parse_header(signature_header)
    if parsed is None:
        return False

    timestamp, provided = parsed

    if tolerance_seconds > 0:
        age = time.time() - timestamp
        # Absolute, so a delivery stamped in the future — a forged request, or badly skewed
        # clocks — is refused too.
        if abs(age) > tolerance_seconds:
            return False

    body = payload.decode("utf-8") if isinstance(payload, bytes) else payload
    expected = _compute(secret, timestamp, body)

    # compare_digest, not ==: a plain comparison stops at the first differing character, and the
    # time it takes leaks how much of the signature an attacker has guessed correctly.
    return hmac.compare_digest(expected, provided)


def timestamp_of(signature_header: str) -> float | None:
    """When Connect24 signed the delivery, as a Unix timestamp, or None if the header is malformed."""
    parsed = _parse_header(signature_header)
    return parsed[0] if parsed else None


def _parse_header(header: str) -> tuple[int, str] | None:
    timestamp = 0
    signature = ""

    for part in header.split(","):
        key, separator, value = part.partition("=")
        if not separator:
            continue
        key, value = key.strip(), value.strip()
        if key == "t":
            try:
                timestamp = int(value)
            except ValueError:
                return None
        elif key == "v1":
            signature = value

    return (timestamp, signature) if timestamp > 0 and signature else None


def _compute(secret: str, timestamp: int, payload: str) -> str:
    """The HMAC covers ``"{timestamp}.{payload}"``, not the payload alone.

    That is what stops a captured request being replayed indefinitely: the timestamp is inside the
    signature, so an attacker cannot rewrite it to look recent without invalidating the whole thing.
    """
    signed = f"{timestamp}.{payload}".encode("utf-8")
    return hmac.new(secret.encode("utf-8"), signed, hashlib.sha256).hexdigest()
