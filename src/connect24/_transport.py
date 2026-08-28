"""Shared request plumbing.

Private on purpose: the shape of a Connect24 call is not part of the public surface, so it can
change without breaking anyone.

Built on the standard library rather than ``requests`` or ``httpx``. An SDK is a dependency of
somebody else's application, and every package it drags in is a version conflict waiting to be
theirs to resolve. What this needs — JSON over HTTPS with a few headers — ``urllib`` does perfectly
well.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from typing import Any, Mapping

from .errors import Connect24ApiError, Connect24ConnectionError

_USER_AGENT = "connect24-python"

#: Statuses worth trying again. A 429 says the rate limit is temporary; 5xx says the fault was
#: ours. A 4xx means the request itself is wrong, and repeating it changes nothing.
_RETRYABLE = frozenset({429, 500, 502, 503, 504})


class Transport:
    """Turns a path and a body into a call, and an error response into an exception."""

    def __init__(
        self,
        base_url: str,
        account_id: str,
        api_key: str,
        timeout: float,
        max_retries: int,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._account_id = account_id
        self._api_key = api_key
        self._timeout = timeout
        self._max_retries = max_retries

    def get(self, path: str) -> Any:
        return self._request("GET", path)

    def post(self, path: str, body: Any = None, *, idempotency_key: str | None = None) -> Any:
        return self._request("POST", path, body, idempotency_key=idempotency_key)

    def put(self, path: str, body: Any = None) -> Any:
        return self._request("PUT", path, body)

    def delete(self, path: str) -> None:
        self._request("DELETE", path)

    # ---------------------------------------------------------------- internals

    def _request(
        self,
        method: str,
        path: str,
        body: Any = None,
        *,
        idempotency_key: str | None = None,
    ) -> Any:
        url = f"{self._base_url}/{path.lstrip('/')}"
        payload = None
        if body is not None:
            payload = json.dumps(_without_nones(body)).encode("utf-8")

        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "X-Account-Id": self._account_id,
            "Accept": "application/json",
            "User-Agent": _USER_AGENT,
        }
        if payload is not None:
            headers["Content-Type"] = "application/json"
        if idempotency_key:
            headers["Idempotency-Key"] = idempotency_key

        attempt = 0
        while True:
            request = urllib.request.Request(url, data=payload, headers=headers, method=method)
            try:
                with urllib.request.urlopen(request, timeout=self._timeout) as response:
                    raw = response.read().decode("utf-8")
                    return json.loads(raw) if raw.strip() else None

            except urllib.error.HTTPError as error:
                raw = error.read().decode("utf-8", errors="replace")
                if error.code in _RETRYABLE and attempt < self._max_retries:
                    attempt += 1
                    time.sleep(_backoff(attempt))
                    continue
                raise Connect24ApiError.from_response(error.code, raw) from None

            except urllib.error.URLError as error:
                # The request never reached us, so whether it was applied is unknown. Retrying a
                # send here is safe only because the caller can pass an idempotency key — which is
                # exactly the situation that argument exists for.
                if attempt < self._max_retries:
                    attempt += 1
                    time.sleep(_backoff(attempt))
                    continue
                raise Connect24ConnectionError(str(error.reason)) from None


def _backoff(attempt: int) -> float:
    """Doubling, capped. Enough to let a rate limit clear without stalling a request thread."""
    return min(0.5 * (2 ** (attempt - 1)), 4.0)


def _without_nones(value: Any) -> Any:
    """Drops null members before sending.

    The API treats an absent field and an explicit null differently in places — an absent ``from``
    means "use my account's assigned address", where a null would be an attempt to send from
    nothing.
    """
    if isinstance(value, Mapping):
        return {k: _without_nones(v) for k, v in value.items() if v is not None}
    if isinstance(value, list):
        return [_without_nones(v) for v in value]
    return value
