"""The client and its transport, without touching the network."""

from __future__ import annotations

import json

import pytest

from connect24 import Connect24, Connect24ApiError
from connect24.errors import Connect24ApiError as ApiError
from connect24.models import Message, WebhookEvent


def test_requires_both_credentials():
    with pytest.raises(ValueError, match="account_id"):
        Connect24(account_id="", api_key="ck_live_x")

    with pytest.raises(ValueError, match="api_key"):
        Connect24(account_id="acc_1", api_key="")


def test_from_env_names_what_is_missing(monkeypatch):
    monkeypatch.delenv("CONNECT24_ACCOUNT_ID", raising=False)
    monkeypatch.setenv("CONNECT24_API_KEY", "ck_live_x")

    with pytest.raises(RuntimeError, match="CONNECT24_ACCOUNT_ID"):
        Connect24.from_env()


def test_from_env_builds_a_client(monkeypatch):
    monkeypatch.setenv("CONNECT24_ACCOUNT_ID", "acc_1")
    monkeypatch.setenv("CONNECT24_API_KEY", "ck_live_x")

    client = Connect24.from_env()

    assert client.account_id == "acc_1"
    assert client.messages is not None


def test_repr_does_not_leak_the_key():
    # A client that prints its own credential ends up in a log, and a log ends up in a ticket.
    client = Connect24(account_id="acc_1", api_key="ck_live_supersecret")

    assert "ck_live_supersecret" not in repr(client)
    assert "acc_1" in repr(client)


class TestErrors:
    def test_reads_the_api_error_message(self):
        body = json.dumps({"error": "Insufficient credit."})

        error = ApiError.from_response(402, body)

        assert error.status_code == 402
        assert "Insufficient credit." in str(error)

    def test_reads_validation_errors(self):
        body = json.dumps({"title": "Validation failed", "errors": {"to": ["Not a valid number."]}})

        error = ApiError.from_response(400, body)

        assert error.errors["to"] == ["Not a valid number."]
        assert "to: Not a valid number." in str(error)

    def test_survives_a_body_that_is_not_json(self):
        # A proxy returning an HTML 502 must not turn into a JSON parse error that hides the 502.
        error = ApiError.from_response(502, "<html>Bad Gateway</html>")

        assert error.status_code == 502
        assert "502" in str(error)

    def test_survives_an_empty_body(self):
        assert ApiError.from_response(500, "").status_code == 500


class TestModels:
    def test_message_status_helpers(self):
        delivered = Message._parse({"status": "Delivered"})
        failed = Message._parse({"status": "failed"})
        queued = Message._parse({"status": "queued"})

        assert delivered.is_delivered and not delivered.is_failed
        assert failed.is_failed and not failed.is_in_flight
        assert queued.is_in_flight

    def test_message_maps_the_from_field(self):
        # `from` is a Python keyword, so the attribute carries a trailing underscore.
        message = Message._parse({"from": "acc_1@connect24.co.za"})

        assert message.from_ == "acc_1@connect24.co.za"

    def test_keeps_the_raw_response(self):
        # So a field the API adds after this version shipped is still reachable.
        message = Message._parse({"id": "msg_1", "somethingNew": 42})

        assert message.raw["somethingNew"] == 42

    def test_parses_timestamps_including_a_trailing_z(self):
        message = Message._parse({"createdAt": "2026-08-28T10:00:00Z"})

        assert message.created_at is not None
        assert message.created_at.year == 2026

    def test_a_bad_timestamp_is_none_rather_than_an_exception(self):
        assert Message._parse({"createdAt": "not a date"}).created_at is None

    def test_webhook_event_parses_a_raw_body(self):
        event = WebhookEvent.parse('{"id":"evt_1","type":"message.delivered","messageId":"msg_1"}')

        assert event.id == "evt_1"
        assert event.type == "message.delivered"
        assert event.message_id == "msg_1"


class TestTransportBodies:
    def test_drops_nulls_before_sending(self):
        from connect24._transport import _without_nones

        # An absent `from` means "use my account's assigned address". An explicit null would be an
        # attempt to send from nothing, which the API rejects.
        body = _without_nones({"channel": "Sms", "to": "+27821234567", "from": None, "cc": None})

        assert body == {"channel": "Sms", "to": "+27821234567"}

    def test_drops_nulls_inside_nested_objects(self):
        from connect24._transport import _without_nones

        body = _without_nones({"content": {"type": "text", "text": "hi", "subject": None}})

        assert body == {"content": {"type": "text", "text": "hi"}}


def test_public_surface_is_exported():
    import connect24

    for name in ("Connect24", "Connect24ApiError", "verify_signature", "WebhookEvent"):
        assert hasattr(connect24, name), name

    assert Connect24ApiError is ApiError
