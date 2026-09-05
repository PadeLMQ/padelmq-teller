# Universele AI Development Orchestrator — haalbaarheidsanalyse & technisch ontwerp

**Versie:** 2 — bijgewerkt na jouw besluiten over B1 (API-verbruik) en B6 (projecten),
en na je correctie op de rol van de GPT-reviewer.
**Status:** ontwerp ter beoordeling. Nog niets geïmplementeerd.
**Datum:** 5 september 2026
**Opdrachtgever:** Mathias (PadeLMQ)

> **Wat er in versie 2 veranderd is**
> 1. B1 en B6 zijn beslist en verwerkt (§1, §5, §8).
> 2. De GPT-reviewer zit **wel** in V1. Mijn eerdere bezwaar ging over een andere rol
>    dan die jij bedoelde; ik trek dat deel in en leg uit waarom (§4).
> 3. Nieuwe kern van het ontwerp: de **projectkennisbasis** — de businesscontext hoort
>    niet in een chat maar in versiebeheerde bestanden (§5).
> 4. Nieuwe beslislaag **AUTO / PARK / BLOCK** met een citatieplicht (§6). Dit vervangt
>    de "doorwerken op een standaardaanname" uit versie 1, die in strijd was met
>    "nooit gokken".
> 5. Verplichte tegenspraak van beide modellen, structureel afgedwongen (§7).
> 6. Volledige kostenbewaking vanaf V1 (§9).
> 7. Faseplan herzien: V1 is groter maar strak begrensd, met een expliciete afkaplijn (§11).

---

## 1. Wat er nu vaststaat

| # | Beslissing | Uitkomst |
|---|---|---|
| **B1** | API-verbruik | **Akkoord.** Officiële API's met verbruiksfacturering. Voorwaarde: volledige kostenbewaking vanaf V1 — per project, per model, per taak, per dag, met instelbare limieten én waarschuwingen. Geen onbegrensde kosten. Uitgewerkt in §9. |
| **B6** | Projecten | **Geen vaste lijst, geen vast aantal.** Een project toevoegen is één commando. Elk project krijgt volledig gescheiden context, geschiedenis, configuratie, Claude-sessie en reviewer-context. Vermenging is architectonisch uitgesloten, niet alleen afgesproken. Uitgewerkt in §5. |
| **Reviewer** | Rol in V1 | **Blijft in V1.** Twee rollen: *beantwoorder* (vóór Claude) en *beoordelaar* (na de harde verificatie). Zie §4. |
| **Beslisvolgorde** | Hybride | Harde verificatie → reviewer/context → Claude → harde verificatie → volgende stap. Een model kan een harde test nooit overrulen. Zie §4.3. |
| **Grondregel** | Nooit gokken | Drie uitkomsten per vraag: AUTO, PARK, BLOCK. Een ontbrekende businessregel wordt nooit verzonnen om de lus draaiende te houden. Zie §6. |

---

## 2. Haalbaarheid — samenvatting

| Onderdeel | Haalbaar | Toelichting |
|---|---|---|
| Claude aansturen zonder chatvenster | **Ja, officieel** | Claude Agent SDK / `claude -p`: hervatbare sessies per project, JSON-uitvoer, rechtenmodel, kosten per run. |
| Reviewer met eigen geheugen per project | **Ja, via de OpenAI API** | Responses API met `previous_response_id`-ketening per project, plus structured outputs. |
| Je bestaande ChatGPT-chats hergebruiken | **Nee** | Geen officiële API voor de ChatGPT-app; geautomatiseerde toegang buiten de API valt onder het verbod in de gebruiksvoorwaarden. **Dit is nu het belangrijkste openstaande punt** — zie §5.2 en beslissing N1. |
| Onbeperkt projecten, strikt gescheiden | **Ja** | §5.1. |
| Doorlopen tot menselijke input nodig is | **Ja, met grenzen** | §6 en §10. |
| Vragen parkeren en gebundeld voorleggen | **Ja** | §6.4. |
| Geen handmatig knip- en plakwerk meer | **Ja** | Dat is precies wat V1 wegneemt. |

---

## 3. Waar de tijd nu heen gaat

