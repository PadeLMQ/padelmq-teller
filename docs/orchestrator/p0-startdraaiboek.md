# P0 — draaiboek voor de eerste echte lus

Alles wat zonder credentials kon, is gedaan. Dit document is wat er gebeurt zodra
de OpenAI-sleutel er is: de volgorde, de pilottaak, en wat het eindrapport toont.

**Niets in dit draaiboek raakt live bedrijfsdata.** Geen Shopify, geen prijzen,
geen voorraad, geen merge naar `main`.

---

## Deel A — wat jij doet

### A1. De private repository (los van P0, mag parallel)

Ik kan geen repository aanmaken: deze sessie mag alleen schrijven naar repo's die
eraan gekoppeld zijn.

1. Maak op GitHub **`PadeLMQ/padelmq-orchestrator`** aan, **private**, leeg
   (geen README, geen .gitignore — het script pusht een complete geschiedenis).
2. Draai in `padelmq-teller` eerst de proef:

   ```bash
   ./orchestrator/deploy/verhuis-naar-eigen-repo.sh
   ```

   Die scant op geheimen, splitst de geschiedenis van `orchestrator/` af en
   controleert dat er geen bestand van buiten die map in zit. Er wordt **niets**
   gepusht.
3. Ziet de uitvoer er goed uit, dan:

   ```bash
   ./orchestrator/deploy/verhuis-naar-eigen-repo.sh --push \
       git@github.com:PadeLMQ/padelmq-orchestrator.git
   ```
4. In de nieuwe kloon:

   ```bash
   ln -sf ../../deploy/pre-commit .git/hooks/pre-commit
   orchestrator secret-scan .          # moet "Geen geheimen gevonden" zeggen
   ```
5. Controleer op GitHub dat de repository **private** staat.
6. Verwijder `orchestrator/` uit `padelmq-teller` in een **aparte** commit.

### A2. De OpenAI-sleutel, veilig — vijf stappen

**Stap 1 — maak de sleutel aan.**
platform.openai.com → **API keys** → *Create new secret key*. Geef hem een naam
als `padelmq-orchestrator`. Beperk hem tot één project als je meerdere projecten
hebt. Je ziet de waarde **één keer**; kopieer hem meteen naar je wachtwoordbeheerder.

**Stap 2 — zet er een kostenplafond op, vóór je hem gebruikt.**
platform.openai.com → **Settings → Limits**:

| | |
|---|---|
| *Budget limit* (hard) | het bedrag waarbij de API **stopt**. Zet dit laag — bijvoorbeeld €10 voor de eerste maand. |
| *Email threshold* (soft) | waar je een waarschuwing wilt, bijvoorbeeld €5. |

Dit is jouw vangnet bij OpenAI zelf, onafhankelijk van de orkestrator. De
orkestrator heeft zijn eigen rem (§9 van het ontwerp), maar twee onafhankelijke
plafonds is beter dan één.

**Stap 3 — zet de variabelen in de permanente omgeving.**
Niet in een gesprek, niet in git, niet in een tijdelijke sessie.

*Op de VPS* — dat is de productieplek:

```bash
sudo -u orchestrator install -m 600 /dev/null /opt/orchestrator/.env
sudo -u orchestrator nano /opt/orchestrator/.env
```

Invullen:

```
OPENAI_API_KEY=...
ANTHROPIC_API_KEY=...
ORCH_REVIEWER_MODEL=...
ORCH_REVIEWER_PRICE_IN=...
ORCH_REVIEWER_PRICE_OUT=...
ORCH_DATA_DIR=/var/lib/orchestrator
ORCH_GITHUB_TOKEN=...
```

De systemd-units in `deploy/` lezen dit bestand via `EnvironmentFile`. Zo staan de
sleutels op één plek, met rechten `600`, en overleven ze elke herstart.

*Wil je dat een Claude Code-sessie het draaiboek voor je uitvoert*, zet dezelfde
variabelen dan bij de **omgeving** van je remote sessie in plaats van in een
gesprek: https://code.claude.com/docs/en/claude-code-on-the-web

**Stap 4 — installeer het pakket.**

