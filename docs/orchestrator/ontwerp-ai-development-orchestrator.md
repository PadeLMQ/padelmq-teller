# Universele AI Development Orchestrator — haalbaarheidsanalyse & technisch ontwerp

**Status:** ontwerp ter beoordeling. Nog niets gebouwd.
**Datum:** 5 september 2026
**Opdrachtgever:** Mathias (PadeLMQ)
**Scope:** één orkestrator die meerdere ontwikkelprojecten aanstuurt; doel is snellere
oplevering van díe projecten, niet de orkestrator zelf.

---

## 0. Samenvatting en oordeel

**Kan het? Grotendeels ja — maar niet zoals je het beschrijft.**

| Onderdeel van je voorstel | Haalbaar? | Toelichting |
|---|---|---|
| Claude automatisch laten werken, zonder chatvenster | **Ja, officieel** | Claude Agent SDK / `claude -p`. Sessies per project, hervatbaar, hooks, rechtenmodel. |
| Output automatisch naar analyse sturen | **Ja** | Gewoon een functieaanroep in de lus. |
| "GPT" die de volgende prompt maakt | **Ja via de OpenAI API** | Maar **niet** via je ChatGPT-chats. Zie §2.2. |
| Je bestaande ChatGPT-gesprekken hergebruiken | **Nee** | Er is geen officiële API voor de ChatGPT-app. Alleen een handmatige export als eenmalige startvulling. |
| Onbeperkt projecten, elk eigen context/geschiedenis | **Ja** | Per project een map, een SQLite-record en een eigen Claude-sessie-id. |
| Doorlopen tot menselijke input echt nodig is | **Ja, met grenzen** | Werkt alleen betrouwbaar met harde stopcondities: budget, iteratielimiet, geen-vooruitgang-detectie. |
| Open vragen parkeren en gebundeld voorleggen | **Ja** | Dit is het waardevolste stuk van je voorstel. Zie §4.5. |
| "Vrijwel geen handmatig kopiëren en plakken meer" | **Ja** | Realistisch: het plakken verdwijnt volledig; jouw beslismomenten niet. |

**Mijn belangrijkste tegenspraak:** je beschrijft een lus waarin het oordeel van een tweede
taalmodel het stuursignaal is. Dat is het zwakste signaal dat beschikbaar is. In
softwareontwikkeling bestaat er hard bewijs — tests, typecheck, linter, build, een
draaiende app — en dát hoort de motor van de lus te zijn. Een tweede model heeft wél
waarde (andere blinde vlekken), maar als **poortwachter**, niet als promptschrijver.
Uitgewerkt in §3. Als je het na het lezen anders ziet, bouw ik jouw variant — maar dan
met open ogen.

**Tweede tegenspraak:** de eerste versie hoeft GPT helemaal niet te bevatten. Ongeveer
80% van de winst zit in "Claude blijft doorwerken tot de tests groen zijn en vraagt me
niets tussendoor". Dat is fase 1 en kost een fractie van het geheel. Bouw dat eerst,
meet het, en voeg de tweede leverancier pas toe als de meting het rechtvaardigt.

---

## 1. Waar de tijd nu écht heen gaat

Je huidige lus: Claude antwoordt → jij plakt in GPT → GPT analyseert → jij plakt terug.
De kosten daarvan zijn niet alleen de seconden van het plakken.

| Verliespost | Wat het je kost | Wordt opgelost door |
|---|---|---|
| Kopiëren/plakken | seconden per stap, tientallen keren per dag | de orkestrator (volledig weg) |
| **Jij bent de planner** | de lus staat stil zodra jij iets anders doet | de orkestrator werkt door terwijl je slaapt — **grootste winst** |
| Contextwissels | 20 onderbrekingen per dag, elk ~10-15 min herstel | vraagbundeling (§4.5) |
| Verkeerd werk dat pas laat opvalt | hele iteraties weggegooid | harde verificatiepoort vóór de reviewstap (§3) |
| Wachten op een lange Claude-run | dode tijd | parallelle projecten (§4.6) |

De echte winst is dus **doorvoer**, niet snelheid per stap. Eén project gaat niet
dramatisch sneller; vier projecten tegelijk vorderen wel terwijl jij er één bekijkt.

