"""E-mail: dagrapport, en een korte directe mail bij een belangrijke BLOCK."""

from __future__ import annotations

import os
import smtplib
from email.message import EmailMessage

from . import Message


class EmailNotifier:
    name = "email"

    def __init__(
        self,
        host: str | None = None,
        port: int | None = None,
        user: str | None = None,
        password: str | None = None,
        sender: str | None = None,
        recipient: str | None = None,
        use_tls: bool = True,
    ):
        self.host = host or os.environ.get("ORCH_SMTP_HOST", "")
        self.port = port or int(os.environ.get("ORCH_SMTP_PORT", "587"))
        self.user = user or os.environ.get("ORCH_SMTP_USER", "")
        self.password = password or os.environ.get("ORCH_SMTP_PASSWORD", "")
        self.sender = sender or os.environ.get("ORCH_MAIL_FROM", self.user)
        self.recipient = recipient or os.environ.get("ORCH_MAIL_TO", "")
        self.use_tls = use_tls

    @property
    def configured(self) -> bool:
        return bool(self.host and self.sender and self.recipient)

    def send(self, message: Message) -> str | None:
        if not self.configured:
            raise RuntimeError(
                "e-mail is niet ingesteld; zet ORCH_SMTP_HOST, ORCH_MAIL_FROM en ORCH_MAIL_TO"
            )
        mail = EmailMessage()
        prefix = "[orchestrator]" + (f"[{message.project}]" if message.project else "")
        mail["Subject"] = f"{prefix} {message.subject}"
        mail["From"] = self.sender
        mail["To"] = self.recipient
        mail.set_content(message.body)
        with smtplib.SMTP(self.host, self.port, timeout=30) as server:
            if self.use_tls:
                server.starttls()
            if self.user:
                server.login(self.user, self.password)
            server.send_message(mail)
        return None