```bash
sudo -u orchestrator /opt/orchestrator/.venv/bin/pip install "openai>=1.0"
```

**Stap 5 — controleer, zonder de sleutel te tonen.**

```bash
orchestrator doctor
```

Toont per geheim alleen `gezet` of `NIET gezet`, met een **vingerafdruk** — de
eerste acht tekens van een sha256. Daarmee kun je nagaan of op twee plekken
dezelfde sleutel staat, zonder dat de waarde ergens in beeld of in een logboek
komt. De volledige waarde wordt nergens getoond, gelogd of naar een model
gestuurd.

Alles groen? Dan door naar Deel B.

---

## Deel B — de volgorde, strikt

Elke stap moet slagen voordat de volgende begint. Bij twijfel stoppen we; er
wordt niet stil teruggevallen op een ander model of een andere API-vorm.

### B1. Omgeving controleren

```bash
orchestrator doctor
```

Moet groen zijn op: datamap buiten git, `claude` en `git` in PATH, prijs bekend
voor het reviewer-model.

### B2. Offline validatie — geen netwerk, geen kosten

```bash
orchestrator verify-reviewer --offline
```

Vergelijkt de parameters die de adapter verstuurt (`model`, `input`,
`previous_response_id`, `text`) met de handtekening van de geïnstalleerde
`openai`-versie.

**Faalt dit, dan stopt het hier.** Ik corrigeer `adapters/reviewer.py` en we
beginnen opnieuw bij B2. Geen andere API-vorm proberen.

### B3. Precies één minimale echte aanroep

```bash
orchestrator verify-reviewer --model "$ORCH_REVIEWER_MODEL"
```

Eén aanroep, met een schema van één booleaans veld en een prompt van drie
woorden, langs **exact hetzelfde codepad** als productie. Gecontroleerd wordt:

- of de API de aanroep aanvaardt;
- of `output_text`, `id` en `usage` aanwezig zijn — de drie velden die de adapter
  uitleest;
- of de gestructureerde uitvoer geldige JSON is die het schema volgt;
- of de tokentelling bruikbaar is, want anders kan de kostenbewaking niet meten.

Verbruik: enkele tientallen tokens. **Bij enige afwijking stopt het en corrigeer
ik eerst.**

### B4. Het pilotproject aankoppelen

```bash
orchestrator project add padelmq-pro \
    --repo ~/code/padelmq-pro \
    --github-repo PadeLMQ/padelmq-pro \
    --check tests="npm run test" \
    --check typecheck="npm run typecheck" \
    --check lint="npm run lint" \
    --check build="npm run build"
```

Verwachte uitvoer: **verificatiesterkte sterk**, maximaal 5 iteraties per taak.

De uitvoerder weigert elk ander commando: `sync`, `daily`, `scan:*`, `import:*`,
`setup:*`, `seed`, `migrate`, `discover:*`, `flag:*`, `publish`, `deploy`, elke
`--live`- of `--push`-vlag, `ENABLE_STOCK_WRITE=true`, rechtstreekse
`myshopify.com`-aanroepen en `curl`/`wget`. Die poort zit in de uitvoerder zelf,
niet in de configuratie.

### B5. De kennisbasis een startzetje geven

De AUTO-route werkt alleen met **bevestigde** bronnen. Voor de eerste run zijn
drie regels genoeg; alles wat jij hier invult, telt als bevestigd omdat jij het
zegt. In `$ORCH_DATA_DIR/projects/padelmq-pro/kennis/`:

- `verboden.md` — de lijst uit B4, plus: nooit zelf een prijs, marge, btw-tarief
  of voorraadaantal bepalen.
- `voorkeuren.md` — bijvoorbeeld: commentaar en tests in het Nederlands, geen
  nieuwe afhankelijkheden zonder overleg, vitest als testrunner.
- `doel.md` — twee zinnen over wat `padelmq-pro` is.

Meer is voor de eerste run niet nodig. Wat ontbreekt, wordt vanzelf een
geparkeerde vraag — en dat is precies wat we willen zien werken.

### B6. De pilottaak

