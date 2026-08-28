"""Official Python client for the Connect24 communications API.

One interface for email, SMS and WhatsApp::

    from connect24 import Connect24

    client = Connect24.from_env()
    client.messages.send_sms("+27821234567", "Your order has shipped.")

Two things surprise people, both of them deliberate:

**Your ``from`` address is not used until you verify the domain.** Until then mail leaves from your
account's assigned address on ``connect24.co.za`` and yours becomes the Reply-To.

**There is no sender for SMS.** South African traffic routes from a shared originator pool, and
naming an identity you do not own is rejected by the network.
"""

from .client import DEFAULT_BASE_URL, Connect24
from .errors import Connect24ApiError, Connect24ConnectionError, Connect24Error
from .models import (
    AccountInfo,
    Balance,
    ChannelStatus,
    LedgerEntry,
    Message,
    MessageAccepted,
    SendingDomain,
    Suppression,
    Template,
    WebhookDelivery,
    WebhookEndpoint,
    WebhookEvent,
)
from .webhooks import DEFAULT_TOLERANCE_SECONDS, timestamp_of, verify_signature

__version__ = "0.1.0"

__all__ = [
    "Connect24",
    "DEFAULT_BASE_URL",
    "Connect24Error",
    "Connect24ApiError",
    "Connect24ConnectionError",
    "verify_signature",
    "timestamp_of",
    "DEFAULT_TOLERANCE_SECONDS",
    "WebhookEvent",
    "AccountInfo",
    "Balance",
    "ChannelStatus",
    "LedgerEntry",
    "Message",
    "MessageAccepted",
    "SendingDomain",
    "Suppression",
    "Template",
    "WebhookDelivery",
    "WebhookEndpoint",
    "__version__",
]
