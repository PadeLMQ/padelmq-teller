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

Verder: `questions`, `question-add`, `answer`, `poll-answers`, `digest`, `costs`, `pause`.

### Voordat je aankoppelt

```bash
orchestrator inspect ~/code/mijnapp      # welke verificatie is er echt?
orchestrator verify-reviewer --offline   # klopt de reviewer-aanroep met de SDK?
orchestrator secret-scan .               # staat er niets geheims in git?
```

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
| Datamap mag nooit in een git-repo liggen | `config.py`, geweigerd door `run` en `doctor` |
| **Verboden commando's kunnen niet als verificatie draaien** | `verify.assert_safe_checks` — de poort zit in de uitvoerder, niet in de configuratie |
| Geheimenscan met vindbaar ontsnappingsluik (`nep-geheim`) | `secret_scan.py`, `deploy/pre-commit` |
| Reviewer-aanroep valideren zonder stille terugval | `validate_reviewer.py` |
| Eén antwoordmachine voor alle kanalen (GitHub, opdrachtregel, spraak) | `answer_session.py` |
| Ondubbelzinnigheidspoort: nooit aanvullen, nooit raden | `answer_session.py` |
| `bevestigd` ontstaat op één plek | `answers.record_human_decision` |
| Volledig audit spoor per gesprek | `db.py` (`answer_turns`) |
| Verificatie vaststellen op wat er werkelijk draait | `inspect.py` |

## Tests

```bash
python3 -m unittest discover -s tests -t .
```

129 tests, geen externe afhankelijkheden nodig behalve PyYAML en `git`. De lus
wordt end-to-end getest met een echte git-repository en echte
verificatiecommando's; alleen de modellen zijn nepobjecten.

## Wat bewust nog niet af is

| Onderdeel | Status |
|---|---|
| `import chatgpt` | Weigert bewust te draaien. Het ontwerp legt vast dat we de structuur van de export op een echt bestand verifiëren voordat we de parser schrijven. |
| Reviewer-aanroep | `orchestrator verify-reviewer --offline` controleert de SDK-handtekening zonder netwerk of kosten. De online trap (één minimale echte aanroep) moet nog gedraaid worden vóór de eerste productierun; bij afwijking stopt hij in plaats van terug te vallen. |
| Parallelle projecten | V1 draait sequentieel; dat is doorvoer, geen functionaliteit. |
| Auto-merge | Alleen als schakelaar in `project.yaml`, standaard uit, niet geïmplementeerd. |

## Spraak (P2) — de naad is er, het transport nog niet

`voice/` levert precies twee handelingen voor een transport: `next_question()` en
`submit(session_id, transcript, confidence)`. Alles wat bepaalt of een antwoord
voldoende is, zit in `answer_session.py` en is gedeeld met de andere kanalen — er
hoeft dus niets herbouwd te worden als spraak erbij komt.

Nog te bouwen: het HTTP-eindpunt op de VPS (`GET /voice/next`, `POST /voice/answer`)
met tokenauthenticatie, en de keuze voor de transcriptiedienst. Zie §16d van het
ontwerp voor de twee transportroutes.

## De code naar een eigen private repository

```bash
./deploy/verhuis-naar-eigen-repo.sh                    # proef: scant en splitst, pusht niets
./deploy/verhuis-naar-eigen-repo.sh --push <git-url>   # pas na jouw controle
```

De proef weigert te splitsen als er iets geheims in de map staat, en controleert
dat de afgesplitste branch geen bestanden van buiten `orchestrator/` bevat.

## Naar de VPS

`deploy/` bevat systemd-units. De code hoort in `/opt/orchestrator`, de
gegevens in `ORCH_DATA_DIR` (standaard buiten de repository — daar staat je
kennisbasis met businessregels in).

Back-up: maak van `$ORCH_DATA_DIR/projects/*/kennis/` een git-repo die naar een
**privé** GitHub-repo pusht. Dat is het waardevolste dat het systeem opbouwt.
