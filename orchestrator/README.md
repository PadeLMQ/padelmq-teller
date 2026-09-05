# AI Development Orchestrator — V1

Orkestreert Claude als uitvoerder en een reviewer als kennisdrager over een
onbeperkt aantal ontwikkelprojecten. Ontwerp:
[`docs/orchestrator/ontwerp-ai-development-orchestrator.md`](../docs/orchestrator/ontwerp-ai-development-orchestrator.md).

De grondregel is **nooit gokken**. Elke vraag krijgt een antwoord met een
controleerbare, bevestigde bron (AUTO), wordt geparkeerd (PARK), of stopt de
taak en meldt het (BLOCK).

## De lus

```
0 baseline      projectchecks vóór er iets wijzigt
1 beantwoorden  reviewer beantwoordt openstaande vragen uit de kennisbasis
                → AUTO / PARK / BLOCK
2 uitvoeren     Claude, met de beantwoorde vragen in de prompt
3 verifiëren    tests · typecheck · lint · build — deterministisch, geen model
                rood → terug naar 2 met de echte fout
4 beoordelen    alleen op groen; pass → commit op orch/<taak-id> → PR
```

Nooit rechtstreeks naar `main`. Nooit automatisch mergen. Commit alleen na
groene verificatie.

## Snel starten

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -e .
cp .env.example .env      # invullen; chmod 600 .env

orchestrator doctor
orchestrator project add mijnapp --repo ~/code/mijnapp \
    --github-repo eigenaar/mijnapp \
    --check tests="pytest -q" --check types="mypy ."
orchestrator task add mijnapp "Voeg endpoint X toe" \
    --spec "…" --acceptance "GET /x geeft 200" --acceptance "test dekt de foutpad"
orchestrator run mijnapp
```

Verder: `questions`, `answer`, `poll-answers`, `digest`, `costs`, `pause`.

## Wat de veiligheid draagt

| Mechanisme | Waar |
|---|---|
| Alleen bevestigde bronnen tellen voor AUTO | `triage.py`, `knowledge.py` |
| Categorieën die nooit automatisch mogen (geld, btw, juridisch, …) | `triage.py` |
| Verzonnen-waarde-detector op de diff | `guards.py` |
| Aanname zonder bron houdt de commit tegen | `adapters/claude.py`, `runner.py` |
| Geen-vooruitgang-detector | `guards.py`, `db.py` |
| Kostenrem vóór de aanroep, vier niveaus | `cost.py` |
| Geheimen worden onvoorwaardelijk geredigeerd | `redact.py` |
| Beoordelaar kan een testuitslag niet overrulen | `adapters/reviewer.py` |
| Projectisolatie via verplichte `project_id` | `db.py` |
| Noodstop | `config.py`, `orchestrator pause` |

## Tests

```bash
python3 -m unittest discover -s tests -t .
```

72 tests, geen externe afhankelijkheden nodig behalve PyYAML en `git`. De lus
wordt end-to-end getest met een echte git-repository en echte
verificatiecommando's; alleen de modellen zijn nepobjecten.

## Wat bewust nog niet af is

| Onderdeel | Status |
|---|---|
| `import chatgpt` | Weigert bewust te draaien. Het ontwerp legt vast dat we de structuur van de export op een echt bestand verifiëren voordat we de parser schrijven. |
| Reviewer-aanroep | De code staat er; de exacte parametervorm van de Responses API moet met één echte aanroep bevestigd worden vóór de eerste productierun. |
| PR automatisch openen | `report.pr_body()` bouwt de omschrijving en `notify/github.py` heeft `create_pull_request`; de runner laat de branch nu klaarstaan. Aansluiten is een kleine stap. |
| Parallelle projecten | V1 draait sequentieel; dat is doorvoer, geen functionaliteit. |
| Auto-merge | Alleen als schakelaar in `project.yaml`, standaard uit, niet geïmplementeerd. |

## Naar de VPS

`deploy/` bevat systemd-units. De code hoort in `/opt/orchestrator`, de
gegevens in `ORCH_DATA_DIR` (standaard buiten de repository — daar staat je
kennisbasis met businessregels in).

Back-up: maak van `$ORCH_DATA_DIR/projects/*/kennis/` een git-repo die naar een
**privé** GitHub-repo pusht. Dat is het waardevolste dat het systeem opbouwt.
