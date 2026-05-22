from typing import Protocol, runtime_checkable

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


@runtime_checkable
class EmailClient(Protocol):
    async def send(
        self,
        to: str,
        subject: str,
        html: str,
        from_addr: str | None = None,
    ) -> None: ...


class ConsoleEmailClient:
    """Dev email backend: prints emails to stdout instead of sending."""

    async def send(self, to: str, subject: str, html: str, from_addr: str | None = None) -> None:
        logger.info(
            "email_console",
            to=to,
            subject=subject,
            from_addr=from_addr or settings.EMAIL_FROM,
            body_preview=html[:200],
        )


class ResendEmailClient:
    """Production email backend using Resend."""

    def __init__(self) -> None:
        import resend
        resend.api_key = settings.RESEND_API_KEY
        self._resend = resend

    async def send(self, to: str, subject: str, html: str, from_addr: str | None = None) -> None:
        self._resend.Emails.send({
            "from": from_addr or settings.EMAIL_FROM,
            "to": to,
            "subject": subject,
            "html": html,
        })
        logger.info("email_sent", to=to, subject=subject)


def get_email_client() -> EmailClient:
    if settings.EMAIL_BACKEND == "resend":
        return ResendEmailClient()
    return ConsoleEmailClient()