| Verliespost | Wat het kost | Opgelost door |
|---|---|---|
| Knippen en plakken tussen twee chats | Seconden per stap, tientallen keren per dag | De orkestrator — verdwijnt volledig |
| **Jij bent de planner** | De lus staat stil zodra jij iets anders doet | Doorwerken zonder jou — grootste winst |
| Claude stelt een functionele/UX/business-vraag | Jij moet naar de juiste ChatGPT-chat, context ophalen, antwoord terugbrengen | De **beantwoorderrol** van de reviewer (§4.2) — dit is jouw eigenlijke bottleneck |
| Contextwissels | ~20 onderbrekingen per dag | Vraagbundeling (§6.4) |
| Verkeerd werk dat pas laat opvalt | Hele iteraties weggegooid | Harde verificatiepoort (§4.3) |

---

## 4. De rol van de reviewer — herziening van mijn eerdere bezwaar

### 4.1 Wat ik terugneem

In versie 1 stelde ik dat de tweede-modelstap uit V1 kon. Dat bezwaar richtte zich op de
rol die ik erin las: *een model dat het antwoord van een ander model leest en daar een
mooiere prompt van maakt*. Die rol voegt weinig toe en verbergt fouten.

De rol die jij beschrijft is een andere: **de bewaarplaats van eerdere beslissingen,
doelstellingen en businessregels, die de functionele en UX-vragen van Claude kan
beantwoorden.** Dat is geen tweede mening — dat is ontbrekende informatie aanleveren.
Zonder die stap moet jij zelf de brug slaan, en precies die brug is je bottleneck.
Mijn bezwaar was op die rol niet van toepassing. De reviewer blijft in V1.

Wat ik **niet** terugneem, en wat jij ook onderschrijft: waar hard bewijs bestaat, is hard
bewijs leidend. Een model kan een falende test niet wegredeneren.

### 4.2 Twee verschillende rollen, twee verschillende momenten

De reviewer verschijnt twee keer in de lus, met verschillende opdrachten en
verschillende uitvoerschema's:

| | **Beantwoorder** (vóór Claude) | **Beoordelaar** (na groene verificatie) |
|---|---|---|
| Invoer | Openstaande vragen van Claude, de taakspecificatie, de projectkennisbasis | De diff, de testuitslag, de acceptatiecriteria, de kennisbasis |
| Opdracht | Beantwoord wat aantoonbaar afleidbaar is; markeer de rest | Beoordeel of dit de taak echt afmaakt en of er iets beters bestaat |
| Uitvoer | Antwoord + **verplichte bronvermelding** + AUTO/PARK/BLOCK | `pass` / `revise` / `escalate` + bevindingen + betere alternatieven |
| Mag nooit | Een businessregel verzinnen | Een harde testuitslag tegenspreken |

### 4.3 De lus

```
  ┌── 0. BASELINE ────────────────────────────────────────────────────┐
  │   Draai de projectchecks vóór er iets wijzigt.                    │
  │   Waarom eerst: een repo die al rood staat, mag niet aan Claude   │
  │   worden toegeschreven. Jouw volgorde klopt hier.                 │
  └──────────────────────────┬────────────────────────────────────────┘
                             ▼
  ┌── 1. CONTEXT / BEANTWOORDEN — reviewer ───────────────────────────┐
  │   Openstaande vragen tegen de kennisbasis.                        │
  │   → AUTO: antwoord met bron, gaat de prompt in                    │
  │   → PARK: vraag geparkeerd, déze taak stopt, andere taken lopen   │
  │   → BLOCK: taak stopt, jij krijgt onmiddellijk bericht            │
  └──────────────────────────┬────────────────────────────────────────┘
                             ▼
  ┌── 2. UITVOEREN — Claude (Agent SDK) ──────────────────────────────┐
  │   Met de beantwoorde vragen in de prompt. Moet zelf nieuwe        │
  │   onzekerheden melden i.p.v. invullen.                            │
  └──────────────────────────┬────────────────────────────────────────┘
                             ▼
  ┌── 3. VERIFIËREN — hard bewijs, geen model ────────────────────────┐
  │   tests · typecheck · lint · build · databasechecks · smoke-run   │
  │   rood → terug naar 2 met de echte fout (max N pogingen)          │
  └──────────────────────────┬─── groen ──────────────────────────────┘
                             ▼
  ┌── 4. BEOORDELEN — reviewer ───────────────────────────────────────┐
  │   pass → commit    revise → terug naar 2    escalate → BLOCK      │
  │   Verdict wordt gevalideerd tegen de harde feiten uit stap 3.     │
  └───────────────────────────────────────────────────────────────────┘
```

