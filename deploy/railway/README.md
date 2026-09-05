# De orkestrator op Railway

Naast de bestaande Product Engine, als **aparte service met een eigen volume**.
De Product Engine en haar volume op `/app/data` worden niet aangeraakt.

## Waarom een aparte service

Ze delen niets wat ze zouden moeten delen. De Product Engine is een webapp met
een SQLite-database van producten; de orkestrator is een achtergrondlus met een
eigen database van taken, kennis en kosten. In één service zetten zou betekenen
dat een herstart van de één de ander meesleept, en dat een fout in de één de
data van de ander kan raken.

Aparte service, apart volume, aparte variabelen. Dat is ook wat projectisolatie
op codeniveau al afdwingt; het zou vreemd zijn dat op infrastructuurniveau weer
weg te gooien.

## Wat er in de container zit

| | waarom |
|---|---|
| Python 3 | de orkestrator zelf |
| Node 22 + npm | de **harde checks van de projecten**; zonder npm kan `npm run test` niet draaien en dat is precies het defect dat eerder geld kostte |
| `@anthropic-ai/claude-code` | de uitvoerder |
| `openai` | de beoordelaar |
| git | branches, worktrees, commits, push |

## Paden

```
/data/orchestrator     SQLite, kennisbasis, audittrail, kosten, worktrees
/data/repos            de klonen van de aangesloten projecten
/app/data              NIET AANRAKEN — dat is de Product Engine
```

Het volume van deze service komt op **`/data`**.

## Variabelen

Alles via Railway-variabelen. Nooit in git, nooit in een logregel, nooit in een
remote-URL.

**Geheim:**

```
ANTHROPIC_API_KEY     de uitvoerder (Claude Code kan op een server alleen hiermee)
OPENAI_API_KEY        de beoordelaar
ORCH_GITHUB_TOKEN     issues, pull requests en pushen
```

**Gewoon:**

```
ORCH_DATA_DIR=/data/orchestrator
ORCH_REPOS=/data/repos
ORCH_CURRENCY=USD
ORCH_REVIEWER_MODEL=gpt-5.6-terra
ORCH_REVIEWER_PRICE_IN=2.00
ORCH_REVIEWER_PRICE_OUT=12.00
ORCH_REVIEWER_PRICE_CACHED_IN=0.20
ORCH_BUDGET_GLOBAL_DAILY_EUR=5
ORCH_BUDGET_PROJECT_DAILY_EUR=5
ORCH_BUDGET_TASK_EUR=2
ORCH_BUDGET_RUN_EUR=1
ORCH_INTERVAL=120
```

De $5 per dag blijft staan als noodrem, niet als streefbedrag.

## Wat er bij het starten gebeurt

`start.sh` doet drie dingen vóór de lus begint, en stopt als er één faalt:

1. **git-authenticatie** uit `ORCH_GITHUB_TOKEN`, in een bestand met rechten
   600. Niet in de remote-URL: die belandt in `.git/config` en in logs.
2. **`project bootstrap`** — de klonen terughalen. Op een container is alles
   buiten het volume weg na een herstart.
3. **`doctor`** — toetst of authenticatie werkelijk wérkt, niet of er een
   variabele bestaat. Faalt hij, dan stopt de container en staat de reden in de
   log. Railway herstart en probeert opnieuw.

Een dienst die opkomt en dan stilletjes niets doet is erger dan een die weigert
te starten: het eerste merk je pas als je iets verwacht.

## Bewijzen dat het draait

Railway-shell, of lokaal tegen dezelfde database:

```
orchestrator status      # exit 0 = levensteken vers genoeg
orchestrator digest      # dagrapport
orchestrator summary <project> <taak>
```

De lus schrijft na élke ronde een levensteken, ook een stille.

## Terugrollen

Railway houdt elke deploy bij. Terugrollen is in de service-geschiedenis de
vorige deploy kiezen en op **Redeploy** klikken. Het volume blijft daarbij
staan: taken, kennis, audittrail en kosten gaan niet mee terug.

Dat is de reden dat de data op een volume staan en niet in het image.

## Wat 24/7 draaien NIET verandert

Geen automatische merge naar `main`, geen deploy, geen live Shopify-, prijs- of
voorraadactie, budgetremmen vóór elke betaalde aanroep, BLOCK bij ontbrekende
businessregels, en strikte scheiding tussen projecten.

Die grenzen zitten in de code en niet in de manier van starten. Een lus die
vaker draait mag niet méér mogen.
