"""Modulaire meldlaag. V1 levert e-mail en GitHub; andere kanalen zijn later
één extra adapter plus een regel configuratie — de lus verandert er niet van.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol


@dataclass
class Message:
    subject: str
    body: str
    project: str = ""
    urgent: bool = False
    labels: list[str] = field(default_factory=list)


class Notifier(Protocol):
    name: str

    def send(self, message: Message) -> str | None:
        """Verstuurt de melding. Geeft optioneel een referentie terug (bv. issuenummer)."""


class ConsoleNotifier:
    """Standaardkanaal tijdens ontwikkeling en in tests."""

    name = "console"

    def __init__(self) -> None:
        self.sent: list[Message] = []

    def send(self, message: Message) -> str | None:
        self.sent.append(message)
        marker = "!" if message.urgent else " "
        print(f"[{marker}] {message.project}: {message.subject}")
        return None


class MultiNotifier:
    name = "multi"

    def __init__(self, *notifiers: Notifier):
        self.notifiers = [n for n in notifiers if n is not None]

    def send(self, message: Message) -> str | None:
        reference = None
        for notifier in self.notifiers:
            try:
                result = notifier.send(message)
                reference = reference or result
            except Exception as exc:  # een kapot kanaal mag de lus niet stoppen
                print(f"melding via {notifier.name} mislukt: {exc}")
        return reference