**Hoe "een model overrulet nooit een test" wordt afgedwongen**, en niet slechts
afgesproken:

1. Rood bereikt de beoordelaar helemaal niet — stap 4 draait alleen op groen.
2. De orkestrator valideert het verdict tegen de machinaal vastgestelde feiten. Zegt de
   beoordelaar `pass` terwijl een acceptatiecriterium meetbaar niet gehaald is, dan wordt
   het verdict verworpen en geteld als reviewerfout in de kwaliteitsmeting.
3. De beoordelaar krijgt geen enkele mogelijkheid om een verificatiecommando te wijzigen,
   over te slaan of als "flaky" te markeren. Die knop bestaat niet.

---

## 5. Projecten: onbeperkt, en strikt gescheiden

### 5.1 Een project toevoegen

```
orchestrator project add <slug> --repo <pad-of-url>
```

Dit maakt aan:

```
projects/<slug>/
  project.yaml          repo, branch, verificatiecommando's, budgetten,
                        autonomieniveau, datapolicy, notificatiekanaal
  kennis/
    doelen.md           wat dit project moet bereiken
    businessregels.md   regels die het gedrag bepalen (prijzen, btw, limieten)
    beslissingen.md     append-only logboek: D-001, D-002, … met datum en reden
    woordenlijst.md     projecttaal, zodat beide modellen hetzelfde bedoelen
  state/
    tasks.db            of één gedeelde SQLite met een verplichte project_id
    sessions.json       Claude-sessie-id's en reviewer-response-id's
```

**Isolatie is structureel, niet procedureel.** Vier onafhankelijke sloten:

| Slot | Werking |
|---|---|
| Eigen werkmap | Claude draait met `cwd` in de projectmap; alleen die map en expliciet toegevoegde mappen zijn leesbaar |
| Eigen sessies | Eén Claude-sessie-id en één reviewer-gespreksketen per project; er bestaat nooit een gedeelde keten |
| Verplichte sleutel | Elke database-query loopt via een laag die `project_id` verplicht meegeeft; een query zonder project is een programmeerfout die de test vangt |
| Contextopbouw | De prompt wordt opgebouwd uit uitsluitend bestanden onder `projects/<slug>/`; er is geen codepad dat twee projectmappen tegelijk inleest |

Vermenging kan dus niet "ongemerkt" gebeuren, omdat er geen mechanisme is dat twee
projecten in één context brengt.

### 5.2 De kennisbasis — de belangrijkste toevoeging in versie 2

Je beschrijft dat ChatGPT "veel van onze eerdere beslissingen, doelstellingen en
businessregels kent". Dat is waar, en het is precies het probleem: **die kennis zit
opgesloten in chats die we niet via een API kunnen lezen.** Een reviewer die we via de
API aanspreken, begint met nul kennis van jouw projecten. Dan beantwoordt hij niets, of
erger: hij verzint iets.

Daarom verplaatst dit ontwerp de kennis van de chat naar **bestanden die de orkestrator
bezit**:

- Beide modellen lezen dezelfde bron, dus ze kunnen niet uiteenlopen.
- Elk AUTO-antwoord kan naar een regel verwijzen: *"btw-behandeling volgt D-014"*.
  Zonder verwijzing geen AUTO (§6.2).
- Jij kunt de regels lezen en corrigeren; je hoeft geen chat te doorzoeken.
- Het is leveranciersonafhankelijk. Wisselt de reviewer ooit van model of leverancier,
  dan blijft de kennis staan.
- Elk antwoord dat je op een geparkeerde vraag geeft, wordt automatisch als nieuwe
  beslissing toegevoegd. De kennisbasis groeit dus vanzelf naarmate je hem gebruikt.

**Hoe hij gevuld wordt bij de start** is een openstaande beslissing — zie N1 in §12.

---

## 6. Nooit gokken: AUTO / PARK / BLOCK

### 6.1 De drie uitkomsten

| Uitkomst | Wanneer | Wat er gebeurt |
|---|---|---|
| **AUTO** | Het antwoord is aantoonbaar afleidbaar uit een controleerbare bron | Antwoord gaat de prompt in, met bronvermelding in het logboek. Werk gaat door. |
| **PARK** | Geen bron, maar er kan veilig aan ander werk verder gegaan worden | De vraag wordt geparkeerd, **de afhankelijke taak stopt**, andere taken lopen door. Jij ziet hem in de bundel. |
| **BLOCK** | Een beslissing is noodzakelijk, of fout implementeren is te riskant | De taak stopt en jij krijgt onmiddellijk bericht. |

