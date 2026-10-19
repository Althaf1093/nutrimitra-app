"""Sending email (password reset and verification codes) behind a small provider interface.

    ConsoleEmailProvider  default for development: the message is written to the server log, nothing is sent.
    ResendEmailProvider   used when RESEND_API_KEY and EMAIL_FROM are both set (https://resend.com, free tier).

Tests point RESEND_BASE_URL at a local fake, so they exercise the real Resend client without a key.
"""
import logging
import os
from typing import Optional

import httpx

logger = logging.getLogger("nutrimitra.mailer")

DEFAULT_RESEND_BASE_URL = "https://api.resend.com"


class EmailError(Exception):
    """The provider could not send the message."""


class EmailProvider:
    name = "base"

    async def send(self, to: str, subject: str, text: str) -> None:
        raise NotImplementedError


class ConsoleEmailProvider(EmailProvider):
    """Development default. The full message, including any code in it, goes to the log: do not use in production."""

    name = "console"

    async def send(self, to: str, subject: str, text: str) -> None:
        logger.info("EMAIL (console, not sent) to=%s subject=%r\n%s", to, subject, text)


class ResendEmailProvider(EmailProvider):
    name = "resend"

    def __init__(self, api_key: str, sender: str, base_url: str = DEFAULT_RESEND_BASE_URL):
        self.api_key = api_key
        self.sender = sender
        self.base_url = base_url.rstrip("/")

    async def send(self, to: str, subject: str, text: str) -> None:
        try:
            async with httpx.AsyncClient(timeout=20) as http:
                response = await http.post(
                    f"{self.base_url}/emails",
                    headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                    json={"from": self.sender, "to": [to], "subject": subject, "text": text},
                )
        except httpx.HTTPError as exc:
            raise EmailError(f"resend request failed: {type(exc).__name__}") from exc
        if response.status_code >= 300:
            # Log Resend's own reason, never the message or the key.
            raise EmailError(f"resend returned HTTP {response.status_code}: {response.text[:200]}")


def get_provider() -> EmailProvider:
    """Settings are read on each call, so a restart is the only thing needed after changing them."""
    api_key = (os.getenv("RESEND_API_KEY") or "").strip()
    sender = (os.getenv("EMAIL_FROM") or "").strip()
    if api_key and sender:
        return ResendEmailProvider(api_key, sender, os.getenv("RESEND_BASE_URL") or DEFAULT_RESEND_BASE_URL)
    return ConsoleEmailProvider()


async def send_email(to: str, subject: str, text: str, provider: Optional[EmailProvider] = None) -> bool:
    """Send one message; returns False (and logs why) instead of raising, so a mail problem never breaks the request."""
    provider = provider or get_provider()
    try:
        await provider.send(to, subject, text)
        return True
    except EmailError as exc:
        logger.error("Could not send email via %s: %s", provider.name, exc)
        return False
