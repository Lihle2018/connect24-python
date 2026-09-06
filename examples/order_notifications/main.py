"""Runs the notifier for one demo order. Safe with a TEST key: the default recipient uses a
simulation local part (``queued@``) that never leaves the platform and costs nothing.

    set CONNECT24_ACCOUNT_ID=acc_...
    set CONNECT24_API_KEY=ck_test_...
    python main.py
"""

import os
import sys

from connect24 import Connect24
from order_notifier import Order, OrderNotifier, OutOfCreditError

client = Connect24.from_env()
notifier = OrderNotifier(client)

try:
    result = notifier.notify_shipped(
        Order(
            id="1042",
            customer_name="Thandi",
            email=os.environ.get("CONNECT24_EMAIL_TO", "queued@example.com"),
            phone=os.environ.get("CONNECT24_SMS_TO"),
            tracking_url="https://store.example/track/1042",
        )
    )
except OutOfCreditError as error:
    print(f"Top up before retrying: {error}", file=sys.stderr)
    raise SystemExit(1)

print(f"email: {result['email'].status}  {result['email'].detail}")
print(f"sms:   {result['sms'].status}  {result['sms'].detail}")
