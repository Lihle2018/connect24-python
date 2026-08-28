"""The client. Create one and reuse it."""

from __future__ import annotations

import os

from ._transport import Transport
from .resources import (
    AccountResource,
    BillingResource,
    Messages,
    SendingDomains,
    Suppressions,
    Templates,
    Webhooks,
)

#: Where the API lives. Override with ``base_url`` to point at a sandbox.
DEFAULT_BASE_URL = "https://api.connect24.co.za"

DEFAULT_TIMEOUT_SECONDS = 30.0

#: Retries apply to rate limits, 5xx and connection failures — never to a 4xx, which would fail
#: identically however many times it is repeated.
DEFAULT_MAX_RETRIES = 2


class Connect24:
    """Entry point to the Connect24 communications API.

    Both credentials come from the portal, under **Settings → API keys**. The account id
    (``acc_…``) is safe to commit; the key (``ck_live_…``) is a secret and belongs in an
    environment variable or a secret store, never in source control — anyone holding it can send
    messages billed to you and attributed to you.

    ::

        from connect24 import Connect24

        client = Connect24(
            account_id="acc_3f9c1a7b4e2d",
            api_key=os.environ["CONNECT24_API_KEY"],
        )

        client.messages.send_sms("+27821234567", "Your order has shipped.")

    Or read both from the environment, which is what most deployments want::

        client = Connect24.from_env()

    The client holds no per-request state, so it is safe to share across threads.
    """

    def __init__(
        self,
        account_id: str,
        api_key: str,
        *,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
        max_retries: int = DEFAULT_MAX_RETRIES,
    ) -> None:
        if not account_id:
            raise ValueError("account_id is required — find it in the portal under Settings → API keys.")
        if not api_key:
            raise ValueError("api_key is required — find it in the portal under Settings → API keys.")

        transport = Transport(
            base_url=base_url,
            account_id=account_id,
            api_key=api_key,
            timeout=timeout,
            max_retries=max_retries,
        )

        self.account_id = account_id

        #: Send messages, and read back what happened to them.
        self.messages = Messages(transport)
        #: Stored bodies with placeholders.
        self.templates = Templates(transport)
        #: Addresses that will not be sent to.
        self.suppressions = Suppressions(transport)
        #: Delivery events pushed to you.
        self.webhooks = Webhooks(transport)
        #: Domains you have proved you control.
        self.sending_domains = SendingDomains(transport)
        #: Prepaid credit and the statement.
        self.billing = BillingResource(transport)
        #: Who you are, and which channels can send right now.
        self.account = AccountResource(transport)

    @classmethod
    def from_env(
        cls,
        *,
        base_url: str | None = None,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
        max_retries: int = DEFAULT_MAX_RETRIES,
    ) -> "Connect24":
        """Builds a client from ``CONNECT24_ACCOUNT_ID`` and ``CONNECT24_API_KEY``.

        ``CONNECT24_BASE_URL`` is honoured too, which is how a staging deployment points elsewhere
        without a code change.

        :raises RuntimeError: Either variable is missing, named so the message says which.
        """
        account_id = os.environ.get("CONNECT24_ACCOUNT_ID", "")
        api_key = os.environ.get("CONNECT24_API_KEY", "")

        missing = [
            name
            for name, value in (("CONNECT24_ACCOUNT_ID", account_id), ("CONNECT24_API_KEY", api_key))
            if not value
        ]
        if missing:
            raise RuntimeError(f"Missing environment variable(s): {', '.join(missing)}.")

        return cls(
            account_id=account_id,
            api_key=api_key,
            base_url=base_url or os.environ.get("CONNECT24_BASE_URL") or DEFAULT_BASE_URL,
            timeout=timeout,
            max_retries=max_retries,
        )

    def __repr__(self) -> str:
        # The key is deliberately absent. A client that prints its own credential ends up in a log.
        return f"<Connect24 account_id={self.account_id!r}>"