Dit is meetbaar en de orkestrator meet het zelf mee vanaf dag één — zie §9. Ik geef
bewust geen "3× sneller"-belofte; dat zou giswerk zijn.

---

## 2. Haalbaarheid per koppeling

### 2.1 Claude-kant — volledig officieel ondersteund

De Claude Agent SDK is Claude Code als bibliotheek, in Python en TypeScript. Alles wat de
lus nodig heeft, zit erin:

| Nodig | Beschikbaar |
|---|---|
| Programmatisch een opdracht draaien | `query(prompt, options)` (Python/TS), of `claude -p` als subproces |
| Machineleesbare uitvoer | `--output-format json` / `stream-json`; met `--json-schema` zelfs schema-gedwongen |
| Geschiedenis per project/taak | Sessies op schijf; `resume=<session_id>`, `fork_session` voor varianten |
| Rechten zonder mens aan de knoppen | `--permission-mode` (`auto`, `dontAsk`, `acceptEdits`) + `--permission-prompts none` |
| Ingrijpen op vaste momenten | Hooks (o.a. `SessionStart`, `PermissionRequest`, `SessionEnd`) |
| Kostenbewaking per run | `total_cost_usd` in het resultaatbericht; `error_max_budget_usd` als stopreden |
| Reproduceerbaarheid in scripts | `--bare` slaat hooks/plugins/MCP van de host over |

Twee praktische aandachtspunten:

1. **Sessiebestanden zijn machinegebonden** (`~/.claude/projects/<map>/<id>.jsonl`).
   Draait de orkestrator altijd op dezelfde machine, dan is dat geen probleem. Wil je later
   naar een VPS of CI, dan is er een `SessionStore`-adapter, of — robuuster — je vertrouwt
   niet op sessie-hervatting maar bouwt de context elke run opnieuw op uit je eigen
   opslag. Mijn advies: **hervat sessies waar het kan, maar maak de orkestrator er niet
   afhankelijk van.** De taakstatus in SQLite is de waarheid, de Claude-sessie is
   versnelling.
2. **Authenticatie/kosten.** `claude -p` gebruikt je bestaande login; `--bare` (de
   aanbevolen modus voor scripts) leest géén OAuth-credentials en vereist een
   `ANTHROPIC_API_KEY` met verbruiksfacturering. Anthropic staat derden bovendien niet toe
   claude.ai-login of -limieten aan hun producten aan te bieden. Voor eigen, persoonlijk
   gebruik op je eigen machine is `-p` zonder `--bare` technisch mogelijk, maar dit is een
   **beslissing met kosten- en voorwaardengevolgen** die jij moet nemen, niet ik. Zie
   beslissing B1 in §8.

### 2.2 ChatGPT-kant — hier zit het gat in je voorstel

**Wat niet kan:** er bestaat geen officiële API om berichten in je ChatGPT-chats te
plaatsen of eruit te lezen. De gebruiksvoorwaarden van OpenAI verbieden geautomatiseerde
of programmatische toegang tot de dienst buiten de API om; browserautomatisering van
chatgpt.com valt daaronder. Los van de voorwaarden is het ook technisch fragiel
(loginmuren, botdetectie, UI-wijzigingen) — precies het soort koppeling dat op een
donderdagavond stilvalt.

**Wat wel kan:** de **OpenAI API** (Responses API). Dat is de gesanctioneerde route en
functioneel beter voor dit doel:

- `previous_response_id`-ketening of de Conversations-API geeft server-side
  gespreksgeheugen per project — het equivalent van "een aparte GPT-chat per project".
- Structured outputs dwingen af dat de reviewer JSON teruggeeft in *jouw* schema, in
  plaats van proza dat je moet interpreteren.
- Responses worden standaard 30 dagen bewaard (`store`); je houdt sowieso je eigen kopie
  in de database, dus dat is alleen gemak.

**De consequenties, eerlijk benoemd:**