Twijfelregels, zoals je ze gaf:

- Twijfel tussen AUTO en PARK → **PARK**.
- Twijfel tussen PARK en BLOCK → BLOCK als er in dit project geen veilig, onafhankelijk
  werk overblijft; anders PARK.

> **Correctie op versie 1.** Versie 1 liet de lus doorwerken op een "standaardaanname"
> terwijl een vraag geparkeerd stond. Dat is in strijd met "nooit gokken" en vervalt.
> Een voorgestelde standaardkeuze wordt nog steeds getoond in de bundel — als **voorstel
> aan jou**, nooit als iets dat het systeem zelf toepast.

### 6.2 De citatieplicht — waarom niet op zelfvertrouwen

De voor de hand liggende implementatie is een zekerheidsscore: "beantwoord automatisch
boven 85% zekerheid". Dat werkt niet. Een taalmodel is het meest zelfverzekerd op precies
het punt waar het een plausibele businessregel verzint — de score correleert met
vloeiendheid, niet met juistheid.

Daarom is de poort **verifieerbaarheid, niet zelfvertrouwen**:

> AUTO is alleen toegestaan als het antwoord ten minste één bron noemt die de orkestrator
> zelf kan terugvinden: een beslissing-ID uit `beslissingen.md`, een regel uit
> `businessregels.md`, een bestand en regelnummer in de repo, of een testuitslag.
> De orkestrator controleert dat de bron bestaat en de bewering dekt. Klopt de verwijzing
> niet, dan degradeert het antwoord automatisch naar PARK.

### 6.3 Categorieën die nooit AUTO mogen zijn

Ongeacht bron of zekerheid, deze vragen gaan minimaal naar PARK en bij afhankelijkheid
naar BLOCK:

- geldbedragen, prijzen, kortingen, marges
- btw- en fiscale behandeling
- juridische of contractuele punten
- klant- of persoonsgegevens, bewaartermijnen
- beveiliging, toegang, rechten
- onomkeerbare datamodel- of migratiebeslissingen
- alles wat naar buiten zichtbaar is voor klanten

### 6.4 Parkeren, bundelen en hervatten

1. **Vastleggen** — vraag, waarom geblokkeerd, opties, voorgestelde keuze, de taken die
   ervan afhangen, en het project. Gelijke vragen worden ontdubbeld.
2. **Bundelen** — één overzicht per dag (en op verzoek) over alle projecten, gegroepeerd
   per project, met wat er stilligt.
3. **Antwoorden** — jouw antwoord gaat als nieuwe beslissing (`D-nnn`) de kennisbasis van
   het juiste project in, met datum en jouw formulering.
4. **Hervatten** — de orkestrator zoekt alle taken die op die vraag wachtten, zet ze terug
   op QUEUED en start ze in de juiste volgorde. Raakte het antwoord ook al afgerond werk,
   dan wordt daar automatisch een correctietaak voor geopend.

### 6.5 Claude dwingen om niet in te vullen

De grondregel geldt ook voor de uitvoerder, en die heeft een sterke neiging om door te
werken. Drie afdwingbare controles:

1. **Verplicht uitvoerveld.** Claude levert per stap `open_questions[]` én
   `assumptions_made[]`. Een aanname zonder bron wordt behandeld als een vraag: de commit
   wordt vastgehouden en de vraag gaat door de triage.
2. **Verzonnen-waarde-detector.** De diff wordt deterministisch gescand op nieuw
   ingevoerde harde waarden — bedragen, percentages, btw-tarieven, drempels, limieten.
   Elke nieuwe waarde die niet terug te voeren is op de kennisbasis, de bestaande code of
   de taakspecificatie, blokkeert de commit en wordt een vraag.
3. **Acceptatiecriteria als contract.** Een taak zonder toetsbare acceptatiecriteria komt
   de lus niet in. Dat dwingt af dat "klaar" objectief bestaat.

---

## 7. Verplichte tegenspraak

Je wilt geen bevestigingsmachine. Een instructie als "wees kritisch" is daarvoor te
zwak — dat verdampt na twee beurten. Daarom structureel:

