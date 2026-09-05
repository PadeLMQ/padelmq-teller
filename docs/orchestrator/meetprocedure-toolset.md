# Meetprocedure — kosten van de uitvoerderscontext

Klaar om uitgevoerd te worden zodra het dagbudget dat toelaat. **Nog niet
gedraaid**: de dag waarop deze procedure geschreven is stond al op $5,313365,
boven de veiligheidsgrens van $5.

## Wat we willen weten

Of `--tools` de contextbelasting verder verlaagt dan `--strict-mcp-config` alleen
al deed, en met hoeveel. Niet of het "werkt" — dat is deterministisch al
vastgelegd in `tests/test_toolset.py`.

## Uitgangspunt om tegen af te zetten

De vorige meting, geboekt in de audittrail als fase `meting`:

| | |
|---|---|
| prompt | 286 tekens (~71 tokens) |
| `input_tokens` | 8 |
| `cache_read_input_tokens` | 135.117 |
| `cache_creation_input_tokens` | 9.764 |
| `output_tokens` | 1.716 |
| **tokens_in (Claude-conventie)** | **144.889** |
| **kosten** | **$0,209215** |
| MCP-tools | geen |
| ingebouwde tools | **41** |

## Verwachte toolnamen na de wijziging

Exact zes, en niets anders:

```
Read, Edit, Write, Glob, Grep, Bash
```

Het subproces rapporteert ze zelf; we leiden ze niet af.

## De procedure

1. **Wegwerp-repo**, identiek aan de vorige meting — een verse `git init` in de
   scratchpad met één bestand. Nooit `padelmq-pro`, zodat een mislukte meting
   niets kan raken.

2. **Minimale prompt**, dezelfde vorm als de vorige (286 tekens): een triviale
   wijziging, plus de opdracht om in `summary` te zetten:
   `AANTAL_TOOLS=<n> | MCP=<ja/nee> | NAMEN=<komma-gescheiden>`

3. **Exact één aanroep** via `ClaudeExecutor`, niet via `run`. Geen reviewer, dus
   geen tweede betaalde aanroep.

4. **Vastleggen in de audittrail** vóór de aanroep: een `budget-uitzondering`
   met reden, omvang en de dagkost op dat moment. Daarna de aanroep boeken als
   fase `meting`, ook al liep hij buiten de runner om — echt geld hoort in het
   grootboek.

5. **Meten en vergelijken**: `input_tokens`, `cache_read`, `cache_creation`,
   `output_tokens`, het genormaliseerde totaal, `total_cost_usd`, het aantal
   tools dat het subproces meldt, en de reductie ten opzichte van 144.889
   tokens en $0,209215.

## Afbreken

Wordt de aanroep onverwacht groot of duur, dan stopt het daar. Geen tweede
poging en geen extra diagnose-aanroep: dat was precies de fout die $1,91 kostte.

## Wat deze meting niet kan aantonen

De 144.889 tokens bevatten naast de toolbeschrijvingen ook het systeemprompt van
de CLI, eventuele `CLAUDE.md` uit de repository, en de lijst met beschikbare
skills. `--tools` raakt alleen het eerste. Blijft de belasting hoog, dan ligt de
rest daar, en is `--safe-mode` de volgende kandidaat — met de kanttekening dat
die ook `CLAUDE.md` uitschakelt, en dat is projectkennis die de uitvoerder juist
nodig kan hebben. Dat is een afweging tussen kosten en kwaliteit, geen
technisch detail.
