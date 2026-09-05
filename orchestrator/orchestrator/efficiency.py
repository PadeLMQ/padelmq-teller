"""AI-efficiëntie: wat leverde geld op, en wat niet.

Een totaalbedrag zegt weinig. De vraag is of het besteed is aan werk dat
overeind bleef of aan rondjes die opnieuw moesten. In de B7-pilot was 68% van
$1.229464 verspild aan defecten, en dat was pas zichtbaar toen het apart geteld
werd.

Er wordt hier niets geschat en niets herrekend. Verspilling telt alleen als ze
gemarkeerd is: een run die crashte, of een aanroep die expliciet als verspild is
aangemerkt. Wat niet gemarkeerd is, geldt als nuttig -- te weinig verspilling
melden is beter dan nuttig werk verdacht maken.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field


@dataclass
class Efficiency:
    useful: float = 0.0
    wasted: float = 0.0
    reasons: dict[str, float] = field(default_factory=dict)
    reused: int = 0
    calls_useful: int = 0
    calls_wasted: int = 0

    @property
    def total(self) -> float:
        return self.useful + self.wasted

    @property
    def wasted_pct(self) -> float:
        return (self.wasted / self.total * 100) if self.total else 0.0


def measure(scope, day: str | None = None) -> Efficiency:
    """Telt de aanroepen van een project, eventueel voor één dag."""
    where = "project_id = ?"
    params: list = [scope.project_id]
    if day:
        where += " AND day = ?"
        params.append(day)

    eff = Efficiency()
    for rij in scope.conn.execute(
        f"SELECT cost_eur, wasted_reason FROM calls WHERE {where}", tuple(params)
    ):
        reden = rij["wasted_reason"]
        bedrag = float(rij["cost_eur"] or 0.0)
        if reden:
            eff.wasted += bedrag
            eff.calls_wasted += 1
            eff.reasons[reden] = eff.reasons.get(reden, 0.0) + bedrag
        else:
            eff.useful += bedrag
            eff.calls_useful += 1

    # Elke hervatting die bestaand werk hergebruikte, is een betaalde aanroep
    # die niet gedaan hoefde te worden.
    for rij in scope.conn.execute(
        "SELECT payload FROM events WHERE project_id = ? AND kind = 'hervatting'",
        (scope.project_id,),
    ):
        payload = json.loads(rij["payload"])
        if "hergebruikt" in (payload.get("besluit") or ""):
            eff.reused += 1
    return eff


def format_efficiency(eff: Efficiency, symbol: str = "$") -> str:
    regels = [
        "AI-efficiëntie",
        f"  nuttig          {symbol}{eff.useful:.6f}  ({eff.calls_useful} aanroepen)",
        f"  verspild        {symbol}{eff.wasted:.6f}  ({eff.calls_wasted} aanroepen)",
        f"  totaal          {symbol}{eff.total:.6f}",
        f"  verspild        {eff.wasted_pct:.1f}%",
    ]
    if eff.reasons:
        regels.append("  reden van verspilling:")
        for reden, bedrag in sorted(eff.reasons.items(), key=lambda kv: -kv[1]):
            regels.append(f"    {symbol}{bedrag:.6f}  {reden}")
    regels.append(
        f"  hergebruikt     {eff.reused} keer bestaand werk hergebruikt"
        f" (evenzoveel betaalde aanroepen vermeden)"
    )
    return "\n".join(regels)