1. **Verplicht veld.** Beide modellen leveren bij elke stap `better_alternative`:
   voorstel, waarom het beter is, welk bewijs dat steunt, wat het kost om te wisselen, en
   een aanbeveling (`nu doen` / `later` / `afgewogen en verworpen omdat…`). Het veld is
   verplicht; "geen" moet expliciet ingevuld worden en telt als een bewuste uitspraak.
2. **Een voorstel verandert nooit stilzwijgend het werk.** Een beter alternatief is per
   definitie een beslissing, en beslissingen gaan via PARK of BLOCK naar jou. Tegenspraak
   en "nooit gokken" botsen dus niet.
3. **De beoordelaar krijgt de opdracht om de taak zelf te betwisten**, niet alleen de
   uitvoering: is dit het juiste probleem, is er een eenvoudiger oplossing, maakt bestaande
   code dit overbodig.
4. **Meetbaar.** Het aandeel voorgestelde alternatieven dat jij overneemt, wordt geteld.
   Blijft dat op nul, dan produceert het veld ruis en passen we de instructie aan. Ligt het
   hoog, dan krijgt de rol meer gewicht.

---

## 8. Architectuur

Eén Python-daemon, één repository, één SQLite-bestand. Geen microservices, geen
berichtenbus. Op deze schaal is elke extra laag pure vertraging.

| Component | Verantwoordelijkheid |
|---|---|
| Projectregister | `projects/<slug>/project.yaml` + kennisbasis; toevoegen is één commando |
| Backlog | Taken met acceptatiecriteria, status, afhankelijkheden, project_id |
| Scheduler | Kiest de volgende taak; in V1 sequentieel, één taak tegelijk |
| Runner | De toestandsmachine van §4.3 voor één taak |
| ClaudeAdapter | Start/hervat een sessie, dwingt het uitvoerschema af |
| VerifyAdapter | Draait de projectchecks, classificeert het falen |
| ReviewAdapter | Beantwoorder- en beoordelaarsaanroepen, structured outputs |
| TriageEngine | AUTO/PARK/BLOCK, citatiecontrole, categoriepoort |
| KnowledgeStore | Lezen, doorzoeken en append-only bijschrijven van de kennisbasis |
| CostGuard | Meten, begrenzen en waarschuwen (§9) |
| GitAdapter | Worktree per run, branch `orch/<taak-id>`, commit, PR |
| Bundler | Geparkeerde vragen groeperen, versturen, antwoorden verwerken |

### Toestandsmachine

```
QUEUED → BASELINE → ANSWERING ─┬─(AUTO)──→ IMPLEMENTING
                               ├─(PARK)──→ PARKED
                               └─(BLOCK)─→ BLOCKED
IMPLEMENTING → VERIFYING ─┬─(rood, poging < N)→ IMPLEMENTING
                          ├─(rood, poging = N)→ BLOCKED
                          └─(groen)───────────→ REVIEWING
REVIEWING ─┬─(pass)────→ COMMITTING → DONE
           ├─(revise)──→ IMPLEMENTING   (max M rondes)
           └─(escalate)→ BLOCKED
PARKED / BLOCKED → (jouw antwoord) → QUEUED
elke toestand → FAILED  (budget op · time-out · herhaalde fout)
```

### Stopcondities

| Conditie | Startwaarde | Waarom |
|---|---|---|
| Iteraties implementeren ↔ verifiëren | 5 | Voorkomt de reparatiespiraal |
| Reviewrondes | 3 | Voorkomt oneindig "verbeteren" |
| Budget per taak | instelbaar | §9 |
| Wandkloktijd per run | 30 min | Vangt een vastgelopen run af |
| **Geen-vooruitgang-detector** | 2× gelijk | Tweemaal dezelfde falende testhandtekening of een identieke diff → direct BLOCKED |

---

## 9. Kostenbewaking (B1)

Vanaf V1, niet later.

**Meten.** Elke modelaanroep schrijft een regel weg met: project, taak, run, fase, model,
rol (uitvoerder/beantwoorder/beoordelaar), invoertokens, uitvoertokens, cachehits, kosten
en tijdstip. Daaruit rolt elke gewenste doorsnede: per project, per model, per taak, per
dag, per taaksoort.

**Begrenzen.** Vier niveaus, allemaal instelbaar per project en globaal:

