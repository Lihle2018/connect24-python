"""These tests drive the notifier through the REAL SDK with ``urllib.request.urlopen``
stubbed, so they verify what actually goes on the wire — payloads, headers, idempotency
keys — without a network or an API key. Run with ``pytest`` in this folder.
"""

from __future__ import annotations

import io
import json
import urllib.error

import pytest

from connect24 import Connect24
from order_notifier import Order, OrderNotifier, OutOfCreditError


class StubHttp:
    """Records every request the SDK makes and replies with whatever the test queued."""

    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def __call__(self, request, timeout=None):
        self.calls.append(request)
        status, body = self.responses.pop(0) if len(self.responses) > 1 else self.responses[0]
        if status >= 400:
            raise urllib.error.HTTPError(
                request.full_url, status, "refused", hdrs=None, fp=io.BytesIO(body.encode())
            )
        response = io.BytesIO(body.encode())
        response.__enter__ = lambda *a: response
        response.__exit__ = lambda *a: False
        return response


@pytest.fixture
def wire(monkeypatch):
    def arm(*responses):
        stub = StubHttp(responses)
        monkeypatch.setattr("urllib.request.urlopen", stub)
        return stub

    return arm


ORDER = Order(
    id="1042",
    customer_name="Thandi",
    email="thandi@example.co.za",
    phone="+27821234567",
    tracking_url="https://store.example/track/1042",
)


def notifier() -> OrderNotifier:
    return OrderNotifier(Connect24(account_id="acc_1", api_key="ck_test_x", max_retries=0))


def sent_body(request) -> dict:
    return json.loads(request.data.decode())


def test_sends_email_and_sms_with_idempotency_keys_tied_to_the_order(wire):
    stub = wire((200, json.dumps({"id": "msg_1", "status": "queued"})))

    result = notifier().notify_shipped(ORDER)

    assert result["email"].status == "sent"
    assert result["sms"].status == "sent"
    assert len(stub.calls) == 2

    email, sms = stub.calls
    assert sent_body(email)["channel"] == "Email"
    assert sent_body(email)["to"] == ORDER.email
    assert "1042" in sent_body(email)["content"]["html"]
    assert email.get_header("Idempotency-key") == "order-1042-shipped-email"

    assert sent_body(sms)["channel"] == "Sms"
    assert sent_body(sms)["to"] == ORDER.phone
    assert sms.get_header("Idempotency-key") == "order-1042-shipped-sms"


def test_skips_the_sms_when_no_phone_is_on_file(wire):
    stub = wire((200, json.dumps({"id": "msg_1"})))

    result = notifier().notify_shipped(Order(**{**ORDER.__dict__, "phone": None}))

    assert result["sms"].status == "skipped"
    assert len(stub.calls) == 1  # only the email went out


def test_treats_a_suppressed_recipient_as_a_skip_not_a_failure(wire):
    wire(
        (403, json.dumps({"error": "That recipient is on your suppression list and cannot be contacted."})),
        (200, json.dumps({"id": "msg_2", "status": "queued"})),
    )

    result = notifier().notify_shipped(ORDER)

    assert result["email"].status == "skipped"
    assert "suppression list" in result["email"].detail
    assert result["sms"].status == "sent"  # one refused channel must not block the other


def test_surfaces_an_empty_balance_as_out_of_credit(wire):
    wire((402, json.dumps({"error": "Insufficient credit."})))

    with pytest.raises(OutOfCreditError):
        notifier().notify_shipped(ORDER)


def test_lets_unexpected_errors_escape_for_the_caller_to_retry(wire):
    wire((500, json.dumps({"error": "boom"})))

    with pytest.raises(Exception, match="boom"):
        notifier().notify_shipped(ORDER)
