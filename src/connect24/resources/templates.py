"""Stored message bodies, so copy lives on the platform rather than in your deploy."""

from __future__ import annotations

from typing import Any, Iterable

from .._transport import Transport
from ..models import Template


class Templates:
    """``client.templates``."""

    def __init__(self, transport: Transport) -> None:
        self._transport = transport

    def list(self, limit: int = 100) -> list[Template]:
        data: Iterable[Any] = self._transport.get(f"v1/templates?limit={int(limit)}") or []
        return [Template._parse(item) for item in data]

    def create(
        self,
        name: str,
        *,
        subject: str | None = None,
        html: str | None = None,
        text: str | None = None,
    ) -> Template:
        """Creates a template.

        Placeholders are written ``{{name}}`` and filled at send time from the ``variables`` you
        pass. A placeholder with no matching variable is left as-is rather than blanked, so a
        missing value shows up in a test message instead of silently sending an empty sentence.
        """
        body = {"name": name, "subject": subject, "html": html, "text": text}
        return Template._parse(self._transport.post("v1/templates", body) or {})

    def update(
        self,
        template_id: str,
        *,
        name: str | None = None,
        subject: str | None = None,
        html: str | None = None,
        text: str | None = None,
    ) -> Template:
        """Updates a template, which bumps its version.

        The version is why editing is safe: a message already sent stays traceable to the body that
        produced it, rather than appearing to have said whatever the template says today.
        """
        body = {"name": name, "subject": subject, "html": html, "text": text}
        return Template._parse(self._transport.put(f"v1/templates/{template_id}", body) or {})

    def delete(self, template_id: str) -> None:
        self._transport.delete(f"v1/templates/{template_id}")
