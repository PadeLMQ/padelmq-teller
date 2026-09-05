"""De lus die blijft draaien.

Eén commando dat doet wat anders met de hand gebeurt: herstellen wat een vorige
ronde heeft achtergelaten, antwoorden uit GitHub ophalen, en werk afwerken tot
er niets meer te doen is. Daarna wachten en opnieuw.

Wat hier NIET gebeurt is de veiligheid oprekken. Elke ronde loopt door dezelfde
poorten als een handmatige run: dezelfde budgetremmen, dezelfde
verificatiecommando's, dezelfde weigering om te raden. Een lus die vaker draait
mag niet méér mogen.
"""

from __future__ import annotations

import time
from dataclasses import dataclass


@dataclass
class Ronde:
    hersteld: int = 0
    antwoorden: int = 0
    taken: int = 0
    fouten: int = 0

    @property
    def stil(self) -> bool:
        return not (self.hersteld or self.antwoorden or self.taken or self.fouten)


class Serve:
    """Voert rondes uit. De klok en het werk zijn injecteerbaar, zodat een test
    dit kan doorlopen zonder te wachten en zonder te betalen."""

    def __init__(self, *, recover_fn, poll_fn, work_fn, sleep_fn=time.sleep,
                 interval: int = 60, on_event=None):
        self.recover_fn = recover_fn
        self.poll_fn = poll_fn
        self.work_fn = work_fn
        self.sleep_fn = sleep_fn
        self.interval = interval
        self.on_event = on_event or (lambda tekst: None)

    def _veilig(self, naam: str, fn, ronde: Ronde) -> int:
        """Een fout in één onderdeel mag de lus niet stoppen.

        Draait er iets 24/7, dan is omvallen bij de eerste hapering geen optie;
        maar stilzwijgend doorgaan evenmin, dus alles wordt gemeld.
        """
        try:
            return int(fn() or 0)
        except Exception as exc:  # noqa: BLE001
            ronde.fouten += 1
            self.on_event(f"{naam} mislukte: {type(exc).__name__}: {exc}")
            return 0

    def ronde(self) -> Ronde:
        r = Ronde()
        r.hersteld = self._veilig("herstel", self.recover_fn, r)
        r.antwoorden = self._veilig("antwoorden ophalen", self.poll_fn, r)
        r.taken = self._veilig("werk afwerken", self.work_fn, r)
        return r

    def run(self, *, rondes: int | None = None) -> list[Ronde]:
        """Draait tot 'rondes' op is, of eeuwig als het None is."""
        uit: list[Ronde] = []
        n = 0
        while rondes is None or n < rondes:
            r = self.ronde()
            uit.append(r)
            n += 1
            if rondes is not None and n >= rondes:
                break
            # Was er werk, dan meteen door: er staat waarschijnlijk meer klaar.
            # Was het stil, dan wachten in plaats van de API afstruinen.
            if r.stil:
                self.sleep_fn(self.interval)
        return uit
