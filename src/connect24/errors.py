"""What goes wrong, and how to tell the cases apart."""

from __future__ import annotations

import json
from typing import Any


class Connect24Error(Exception):
    """Base class, so ``except Connect24Error`` catches everything this library raises."""


class Connect24ConnectionError(Connect24Error):
    """The request never got an answer — DNS, TLS, a timeout, a dropped connection.

    Distinct from :class:`Connect24ApiError` because the outcome is genuinely unknown: the message
    may have been sent. Retry with the same ``idempotency_key`` and you will get the original
    message back rather than a second copy.
    """


class Connect24ApiError(Connect24Error):
    """The API answered, and said no.

    :attr:`status_code` says what kind of problem it was:

    ``400``
        The request is malformed. Repeating it unchanged will fail again.
    ``401``
        The API key is wrong, revoked, or belongs to another account.
    ``402``
        Out of credit. Top up; retrying will not help.
    ``409``
        A conflict — usually a name already taken.
    ``429``
        Rate limited. The client already retried this a few times before giving up.
    ``502``
        The message could not be handed on for delivery. Safe to retry.
    """

    def __init__(self, status_code: int, message: str, *, errors: dict[str, list[str]] | None = None):
        super().__init__(message)
        self.status_code = status_code
        #: Field-level validation messages, when the API returned any.
        self.errors = errors or {}

    def __str__(self) -> str:
        base = super().__str__()
        if not self.errors:
            return base
        detail = "; ".join(f"{field}: {', '.join(messages)}" for field, messages in self.errors.items())
        return f"{base} ({detail})"

    @classmethod
    def from_response(cls, status_code: int, body: str | None) -> "Connect24ApiError":
        """Unwraps whichever error shape the API used, so the message says what actually happened.

        Falling back to the status code alone is deliberate rather than lazy: an error body that is
        HTML from a proxy, or empty, should still produce something a caller can act on instead of
        a parse failure hiding the real problem.
        """
        if not body or not body.strip():
            return cls(status_code, f"The request failed ({status_code}).")

        try:
            parsed: Any = json.loads(body)
        except ValueError:
            return cls(status_code, f"The request failed ({status_code}): {body[:200]}")

        if not isinstance(parsed, dict):
            return cls(status_code, f"The request failed ({status_code}).")

        # ASP.NET validation problems put the useful part under "errors".
        raw_errors = parsed.get("errors")
        errors: dict[str, list[str]] = {}
        if isinstance(raw_errors, dict):
            for field, messages in raw_errors.items():
                if isinstance(messages, list):
                    errors[str(field)] = [str(m) for m in messages]
                else:
                    errors[str(field)] = [str(messages)]

        message = (
            parsed.get("error")
            or parsed.get("detail")
            or parsed.get("title")
            or parsed.get("message")
            or f"The request failed ({status_code})."
        )
        return cls(status_code, str(message), errors=errors)