| Gevolg | Betekenis |
|---|---|
| Je huidige ChatGPT-gesprekken gaan niet mee | Alleen via handmatige data-export als eenmalige startvulling per project. |
| Andere factuur | De API is verbruiksgebaseerd en staat los van je ChatGPT-abonnement. Je betaalt tweemaal zolang je beide gebruikt. |
| Ander gedrag | Het API-model is niet identiek aan wat de ChatGPT-app doet (die heeft eigen systeeminstructies en tools). Verwacht een andere toon; het oordeel is vergelijkbaar. |
| Je code gaat naar een tweede leverancier | Zie §7, risico R4. Voor PadeLMQ relevant: er zitten Shopify-credentials in de omgeving van je projecten. |

### 2.3 Verdict

Beide kanten zijn koppelbaar via officiële, ondersteunde interfaces. Er is **geen enkele
reden om te scrapen of te browserautomatiseren**, en ik zal dat ook niet voorstellen.
De prijs is dat je "GPT-chat per project" migreert naar "reviewer-API met eigen geheugen
per project" — dezelfde rol, andere plek.

---

## 3. Tegenspraak: verplaats het gezag van het tweede model naar het bewijs

Je voorstel: Claude produceert → GPT beoordeelt en schrijft de volgende prompt → Claude
voert uit. In die lus is de **mening van een taalmodel** het enige stuursignaal.

Waarom dat te zwak is als motor:

1. **Twee modellen kunnen samen zelfverzekerd fout zijn.** Als Claude een test breekt en
   GPT ziet alleen de tekst van het antwoord, wordt de fout doorgegeven en versterkt.
2. **Het is duur per eenheid informatie.** Een testrun kost seconden en centen en geeft
   een binair, onbetwistbaar antwoord. Een reviewronde kost tienduizenden tokens en geeft
   een mening.
3. **Het maakt eindeloos ronddraaien mogelijk.** Zonder objectief eindpunt kan de lus
   oneindig "verbeteren" zonder ooit klaar te zijn. Dit is de belangrijkste kostenrisico.
4. **Claude Code doet dit intern al.** De agentlus draait zelf al tests en herstelt zelf.
   Een externe promptschrijver dupliceert dat gedeeltelijk.

**Wat ik in plaats daarvan voorstel — dezelfde automatisering, ander gezag:**

```
                    ┌──────────────────────────────────────────────┐
                    │  Taak met acceptatiecriteria (uit backlog)   │
                    └───────────────────┬──────────────────────────┘
                                        ▼
                            ┌───────────────────────┐
                            │  UITVOEREN — Claude   │  Agent SDK, sessie per taak
                            └───────────┬───────────┘
                                        ▼
                     ┌─────────────────────────────────────┐
                     │  VERIFIËREN — hard bewijs           │  tests · typecheck · lint
                     │  (deterministisch, geen model)      │  · build · smoke-run
                     └──────────┬──────────────┬───────────┘
                          rood  │              │ groen
                                ▼              ▼
                   terug naar Claude   ┌────────────────────────┐
                   met de echte fout   │ BEOORDELEN — reviewer  │ GPT, JSON-verdict
                   (geen model nodig)  │ (2e leverancier)       │
                                       └───────────┬────────────┘
                                                   ▼
                              pass ──► KLAAR      revise ──► terug naar Claude
                                                  escalate ──► vraag parkeren
```

De reviewer blijft dus in het ontwerp — jouw intuïtie dat een tweede model waarde
toevoegt, klopt: het vindt dingen die tests niet vinden (verkeerde aanpak, gemiste eis,
onnodige complexiteit, veiligheidsgat). Maar hij komt **na** het harde bewijs en hij
levert een **gestructureerd verdict**, geen vrije prompt:

```json
{
  "verdict": "pass | revise | escalate",
  "confidence": 0.0,
  "findings": [{"severity": "blocker|major|minor", "file": "", "issue": "", "fix": ""}],
  "next_instruction": "concrete opdracht voor Claude, alleen bij revise",
  "open_questions": [{"question": "", "why_blocking": "", "options": [],
                      "default_assumption": "", "blocking": true}],
  "acceptance_met": ["criterium-1"], "acceptance_missing": ["criterium-3"]
}
```

Dit levert drie dingen op die vrije prompts niet leveren: de lus kan er programmatisch
op beslissen, je kunt de reviewer achteraf beoordelen op zijn eigen cijfers, en
"escalate" wordt een echte, afdwingbare uitkomst in plaats van een zin in een alinea.