| Niveau | Gedrag bij bereiken |
|---|---|
| Per run | Run stopt, taak → FAILED met reden `budget` |
| Per taak | Taak stopt, jij krijgt bericht |
| Per project per dag | Project pauzeert tot middernacht, andere projecten lopen door |
| **Globaal per dag** | **Alles pauzeert. Harde noodrem.** |

**Waarschuwen.** Bij 50%, 80% en 100% van elk dagbudget, plus een dagelijkse
kostenrapportage. Bij het bereiken van het globale dagplafond een directe melding.

**Vooraf remmen, niet achteraf constateren.** Vóór elke aanroep wordt de verwachte kosten
geschat op basis van de tokentelling; past die niet meer binnen het resterende budget, dan
wordt de aanroep niet gedaan. Je kunt dus niet over een limiet heen schieten door één dure
run.

**Kostenbeperkingen in het ontwerp zelf:** promptcaching op de stabiele projectcontext en
kennisbasis; de beoordelaar krijgt de diff plus de testuitslag, nooit de hele repo;
verificatie draait zonder model; triage en samenvatten op het goedkoopste model.

---

## 10. Veiligheid

1. **Nooit rechtstreeks naar `main`.** Worktree per run, branch `orch/<taak-id>`.
2. **Commit alleen na groene verificatie.** Geen uitzonderingen.
3. **Rechten expliciet** per project, plus `--permission-prompts none` zodat een
   onbewaakte run niet eeuwig wacht.
4. **Geheimen buiten de lus.** `.env`, tokens en secrets worden geredigeerd en gaan nooit
   in een prompt. Voor PadeLMQ concreet: de Shopify Client ID en Secret staan als
   GitHub-secret en mogen niet in diffs of logs belanden.
5. **Promptinjectie.** Repo-inhoud, issues en webpagina's zijn *data*, nooit opdracht.
   De lus mag zijn eigen budget-, rechten- of doelinstellingen nooit wijzigen op grond van
   gelezen tekst, en de kennisbasis wordt uitsluitend bijgeschreven vanuit jouw antwoorden
   — nooit door een model zelf.
6. **Noodstop.** Eén commando pauzeert alle runs.
7. **Alles gelogd.** Elke prompt, elk antwoord, elke bronverwijzing, elke kostenpost.

---

## 11. Faseplan

Je randvoorwaarde: dit mag geen wekenlang zijproject worden. Daarom is V1 strak begrensd
en is er een expliciete afkaplijn.

### V1 — de kleinste versie die je knip-en-plakwerk echt wegneemt

**Wel in V1**

1. `project add` met kennisbasis en configuratie (§5.1)
2. De volledige lus van §4.3, sequentieel: één taak tegelijk
3. Reviewer in beide rollen, met structured outputs
4. Triage AUTO/PARK/BLOCK inclusief citatiecontrole en categoriepoort (§6)
5. Claude-controles tegen invullen: verplichte velden, verzonnen-waarde-detector (§6.5)
6. Geparkeerde vragen, dagbundel, antwoordverwerking, automatisch hervatten (§6.4)
7. Volledige kostenbewaking en limieten (§9)
8. Git-worktree, branch, commit, PR (§10)
9. Stopcondities inclusief geen-vooruitgang-detector
10. Volledig logboek

**Bewust niet in V1** — zonder verlies van je doelen:

| Uitgesteld | Waarom dit nu niets kost |
|---|---|
| Parallelle uitvoering | Onbeperkt projecten werkt ook sequentieel; parallellisme is doorvoer, geen functionaliteit |
| Webdashboard | De bundel per e-mail plus het logboek volstaan om te beoordelen |
| Automatische taakontleding uit een roadmap | Je schrijft taken voorlopig zelf; dat is ook de plek waar acceptatiecriteria ontstaan |
| Sessie-hervattingsoptimalisatie | Werkt, maar de database is de waarheid; puur snelheidswinst |
| Tweede uitvoerder (Codex), A/B-vergelijking | Pas zinvol als er meetgegevens zijn |

**Afkaplijn.** Als een onderdeel de eerste volledig automatische taak niet nodig heeft,
gaat het naar V1.1. Ik meld het je op het moment dat ik iets verplaats, met de reden.

### V1.1 en verder — alleen op basis van meting

Parallelle projecten en scheduler · dashboard indien gemist · model per taaksoort
afstemmen · taakontleding · tweede uitvoerder.

