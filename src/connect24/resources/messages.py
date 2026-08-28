"""Sending, and reading back what happened."""

from __future__ import annotations

from typing import Any, Iterable, Mapping, Sequence

from .._transport import Transport
from ..models import Message, MessageAccepted


class Messages:
    """``client.messages`` — every channel through one shape."""

    def __init__(self, transport: Transport) -> None:
        self._transport = transport

    # ------------------------------------------------------------------ sending

    def send(
        self,
        *,
        channel: str,
        to: str,
        content: Mapping[str, Any],
        sender: Mapping[str, Any] | None = None,
        cc: Sequence[str] | None = None,
        bcc: Sequence[str] | None = None,
        reply_to: str | None = None,
        attachments: Sequence[Mapping[str, Any]] | None = None,
        headers: Mapping[str, str] | None = None,
        tags: Sequence[str] | None = None,
        metadata: Mapping[str, str] | None = None,
        template: str | None = None,
        variables: Mapping[str, str] | None = None,
        provider: str | None = None,
        idempotency_key: str | None = None,
    ) -> MessageAccepted:
        """Sends one message.

        Prefer :meth:`send_sms`, :meth:`send_email` or :meth:`send_whatsapp` — this is the full
        shape underneath them, for the cases they do not cover.

        :param idempotency_key: Pass one when a network failure leaves you unsure whether a send
            arrived. A repeat with the same key returns the original message rather than sending a
            second copy. Anything stable and unique to the event works — an order id, not a UUID
            generated at call time, which would be different on the retry and defeat the point.
        """
        body: dict[str, Any] = {
            "channel": channel,
            "to": to,
            "content": dict(content),
            "from": dict(sender) if sender else None,
            "cc": list(cc) if cc else None,
            "bcc": list(bcc) if bcc else None,
            "replyTo": reply_to,
            "attachments": [dict(a) for a in attachments] if attachments else None,
            "headers": dict(headers) if headers else None,
            "tags": list(tags) if tags else None,
            "metadata": dict(metadata) if metadata else None,
            "template": template,
            "variables": dict(variables) if variables else None,
            "provider": provider,
        }
        data = self._transport.post("v1/messages", body, idempotency_key=idempotency_key)
        return MessageAccepted._parse(data or {})

    def send_sms(
        self,
        to: str,
        text: str,
        *,
        idempotency_key: str | None = None,
        **extra: Any,
    ) -> MessageAccepted:
        """Sends an SMS.

        There is no ``sender`` argument, deliberately. South African traffic leaves from a shared
        originator pool, and naming an identity you do not own is rejected by the network rather
        than by us.

        Watch what you put in ``text``. An SMS holds 160 characters using the GSM-7 alphabet; a
        single emoji, curly quote or em dash switches the whole message to UCS-2, which holds 70 per
        part. A 150-character message with one emoji costs three SMS, not one.
        """
        return self.send(
            channel="Sms",
            to=to,
            content={"type": "text", "text": text},
            idempotency_key=idempotency_key,
            **extra,
        )

    def send_email(
        self,
        to: str,
        subject: str,
        *,
        html: str | None = None,
        text: str | None = None,
        sender: Mapping[str, Any] | None = None,
        idempotency_key: str | None = None,
        **extra: Any,
    ) -> MessageAccepted:
        """Sends an email.

        ``sender`` is not used until you verify the domain it belongs to. Until then mail leaves
        from your account's assigned address on ``connect24.co.za`` and the address you give here
        becomes the Reply-To — so replies still reach you, but the envelope is ours. Verify with
        ``client.sending_domains.add("acme.co.za")``, publish the DNS records it returns, then
        ``verify``.
        """
        content: dict[str, Any] = {"type": "html" if html else "text", "subject": subject}
        if html:
            content["html"] = html
        if text:
            content["text"] = text

        return self.send(
            channel="Email",
            to=to,
            content=content,
            sender=sender,
            idempotency_key=idempotency_key,
            **extra,
        )

    def send_whatsapp(
        self,
        to: str,
        text: str | None = None,
        *,
        template_name: str | None = None,
        variables: Mapping[str, str] | None = None,
        idempotency_key: str | None = None,
        **extra: Any,
    ) -> MessageAccepted:
        """Sends a WhatsApp message.

        Free-form text only works inside the 24-hour window that opens when the customer last
        messaged you. Outside it, WhatsApp requires an approved template — pass ``template_name``.
        Sending free-form outside the window is refused by WhatsApp, not by us.
        """
        if not text and not template_name:
            raise ValueError("Give either text, or template_name for a message outside the 24-hour window.")

        content: dict[str, Any] = {"type": "text"}
        if text:
            content["text"] = text
        if template_name:
            content["templateName"] = template_name

        return self.send(
            channel="WhatsApp",
            to=to,
            content=content,
            variables=variables,
            idempotency_key=idempotency_key,
            **extra,
        )

    def send_template(
        self,
        channel: str,
        to: str,
        template: str,
        variables: Mapping[str, str] | None = None,
        *,
        idempotency_key: str | None = None,
        **extra: Any,
    ) -> MessageAccepted:
        """Sends a stored template, with values substituted into its placeholders."""
        return self.send(
            channel=channel,
            to=to,
            content={"type": "template"},
            template=template,
            variables=variables,
            idempotency_key=idempotency_key,
            **extra,
        )

    # ------------------------------------------------------------------ reading

    def get(self, message_id: str) -> Message:
        """One message, with its current status and why it failed if it did."""
        return Message._parse(self._transport.get(f"v1/messages/{message_id}") or {})

    def list(self, limit: int = 100) -> list[Message]:
        """The most recent messages, newest first."""
        data: Iterable[Any] = self._transport.get(f"v1/messages?limit={int(limit)}") or []
        return [Message._parse(item) for item in data]