**Concreet gevolg voor jou:** het verschil tussen jouw variant en de mijne is niet minder
automatisering. Het is dat de mijne kán stoppen met een objectief "klaar", en de jouwe
niet.

---

## 4. Technisch ontwerp

### 4.1 Overzicht

Eén Python-daemon, één repository, één SQLite-bestand. Geen microservices, geen
berichtenbus, geen Kubernetes. Op jouw schaal (één gebruiker, handvol projecten) is
elke extra laag pure vertraging.

```
┌────────────────────────────────────────────────────────────────────────┐
│ ORCHESTRATOR (Python-daemon)                                           │
│                                                                        │
│  Scheduler ──► Runner (toestandsmachine per taak)                      │
│      │              │                                                  │
│      │              ├─► ClaudeAdapter    → Claude Agent SDK            │
│      │              ├─► VerifyAdapter    → shell: pytest/tsc/lint/build│
│      │              ├─► ReviewAdapter    → OpenAI Responses API        │
│      │              └─► GitAdapter       → worktree, branch, commit, PR│
│      │                                                                 │
│  Budgetbewaker · Vragenparkeerplaats · Gebeurtenislogboek              │
└───────────────┬─────────────────────────────┬──────────────────────────┘
                │                             │
        ┌───────▼────────┐            ┌───────▼────────┐
        │ SQLite         │            │ Mens-interface │
        │ projecten      │            │ · dagbundel    │
        │ taken · runs   │            │ · dashboard    │
        │ vragen · logs  │            │ · notificatie  │
        └────────────────┘            └────────────────┘
```

### 4.2 Componenten

| Component | Verantwoordelijkheid | Techniek |
|---|---|---|
| **Projectregister** | Per project: repo, branch, verificatiecommando's, budget, autonomieniveau, datapolicy | `projects/<slug>/project.yaml` |
| **Backlog/taakwinkel** | Taken met acceptatiecriteria, status, afhankelijkheden | SQLite |
| **Scheduler** | Kiest de volgende taak over álle projecten; respecteert gelijktijdigheidslimiet en budget | Python, prioriteit + eerlijkheid per project |
| **Runner** | De toestandsmachine van §4.3 voor één taak | Python |
| **ClaudeAdapter** | Start/hervat een Claude-sessie, levert gestructureerd resultaat | `claude_agent_sdk` (Python) |
| **VerifyAdapter** | Draait de projectcommando's, vangt uitvoer, classificeert falen | subprocess |
| **ReviewAdapter** | Stuurt diff + testuitslag + criteria naar de reviewer, ontvangt JSON | `openai` (Responses API) |
| **GitAdapter** | Worktree per run, branch `orch/<taak-id>`, commit, optioneel PR | `git`, GitHub MCP/API |
| **Budgetbewaker** | Harde kap per run, per taak, per project, per dag | SQLite-teller vóór elke aanroep |
| **Vragenparkeerplaats** | Verzamelt, ontdubbelt en bundelt open vragen | SQLite + bundelgenerator |
| **Interface** | Dashboard + dagbundel + notificatie | zie §4.7 |

### 4.3 De toestandsmachine

```
QUEUED → PLANNING → IMPLEMENTING → VERIFYING ─┬─(rood, poging < N)→ IMPLEMENTING
                                              ├─(rood, poging = N)→ BLOCKED
                                              └─(groen)───────────→ REVIEWING
REVIEWING ─┬─(pass)────→ COMMITTING → DONE
           ├─(revise)──→ IMPLEMENTING   (max M reviewrondes)
           └─(escalate)→ BLOCKED
BLOCKED → (antwoord van mens) → QUEUED
Elke toestand kan → FAILED (budget op, time-out, herhaalde fout)
```

**Stopcondities — niet optioneel.** Zonder deze wordt de eerste onbewaakte nacht duur:

| Conditie | Voorstel voor de standaardwaarde |
|---|---|
| Iteraties implementeren↔verifiëren | max 5 |
| Reviewrondes | max 3 |
| Budget per taak | in te stellen, bv. €2 |
| Budget per project per dag | in te stellen, bv. €10 |
| Wandkloktijd per run | 30 min |
| **Geen-vooruitgang-detector** | tweemaal dezelfde falende testhandtekening óf een identieke diff → direct `BLOCKED`, niet nog eens proberen |