```bash
orchestrator task add padelmq-pro \
  "Voeg toegewijde tests toe voor src/lib/format.ts" \
  --spec "src/lib/format.ts bevat money() en dateShort(): opmaak van bedragen en datums voor het dashboard, 19 regels, geen bedrijfslogica. De module staat op 0% dekking. Voeg tests/format.test.ts toe. Wijzig niets aan de productiecode." \
  --acceptance "tests/format.test.ts bestaat en dekt money() en dateShort()" \
  --acceptance "money(null) geeft een streepje terug en dateShort van een ongeldige datum ook" \
  --acceptance "npm run test slaagt" \
  --acceptance "npm run typecheck slaagt" \
  --acceptance "er is geen enkel bestand buiten tests/ gewijzigd"
```

**Waarom deze taak.** `format.ts` is negentien regels pure opmaak: een bedrag
tonen en een datum tonen. Geen Shopify, geen prijs- of voorraadbeslissing, geen
database. De taak voegt alleen een testbestand toe, dus er verandert geen enkel
gedrag en terugdraaien is één `git branch -D`. Toch is de verificatie echt:
`npm run test` en `npm run typecheck` moeten slagen, en het laatste
acceptatiecriterium is machinaal te controleren in de diff.

Om misverstanden voor te zijn: `money()` *toont* geld, het *beslist* er niets
over. De prijslogica zit in `repricing.ts` en `brain.ts` en die blijft ongemoeid.

### B7. Draaien

```bash
orchestrator run padelmq-pro
```

De lus: baseline → beantwoorden → uitvoeren → verifiëren → beoordelen → commit →
push naar `orch/<taak-id>` → PR. **Nooit een merge naar `main`.**

### B8. Het rapport

```bash
orchestrator report padelmq-pro <taak-id>
orchestrator report padelmq-pro <taak-id> --json > rapport.json
orchestrator costs
```

---

## Deel C — wat het rapport toont

Het rapport bevat exact de twaalf afgesproken punten. Ter illustratie, uit een
volledige testlus met nepmodellen:

| # | Punt | Wat je ziet |
|---|---|---|
| 1 | De taak | titel, specificatie, alle acceptatiecriteria, eindstatus |
| 2 | Wat Claude deed | per poging de samenvatting, gestelde vragen, gemaakte aannames, voorgesteld alternatief |
| 3 | Harde verificatie | per poging elke check met **commando en exitcode**, en of hij slaagde |
| 4 | Context voor de reviewer | per fase: welke kennisitems erin zaten, met hun **status**, hoeveel er bevestigd waren, de omvang in tekens en een **sha256** van de exacte context; plus de omvang van de diff en de voorgelegde vragen |
| 5 | Uitkomst AUTO/PARK/BLOCK | per vraag |
| 6 | Motivatie en bronnen | de motivatie, de **gebruikte bevestigde bronnen** en de aangeboden bronnen die niet telden |
| 7 | Ging Claude zelfstandig verder | ja/nee, aantal uitvoerstappen, of er een menselijk antwoord tussen zat, en de volledige volgorde van gebeurtenissen |
| 8 | Aantal aanroepen | totaal en per rol: uitvoerder, beantwoorder, beoordelaar |
| 9 | Tokens en kosten | per model: aanroepen, tokens in/uit, cache, kosten in euro, plus het totaal |
| 10 | Looptijd | van eerste run tot laatste, met alle deelruns |
| 11 | Oplevering | branch, commit-sha's, PR-URL — en als pushen of de PR mislukte, waarom |
| 12 | Vragen aan jou | elke geparkeerde of blokkerende vraag met opties, voorstel en issuenummer |

Punt 4 is het punt waar ik het meeste aan hecht: het toont niet "de reviewer had
context", maar **welke items met welke status**, plus een hash waarmee je
achteraf kunt vaststellen dat het exact die tekst was.

---

## Deel D — de kostenregels, en waar ze zitten

Doel: **maximale veilige autonomie per betaalde aanroep.** Nooit ten koste van
veiligheid.