---

## 12. Openstaande beslissingen

B1 en B6 zijn beslist (§1). B3 en B7 heb ik met een veilige standaard ingevuld — je kunt
ze wijzigen, maar ze hoeven V1 niet op te houden:

| # | Ingevuld met | Waarom dit veilig is |
|---|---|---|
| **B3** | Datapolicy per project, standaard: reviewer aan, `.env` en secrets altijd geredigeerd, alleen diffs en kennisbasis worden verzonden | Je hebt de reviewer in V1 gewild, dus verzenden is impliciet akkoord. De redactie is onvoorwaardelijk. Bij een project met klantgegevens zet je de schakelaar om bij het toevoegen. |
| **B7** | Startbudget €5/dag globaal, €2/taak; alles instelbaar per project | De mechaniek is wat telt (§9); de getallen wijzig je in de configuratie. |

**Wat ik nog echt van jou nodig heb — vijf punten:**

| # | Vraag | Waarom ik het niet zelf kan invullen |
|---|---|---|
| **B2** | Waar draait de orkestrator: een machine van jou die aan blijft, een kleine VPS, of GitHub Actions? | Bepaalt of nachtelijk doorwerken kan en hoe de opslag ingericht wordt. Ik ontwerp zo dat alle drie werken, maar V1 moet er één kiezen. |
| **N1** | Hoe vullen we de kennisbasis bij de start? ChatGPT-export, een korte vragenlijst per project, of leeg beginnen en hem laten volgroeien? | Dit bepaalt of de AUTO-route vanaf dag één werkt of pas na weken. Grootste invloed op je directe tijdwinst. Alleen jij kunt de export maken. |
| **B4** | Hoe ver mag het gaan met git: committen, pushen naar `orch/*`, PR openen, mergen? | Risicogrens. Mijn advies: alles behalve mergen. |
| **N3** | Via welk kanaal wil je een BLOCK-melding *onmiddellijk* krijgen, en waar mag de dagbundel heen? | "Onmiddellijk melden" is alleen echt als het kanaal je ook bereikt. |
| **B5** | Op welk project valideren we V1 als eerste? | V1 heeft één project nodig om zich te bewijzen. Dit beperkt de architectuur niet — die is projectonafhankelijk (B6). |

---

## 13. Meetplan

| Meetpunt | Wat het aantoont |
|---|---|
| Doorlooptijd per taak | De kernbelofte |
| Menselijke interventies per taak | Of het knip- en plakwerk echt weg is |
| **Verdeling AUTO / PARK / BLOCK** | Of de kennisbasis rijk genoeg is; veel PARK = kennisbasis vullen |
| Onterechte AUTO's die jij achteraf corrigeert | **De belangrijkste veiligheidsmeting.** Boven nul → citatieplicht aanscherpen |
| Onderbrekingen per dag buiten de bundel | Of het bundelen werkt |
| Kosten per afgeronde taak, per project en per model | Of het economisch klopt (B1) |
| Aandeel taken dat groen wordt zonder reviewronde | Wat de beoordelaarsrol toevoegt |
| Aandeel voorgestelde alternatieven dat jij overneemt | Of de verplichte tegenspraak waarde levert (§7) |

---

## 14. Bronnen

- Claude Agent SDK — overzicht: https://code.claude.com/docs/en/agent-sdk/overview
- Claude Agent SDK — sessies, resume en fork: https://code.claude.com/docs/en/agent-sdk/sessions
- Claude Code programmatisch draaien: https://code.claude.com/docs/en/headless
- OpenAI — gespreksstatus: https://developers.openai.com/api/docs/guides/conversation-state
- OpenAI — gestructureerde uitvoer: https://developers.openai.com/api/docs/guides/structured-outputs
- OpenAI — gebruiksvoorwaarden, geautomatiseerde toegang: https://openai.com/policies/row-terms-of-use/
- OpenAI Agents SDK (Python): https://github.com/openai/openai-agents-python
- OpenAI Codex CLI (`codex exec`): https://en.wikipedia.org/wiki/OpenAI_Codex_(AI_agent)
- Prijsindicatie OpenAI (derde partij, te verifiëren): https://www.morphllm.com/openai-api-pricing

---

*Er wordt niets geïmplementeerd voordat B2, N1, B4, N3 en B5 beantwoord zijn.*