De geen-vooruitgang-detector is het belangrijkste onderdeel van deze tabel. Hij vangt
precies het scenario dat automatisering duur maakt: een model dat er zeker van is dat het
deze keer wel lukt.

### 4.4 Datamodel (kern)

```sql
projects(id, slug, name, repo_path, default_branch, verify_cmds_json,
         autonomy_level, data_policy, budget_daily_eur, active)
tasks(id, project_id, title, spec_md, acceptance_criteria_json, status,
      priority, depends_on_task_id, claude_session_id, reviewer_response_id,
      cost_eur, created_at, updated_at)
runs(id, task_id, phase, started_at, ended_at, outcome, cost_eur,
     tokens_in, tokens_out, artifact_path)
questions(id, project_id, task_id, question, why_blocking, options_json,
          default_assumption, blocking, status, answer, answered_at)
assumptions(id, task_id, question_id, assumption, made_at, revisit_needed)
events(id, project_id, task_id, ts, kind, payload_json)
```

De tabel `assumptions` is bewust apart: als je later een geparkeerde vraag anders
beantwoordt dan de aanname, moet dat zichtbaar worden — zie §4.5.

### 4.5 Vragen parkeren en gebundeld voorleggen

Dit is het deel van je voorstel dat de meeste tijd wint, en het verdient de meeste zorg.

**Hoe een vraag ontstaat.** Zowel Claude als de reviewer krijgen de instructie om
onzekerheden niet weg te gissen maar te melden in een vast formaat: vraag, waarom het
blokkeert, mogelijke opties, de aanname die ze zouden maken, en of het blokkerend is.

**Classificatie.**

| Soort | Voorbeeld | Wat de orkestrator doet |
|---|---|---|
| **Blokkerend, zakelijk** | "Moet de teller btw in- of exclusief tonen?" | Taak → `BLOCKED`, direct notificatie als het hele project stilligt, anders in de bundel. Werk gaat door aan andere taken. |
| **Niet-blokkerend** | "Naam van de knop: 'Opslaan' of 'Bewaren'?" | Aanname vastleggen, doorwerken, in de bundel zetten. |
| **Technisch, zelf te beantwoorden** | "Welke Python-versie draait dit?" | Geen vraag: Claude mag het gewoon opzoeken in de repo. |

Het onderscheid tussen de eerste twee is de sleutel. Een verkeerde classificatie kost óf
je aandacht (te veel blokkeren) óf een dag herwerk (te weinig). Praktische regel:
**blokkerend = het antwoord kan het werk dat je nu zou doen weggooien.** Anders parkeren.

**Terugkoppelen van antwoorden.** Als je een geparkeerde vraag beantwoordt en het
antwoord wijkt af van de gemaakte aanname, opent de orkestrator automatisch een
correctietaak met verwijzing naar de commits die op de aanname gebaseerd waren. Dit is
niet optioneel: zonder dit ontstaat er stilzwijgend werk gebouwd op verkeerde aannames.

**De bundel.** Eén keer per dag (en op verzoek) één overzicht over álle projecten:
per vraag de context, de opties, de voorgestelde standaardkeuze, en wat er geblokkeerd is.
Beantwoorden in één sessie. Antwoorden gaan terug de taakcontext in en de taken keren
terug naar `QUEUED`.

### 4.6 Meerdere projecten

"Onbeperkt" is technisch triviaal — een rij in een tabel. De echte beperkingen zijn
anders en daar ontwerpen we op:

| Beperking | Aanpak |
|---|---|
| Snelheidslimieten van beide leveranciers | Globale gelijktijdigheidslimiet (start met 2 lopende runs), exponentieel wachten bij 429 |
| Jouw beoordelingscapaciteit | Niet meer dan X taken tegelijk in `BLOCKED`/wachtend op review, anders pauzeert de scheduler nieuwe taken |
| Kosten | Dagbudget per project én globaal |
| Repo-conflicten | Eén git-worktree per run; nooit twee runs tegelijk in dezelfde werkmap |

Context blijft per project gescheiden via de projectmap, de eigen Claude-sessies en een
eigen reviewer-gespreksketen. Er lekt niets tussen projecten omdat er nooit één gedeelde
context bestaat.

### 4.7 Mens-interface

