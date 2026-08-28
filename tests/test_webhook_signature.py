"""Signature verification.

Tested harder than anything else here, because it is the only part of the SDK that is a security
control. Everything else fails loudly when it is wrong; this one fails by quietly accepting a
forged request.
"""

from __future__ import annotations

import hashlib
import hmac
import time

import pytest

from connect24 import timestamp_of, verify_signature

SECRET = "whsec_test"
PAYLOAD = '{"id":"evt_1","type":"message.delivered","messageId":"msg_1"}'


def header(payload: str = PAYLOAD, secret: str = SECRET, at: int | None = None) -> str:
    at = at if at is not None else int(time.time())
    signed = f"{at}.{payload}".encode()
    digest = hmac.new(secret.encode(), signed, hashlib.sha256).hexdigest()
    return f"t={at},v1={digest}"


def test_accepts_a_genuine_recent_delivery():
    assert verify_signature(PAYLOAD, header(), SECRET) is True


def test_accepts_bytes_as_well_as_text():
    # Flask hands you bytes, Django hands you bytes, FastAPI hands you bytes. Requiring str would
    # push every caller into a decode they might do with the wrong codec.
    assert verify_signature(PAYLOAD.encode("utf-8"), header(), SECRET) is True


def test_rejects_a_payload_that_was_altered():
    tampered = PAYLOAD.replace("delivered", "bounced")
    assert verify_signature(tampered, header(), SECRET) is False


def test_rejects_the_wrong_secret():
    assert verify_signature(PAYLOAD, header(secret="whsec_other"), SECRET) is False


def test_rejects_a_delivery_that_is_too_old():
    # The signature is still valid; the point is that a captured request cannot be replayed
    # tomorrow.
    old = header(at=int(time.time()) - 3600)
    assert verify_signature(PAYLOAD, old, SECRET) is False


def test_rejects_a_delivery_stamped_in_the_future():
    # Not symmetry for its own sake: a future timestamp means either a forged request or a badly
    # skewed clock, and neither should be trusted.
    ahead = header(at=int(time.time()) + 3600)
    assert verify_signature(PAYLOAD, ahead, SECRET) is False


def test_tolerance_of_zero_skips_the_age_check():
    old = header(at=1_600_000_000)
    assert verify_signature(PAYLOAD, old, SECRET, tolerance_seconds=0) is True


@pytest.mark.parametrize(
    "bad_header",
    [
        "",
        "garbage",
        "t=,v1=abc",
        "t=notanumber,v1=abc",
        "v1=abc",
        "t=1770000000",
        "t=1770000000,v1=",
    ],
)
def test_a_malformed_header_returns_false_rather_than_raising(bad_header):
    # An exception here would let an attacker turn a forged request into a 500, which is a denial
    # of service on an endpoint that is supposed to be resilient.
    assert verify_signature(PAYLOAD, bad_header, SECRET) is False


@pytest.mark.parametrize("payload,sig,secret", [("", "t=1,v1=a", SECRET), (PAYLOAD, "", SECRET), (PAYLOAD, "t=1,v1=a", "")])
def test_missing_inputs_return_false(payload, sig, secret):
    assert verify_signature(payload, sig, secret) is False


def test_timestamp_of_reads_the_header():
    at = 1_770_000_000
    assert timestamp_of(header(at=at)) == at


def test_timestamp_of_returns_none_when_malformed():
    assert timestamp_of("nonsense") is None
