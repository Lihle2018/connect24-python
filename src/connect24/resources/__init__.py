"""Resource groups, one per area of the API."""

from .account import AccountResource
from .billing import BillingResource
from .messages import Messages
from .sending_domains import SendingDomains
from .suppressions import Suppressions
from .templates import Templates
from .webhooks import Webhooks

__all__ = [
    "AccountResource",
    "BillingResource",
    "Messages",
    "SendingDomains",
    "Suppressions",
    "Templates",
    "Webhooks",
]