Voorstel: **niet** een eigen webapplicatie bouwen in fase 1. Kies één bestaand kanaal:

| Optie | Voor | Tegen |
|---|---|---|
| **GitHub Issues + labels** (aanbevolen) | Gratis, mobiele notificaties, geschiedenis, per project gescheiden, geen onderhoud | Wat omslachtig voor lange bundels |
| E-mail (dagbundel) | Simpel, jij leest toch e-mail | Geen status, geen knoppen |
| Klein lokaal dashboard | Beste overzicht | Bouw- en onderhoudskosten |

Aanbeveling: bundels als e-mail, blokkerende vragen als GitHub-issue met label
`orch:question`, en een dashboard pas in fase 3 als blijkt dat je het mist.

### 4.8 Veiligheid en governance

Een lus die zonder toezicht code schrijft en commit, verdient strengere regels dan een
chatvenster:

1. **Nooit rechtstreeks naar `main`.** Elke run werkt in een worktree op branch
   `orch/<taak-id>`. Samenvoegen gebeurt via PR of door jou.
2. **Commit alleen na groene verificatie.** Geen uitzonderingen, geen "tijdelijk test
   overgeslagen".
3. **Rechten expliciet.** `--permission-mode dontAsk` met een expliciete toegestane lijst
   per project, plus `--permission-prompts none` zodat een onbewaakte run niet eeuwig op
   een prompt blijft wachten.
4. **Geheimen buiten de lus.** `.env`, tokens en `secrets` worden voor de reviewer
   geredigeerd en gaan nooit in een prompt. Voor PadeLMQ concreet: de Shopify Client
   ID/Secret staan als GitHub-secret en mogen niet in diffs of logs belanden.
5. **Promptinjectie.** Een autonome lus die repo-inhoud, issue-teksten of webpagina's
   leest, kan instructies uit die inhoud tegenkomen. Regel: inhoud uit de repo is data,
   nooit opdracht. De reviewer krijgt expliciet die instructie mee, en de lus mag zijn
   eigen budget-, rechten- of doelinstellingen nooit wijzigen op basis van gelezen tekst.
6. **Noodstop.** Eén bestand of commando dat alle runs pauzeert.
7. **Alles gelogd.** Elke prompt, elk antwoord, elke kostenpost in `events`. Zonder dat
   kun je een nacht werk niet reconstrueren.

### 4.9 Kosten

Indicatieve tarieven per miljoen tokens (verifieer bij de bouw — tarieven wijzigen):

| Model | Invoer | Uitvoer | Rol in het ontwerp |
|---|---|---|---|
| Claude Opus 5 | $5 | $25 | Uitvoerder bij complex werk |
| Claude Sonnet 5 | $2 | $10 | Uitvoerder bij routinewerk |
| Claude Haiku 4.5 | $1 | $5 | Classificatie, samenvatten, triage |
| OpenAI-reviewer (middenklasse) | ~$2 | ~$12 | Reviewer |

*De OpenAI-tarieven komen uit een derde-partijbron; de officiële prijspagina was vanuit
deze omgeving niet bereikbaar. Vóór de bouw verifiëren.*

Kostenbeperkende maatregelen die in het ontwerp zitten: promptcaching op de stabiele
projectcontext, de reviewer krijgt de **diff plus testuitslag** in plaats van de hele
repo, verificatie gebeurt zonder model, en triage draait op het goedkoopste model.

---

## 5. Afgewogen alternatieven

