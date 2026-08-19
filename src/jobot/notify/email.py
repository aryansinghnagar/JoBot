"""Shared email/SMTP delivery (used by Weekly Digest and Outreach)."""

import smtplib
import ssl
from email.message import EmailMessage
from typing import Any

from jobot.config.manager import ConfigManager


class EmailSender:
    """Send email via SMTP. Credentials come from the `smtp.*` config keys
    (stored in the OS keyring per the config layer).

    Injectable `smtp_factory` makes this hermetically testable: it receives
    `(hostname, port)` and must return a context-managed SMTP-like object.
    """

    def __init__(
        self,
        config: ConfigManager | None = None,
        smtp_factory: Any = None,
    ) -> None:
        self.config = config or ConfigManager()
        self.smtp_factory = smtp_factory

    def is_configured(self) -> bool:
        host = self.config.get("smtp.host")
        port = self.config.get("smtp.port")
        from_addr = self.config.get("smtp.from")
        recipient = self.config.get("smtp.recipient")
        return bool(host and port and from_addr and recipient)

    def send(
        self,
        subject: str,
        body_html: str,
        body_text: str | None = None,
    ) -> tuple[bool, str]:
        if not self.is_configured():
            return False, "SMTP not configured (set smtp.host/port/user/password/from/recipient)"

        from_addr = str(self.config.get("smtp.from"))
        recipient = str(self.config.get("smtp.recipient"))
        host = str(self.config.get("smtp.host"))
        port = int(str(self.config.get("smtp.port", 587)))
        user = self.config.get("smtp.user")
        password = self.config.get("smtp.password")

        msg = EmailMessage()
        msg["From"] = from_addr
        msg["To"] = recipient
        msg["Subject"] = subject
        if body_text:
            msg.set_content(body_text)
        msg.add_alternative(body_html, subtype="html")

        try:
            if self.smtp_factory is not None:
                smtp = self.smtp_factory(host, port)
                ctx = None
            else:
                ctx = ssl.create_default_context()
                smtp = smtplib.SMTP(host, port, timeout=30)
            with smtp as s:
                s.starttls(context=ctx)
                if user and password:
                    s.login(str(user), str(password))
                s.sendmail(from_addr, [recipient], msg.as_string())
            return True, "sent"
        except Exception as exc:  # noqa: BLE001
            return False, f"SMTP error: {exc}"