| Regel | Waar het zit | Status |
|---|---|---|
| Geen GPT-call na elke kleine wijziging | De lus roept de reviewer **niet** aan bij een rode verificatie; Claude herstelt zelf en itereert. De reviewer komt pas op groen. | Was al zo — nu met een test die het bewaakt |
| Vragen bundelen | Alle openstaande vragen van één stap gaan in **één** aanroep, niet één per vraag | Was al zo — nu met een test |
| De hele batch vastleggen | Bij een PARK of BLOCK worden **alle** vragen uit de batch vastgelegd, niet alleen de eerste. Anders komen al betaalde vragen een ronde later opnieuw langs en kosten ze opnieuw geld | **Nieuw** |
| Minimale relevante context | Alleen **bevestigde** items gaan volledig mee — alleen die kunnen een AUTO dragen. Van de rest gaat de titel mee met de status, zodat de reviewer weet dát ze bestaan en ernaar kan vragen. Weglaten zou de betrouwbaarheid schaden; volledig meesturen is verspilling | **Nieuw** |
| Hergebruik zonder blind te cachen | De sleutel bevat de vraag, de bevestigde kennis, de diff, de acceptatiecriteria, de verificatie-uitslag en het model. Verandert er iets, dan verandert de sleutel en wordt er gewoon opnieuw gevraagd | **Nieuw** |
| De veiligheidspoort blijft live | Wat de cache bewaart is het **ruwe antwoord** van de reviewer, niet de beslissing. De triage draait bij een treffer opnieuw, tegen de actuele kennisbasis | **Nieuw** |
| Caches lekken niet tussen projecten | De cachetabel is per project gescopeerd, net als al het andere | **Nieuw**, met test |
| Kosten per maand | Naast per call, taak, project en dag | **Nieuw** |
| "€X = €A Claude + €B GPT" | In het runrapport, verdeeld op **rol** en niet op modelnaam | **Nieuw** |
| Nooit gokken om een call te sparen | De triage laat een niet-bevestigde bron nooit als AUTO door, wat een besparing ook zou zijn | Was al zo — nu met een test die het expliciet vastlegt |

**Modelkeuze.** De modellen zijn per rol instelbaar (`ORCH_EXECUTOR_MODEL`,
`ORCH_TRIAGE_MODEL`, `ORCH_REVIEWER_MODEL`). Er komt bewust **geen** slimme
routering vóór P0: eerst meten wat een echte taak kost, dan pas beslissen waar
een goedkoper model volstaat.

**Budgetten.** De huidige waarden (€5/dag globaal, €2/taak) zijn **voorlopig** en
staan er alleen omdat een bug nooit onbeperkt geld mag kosten. Na de eerste
pilots stellen we ze bij op gemeten cijfers, niet op een gok.

---

## Wat kan er misgaan, en wat er dan gebeurt

| Situatie | Wat de lus doet |
|---|---|
| De SDK-vorm wijkt af | B2 of B3 stopt met een precieze melding. Geen stille terugval. |
| `npm run test` staat al rood vóór we beginnen | De taak wordt geblokkeerd met "de repository staat al rood"; Claude draait niet eens. |
| Claude stelt een vraag die niet uit de kennisbasis te beantwoorden is | PARK als er ander werk is, anders BLOCK met een GitHub-issue en een directe e-mail. Er wordt niets ingevuld. |
| Claude voert een hard bedrag of percentage in | De verzonnen-waarde-detector houdt de commit tegen en maakt er een vraag van. |
| Tweemaal dezelfde falende test | Direct geblokkeerd; geen derde poging. |
| Het budget raakt op | De aanroep gaat niet door — de rem zit vóór de aanroep, niet erna. |
| De reviewer zegt `pass` terwijl een criterium open staat | Het verdict wordt verworpen en omgezet naar `revise`; geteld als reviewerfout. |

---

## Wat ik na de eerste run wil weten

Niet of het werkte — dat staat in het rapport. Wel:

1. **Verhouding AUTO / PARK / BLOCK.** Veel PARK betekent: de kennisbasis is te
   dun, niet dat het systeem stuk is.
2. **Kosten per afgeronde taak.** Bepaalt of de dagbudgetten realistisch staan.
3. **Of de reviewer iets ving dat de tests misten.** Dat is de meting die
   bepaalt of de beoordelaarsrol zijn kosten waard is — de meting die mijn eigen
   aanbeveling kan weerleggen.