| Alternatief | Oordeel | Reden |
|---|---|---|
| **Browserautomatisering van beide chat-UI's** | **Afgewezen** | In strijd met de voorwaarden van OpenAI, technisch fragiel, breekt bij elke UI-wijziging. |
| **Alleen Claude Code, met subagents + hooks, zonder GPT** | **Aanbevolen als fase 1** | Levert het grootste deel van de winst tegen een fractie van de complexiteit. Eén leverancier, één factuur, geen datadeling. |
| **n8n / Zapier / Make als motor** | **Afgewezen als motor** | Langlopende, stateful agentlussen met git-worktrees en budgetten passen slecht in een knooppuntendiagram. Prima voor de notificaties. |
| **GitHub Actions als runtime (geen daemon)** | **Levensvatbaar alternatief** | Gebeurtenisgestuurd, geen machine die aan moet staan, past bij je bestaande workflow-ervaring. Nadelen: joblimiet van 6 uur, trager opstarten, lastiger interactief bijsturen. Overweeg dit als je geen machine 24/7 wilt laten draaien. |
| **LangGraph / Temporal voor duurzame toestand** | **Nu overbodig** | Op jouw schaal doet SQLite + een expliciete toestandsmachine hetzelfde. Temporal is de opschaalroute als er ooit meerdere gebruikers bijkomen. |
| **Codex CLI (`codex exec`) als tweede uitvoerder** | **Optie voor later** | Officieel niet-interactief te draaien met JSON-uitvoer. Interessanter als tweede *uitvoerder* voor A/B-vergelijking dan als reviewer. |

---

## 6. Faseplan

Elke fase levert op zichzelf werkende waarde. Je kunt na elke fase stoppen.

### Fase 0 — Meten (halve dag, geen code)
Kies één pilotproject. Leg van vijf taken vast: doorlooptijd, aantal keren dat jij moest
ingrijpen, en waarvoor. Zonder deze nulmeting kun je later niet aantonen dat het werkt.

### Fase 1 — De onbewaakte lus, één project, zonder GPT
Backlog + Claude-adapter + verificatie + git-worktree + stopcondities + logboek.
**Wat je wint:** je geeft een taak op en krijgt een groene branch terug, of een duidelijke
melding waarom niet. Geen plakwerk meer binnen één taak.

### Fase 2 — Reviewer en vragenparkeerplaats
OpenAI Responses API met JSON-verdict, vraagclassificatie, dagbundel, aannameregistratie
met correctietaken.
**Wat je wint:** kwaliteitspoort van een tweede model, en je onderbrekingen zakken van
tientallen per dag naar één beslismoment.

### Fase 3 — Meerdere projecten
Scheduler, gelijktijdigheidslimieten, budgetten per project, overzicht over alles heen.
**Wat je wint:** doorvoer. Vier projecten vorderen terwijl jij er één beoordeelt.

### Fase 4 — Verfijning (alleen op basis van meting)
Automatische taakontleding uit een roadmap-document, kostenanalyse per taaksoort,
model-per-taaksoort afstemmen, eventueel dashboard.

**Volgorde-advies:** bouw fase 1 en gebruik hem twee weken echt. De meetgegevens uit die
twee weken bepalen of fase 2 de reviewer waard is — en dat is een beter argument dan wat
jij of ik nu vermoeden.

---

## 7. Risico's

| # | Risico | Kans | Impact | Mitigatie |
|---|---|---|---|---|
| R1 | Kosten lopen weg in een onbewaakte lus | Middel | Hoog | Harde budgetkap op vier niveaus, geen-vooruitgang-detector, dagelijkse kostenrapportage |
| R2 | De lus draait rond zonder vooruitgang | Hoog zonder maatregel | Middel | Verificatie als motor (§3), iteratielimiet, herhaalde-fout-detectie |
| R3 | Slechte code komt ongemerkt in `main` | Laag | Hoog | Nooit direct naar `main`, commit alleen na groene verificatie, PR-poort |
| R4 | Code/diffs naar een tweede leverancier | Zeker | Afhankelijk | Per project instelbare datapolicy; standaard: geen `.env`, geen secrets, alleen diffs. Voor gevoelige projecten: reviewer uit. |
| R5 | Promptinjectie via repo-inhoud of issues | Laag | Hoog | Repo-inhoud is data, nooit opdracht; lus mag eigen instellingen niet wijzigen |
| R6 | Verkeerd geclassificeerde vragen | Middel | Middel | Conservatieve regel (§4.5), correctietaken bij afwijkende antwoorden |
| R7 | Sessiehervatting breekt na een update | Middel | Laag | Taakstatus in SQLite is de waarheid; sessie is optimalisatie, geen afhankelijkheid |
| R8 | Je bouwt de orkestrator in plaats van je projecten | **Hoog** | **Hoog** | Gefaseerd, elke fase apart bruikbaar; harde tijdsbegroting per fase; fase 1 vóór alle uitbreiding |

R8 verdient aandacht. Het doel is snellere oplevering van je projecten. Een orkestrator
die drie weken bouwtijd kost voordat hij iets oplevert, is per definitie een verlies.

---

## 8. Wat ik van jou nodig heb

Gebundeld, zoals het systeem het straks zelf zal doen. Zonder deze antwoorden kan ik
fase 1 wel voorbereiden, maar niet afronden.

| # | Beslissing | Waarom het uitmaakt | Mijn advies |
|---|---|---|---|
| **B1** | API-facturering akkoord, of moet het binnen je abonnementen blijven? | Bepaalt of `--bare` gebruikt kan worden en dus hoe robuust scripts zijn | Aparte API-sleutel met eigen budgetplafond; scheidt de kosten van de orkestrator van je dagelijks gebruik |
| **B2** | Waar draait het? Altijd-aan machine, kleine VPS, of GitHub Actions? | Bepaalt of sessie-hervatting bruikbaar is en of nachtelijk doorwerken kan | Begin lokaal op een machine die aan blijft; GitHub Actions als je dat niet wilt |
| **B3** | Mag code/diff naar OpenAI? Per project instelbaar? | Datagovernance, en het bestaan van de reviewer hangt ervan af | Per project instelbaar, standaard aan behalve voor projecten met klantgegevens |
| **B4** | Autonomieniveau: mag hij committen? Pushen? PR openen? Mergen? | Bepaalt hoeveel je nog handmatig doet | Committen en pushen naar `orch/*` ja, PR openen ja, mergen nooit |
| **B5** | Welk project wordt de pilot? | Fase 1 heeft er precies één nodig | Het project waar je nu de meeste iteraties op doet |
| **B6** | Welke projecten zijn er nog meer? | Ik ken alleen `padelmq-teller` | — |
| **B7** | Startbudget per dag | Nodig voor de budgetbewaker | Begin laag (bv. €5/dag globaal) en verhoog op basis van meting |

---

## 9. Hoe we bewijzen dat het werkt

De orkestrator meet zichzelf vanaf de eerste run. Na twee weken beantwoord je met data,
niet met gevoel:

| Meetpunt | Wat het aantoont |
|---|---|
| Doorlooptijd per taak (aangemaakt → `DONE`) | De kernbelofte |
| Aantal menselijke interventies per taak | Of "vrijwel geen plakwerk" gehaald is |
| Aantal onderbrekingen per dag (blokkerende vragen buiten de bundel) | Of de vraagbundeling werkt |
| Kosten per afgeronde taak | Of het economisch klopt |
| Aandeel taken dat de verificatie haalt zonder reviewronde | **Of de reviewer zijn kosten waard is** (§3) |
| Aandeel `revise`-verdicten dat daadwerkelijk tot een betere diff leidt | Idem |

De laatste twee zijn expliciet bedoeld om mijn eigen aanbeveling te kunnen weerleggen.
Als blijkt dat de reviewer in 40% van de gevallen een echte fout vangt die de tests
missen, dan had jij gelijk en promoveren we hem.

---

## 10. Bronnen

- Claude Agent SDK — overzicht: https://code.claude.com/docs/en/agent-sdk/overview
- Claude Agent SDK — sessies, resume en fork: https://code.claude.com/docs/en/agent-sdk/sessions
- Claude Code programmatisch draaien (`-p`, uitvoerformaten, rechten): https://code.claude.com/docs/en/headless
- OpenAI — gespreksstatus (`previous_response_id`, Conversations): https://developers.openai.com/api/docs/guides/conversation-state
- OpenAI — gestructureerde uitvoer: https://developers.openai.com/api/docs/guides/structured-outputs
- OpenAI — gebruiksvoorwaarden (geautomatiseerde toegang): https://openai.com/policies/row-terms-of-use/
- OpenAI Agents SDK (Python): https://github.com/openai/openai-agents-python
- OpenAI Codex CLI (`codex exec`): https://en.wikipedia.org/wiki/OpenAI_Codex_(AI_agent)
- Prijsindicatie OpenAI (derde partij, te verifiëren): https://www.morphllm.com/openai-api-pricing

---

*Volgende stap: beantwoord B1 t/m B7 uit §8, of geef aan dat je fase 1 anders wilt
insteken. Ik bouw pas na jouw akkoord.*
