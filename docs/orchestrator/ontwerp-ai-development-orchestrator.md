# Universele AI Development Orchestrator — haalbaarheidsanalyse & technisch ontwerp

**Versie:** 8 — P0 is startklaar; alleen de OpenAI-sleutel ontbreekt nog.
**Status:** ontwerp vastgesteld. Kern gebouwd. Pilot: **PadeLMQ/padelmq-pro**.
**Datum:** 5 september 2026
**Opdrachtgever:** Mathias (PadeLMQ)

> **Nieuw in versie 3**
> 1. B2, N1, B4 en N3 beslist en verwerkt (§1).
> 2. Nieuw hoofdstuk: **import uit de ChatGPT-export** — pipeline, statusmodel en de
>    grens tussen "geïmporteerd" en "waar" (§6).
> 3. Nieuw hoofdstuk: **verificatiesterkte per project** (§8). Dit volgt rechtstreeks uit
>    je keuze voor een VPS en het is de belangrijkste nieuwe waarschuwing in dit document.
> 4. Uitlevering uitgewerkt: PR-inhoud, GitHub-issue-flow met antwoordherkenning,
>    dagrapport (§12).
> 5. Draaiomgeving VPS uitgewerkt, inclusief back-up van de kennisbasis (§13).
> 6. Eén beslissing blijft open: **B5 — het pilotproject** (§16).

---

## 1. Wat er nu vaststaat

| # | Beslissing | Uitkomst |
|---|---|---|
| **B1** | API-verbruik | **Akkoord.** Officiële API's met verbruiksfacturering. Voorwaarde: volledige kostenbewaking vanaf V1 — per project, model, taak en dag, met instelbare limieten én waarschuwingen (§11). |
| **B2** | Draaiomgeving | **Kleine VPS is de productieomgeving.** 24/7 autonoom, onafhankelijk van jouw computers. V1 mag lokaal ontwikkeld en getest worden, mits het zonder noemenswaardige aanpassing naar de VPS gaat (§13). |
| **N1** | Kennisbasis vullen | **ChatGPT-export met automatische extractie**, plus een korte gerichte vragenlijst voor uitsluitend wat onzeker, tegenstrijdig of onvolledig is. Geïmporteerde historie geldt **niet** automatisch als actuele waarheid (§6). Nieuwe projecten zonder historie starten met een korte intake. |
| **B4** | Git-autonomie | **Commit + push naar `orch/*` + automatisch een PR openen. Nooit automatisch mergen naar `main`**, ook niet bij groene tests, lint, typecheck, build en review. PR wordt volledig voorbereid (§12). Gecontroleerde auto-merge per project wordt als schakelaar ontworpen maar staat standaard uit en wordt in V1 niet geïmplementeerd. |
| **N3** | Meldingen | **GitHub-issue voor BLOCK** (met vaste inhoud en automatische antwoordherkenning) en **e-mail naar info@padelmq.be** voor het dagrapport, plus een korte directe e-mail bij een belangrijke BLOCK. Geen Telegram in V1; de meldlaag is modulair zodat Telegram of Slack later inplugbaar is (§12). |
| **B6** | Projecten | **Geen vaste lijst, geen vast aantal.** Een project toevoegen is één commando; isolatie is structureel afgedwongen (§5). |
| **B3** | Datapolicy | Per project instelbaar. Standaard: reviewer aan, `.env` en secrets onvoorwaardelijk geredigeerd, alleen diffs en kennisbasis verlaten de machine. |
| **B7** | Startbudget | €5/dag globaal, €2/taak; alles instelbaar per project. |
| — | Grondregel | **Nooit gokken.** AUTO / PARK / BLOCK met citatieplicht (§7). Een BLOCK in één project legt nooit de hele orkestrator stil. |

**B5 — pilot: `PadeLMQ/padelmq-pro`.** Bevestigd. Zie §16c voor de meting.

**Startklaar.** Het volledige draaiboek voor de eerste echte lus — de volgorde, de
pilottaak, en wat het eindrapport toont — staat in
[`p0-startdraaiboek.md`](p0-startdraaiboek.md). Er ontbreekt nog één ding: de
OpenAI-sleutel.

**Prioriteiten:** P0 = werkende Claude ↔ OpenAI-lus op de pilot, met AUTO/PARK/BLOCK
en veilige verificatie. P1 = notificaties en menselijke antwoorden terug de taak in.
P2 = spraak. P2 is nu ontworpen en de naad is gebouwd, maar blokkeert P0 niet (§16d).

---

## 2. Haalbaarheid — samenvatting

| Onderdeel | Haalbaar | Toelichting |
|---|---|---|
| Claude aansturen zonder chatvenster | **Ja, officieel** | Agent SDK / `claude -p`: hervatbare sessies, JSON-uitvoer, rechtenmodel, kosten per run. |
| Reviewer met eigen geheugen per project | **Ja, via de OpenAI API** | Responses API met `previous_response_id`-ketening per project, plus structured outputs. |
| Je ChatGPT-chats live koppelen | **Nee** | Geen officiële API; geautomatiseerde toegang buiten de API valt onder het verbod in de voorwaarden. **Wel** bruikbaar als eenmalige export — dat is precies wat N1 doet (§6). |
| Onbeperkt projecten, strikt gescheiden | **Ja** | §5. |
| 24/7 autonoom draaien | **Ja** | VPS, §13. |
| Vragen parkeren en gebundeld voorleggen | **Ja** | §7 en §12. |
| Geen handmatig knip- en plakwerk meer | **Ja** | Dat is wat V1 wegneemt. |

---

## 3. Waar de tijd nu heen gaat

| Verliespost | Opgelost door |
|---|---|
| Knippen en plakken tussen twee chats | De orkestrator — verdwijnt volledig |
| **Jij bent de planner** | Doorwerken zonder jou, 24/7 op de VPS |
| **Claude stelt een functionele, UX- of businessvraag** | De beantwoorderrol met de kennisbasis (§4, §6) — dit is je eigenlijke bottleneck |
| Contextwissels | Bundeling in het dagrapport (§12) |
| Verkeerd werk dat pas laat opvalt | Harde verificatiepoort (§4) |

---

## 4. De reviewer: twee rollen, twee momenten

Mijn eerdere bezwaar ging over een rol die jij niet bedoelde ("een model dat een mooiere
prompt schrijft"). De rol die jij beschrijft — de bewaarplaats van eerdere beslissingen die
Claude's functionele vragen beantwoordt — is geen tweede mening maar het aanleveren van
ontbrekende informatie. Dat bezwaar is daarop niet van toepassing; de reviewer blijft in V1.
Wat blijft staan: waar hard bewijs bestaat, is hard bewijs leidend.

| | **Beantwoorder** (vóór Claude) | **Beoordelaar** (na groene verificatie) |
|---|---|---|
| Invoer | Openstaande vragen, taakspecificatie, kennisbasis | Diff, testuitslag, acceptatiecriteria, kennisbasis |
| Opdracht | Beantwoord wat aantoonbaar afleidbaar is; markeer de rest | Maakt dit de taak echt af, en bestaat er iets beters? |
| Uitvoer | Antwoord + verplichte bronvermelding + AUTO/PARK/BLOCK | `pass` / `revise` / `escalate` + bevindingen + alternatief |
| Mag nooit | Een businessregel verzinnen | Een harde testuitslag tegenspreken |

### De lus

```
0. BASELINE      projectchecks vóór er iets wijzigt
                 (een repo die al rood stond, is niet Claude's schuld)
        ▼
1. BEANTWOORDEN  openstaande vragen tegen de kennisbasis
   reviewer      → AUTO (met bron)  → door naar 2
                 → PARK             → vraag geparkeerd, déze taak wacht,
                                      andere taken lopen door
                 → BLOCK            → taak stopt, GitHub-issue + directe e-mail
        ▼
2. UITVOEREN     Claude Agent SDK, met de beantwoorde vragen in de prompt
        ▼
3. VERIFIËREN    tests · typecheck · lint · build · db-checks · smoke-run
                 rood → terug naar 2 met de echte fout (max N)
        ▼ groen
4. BEOORDELEN    pass → commit + PR   revise → terug naar 2   escalate → BLOCK
```

**Hoe "een model overrulet nooit een test" wordt afgedwongen:** rood bereikt de beoordelaar
niet (stap 4 draait alleen op groen); de orkestrator verwerpt een `pass` die in tegenspraak
is met een meetbaar onvervuld acceptatiecriterium en telt dat als reviewerfout; en de
beoordelaar heeft geen enkele knop om een verificatiecommando te wijzigen, over te slaan of
als "flaky" te markeren.

---

## 5. Projecten: onbeperkt en strikt gescheiden (B6)

```
orchestrator project add <slug> --repo <pad-of-url>
```

```
projects/<slug>/
  project.yaml         repo, branch, checks, verificatiesterkte, budgetten,
                       autonomie, datapolicy, meldkanalen
  kennis/
    doel.md            wat de app is en moet bereiken
    architectuur.md    huidige opzet en status
    beslissingen.md    append-only: D-001, D-002, … met datum, status en bron
    businessregels.md  prijzen, btw, limieten, gedragsregels
    voorkeuren.md      vaste keuzes in stijl, stack, werkwijze
    verboden.md        aannames die nooit gemaakt mogen worden
    problemen.md       bekende problemen en hun status
    open.md            openstaande beslissingen
    historie.md        belangrijke context die niet in de andere bestanden past
    woordenlijst.md    projecttaal, zodat beide modellen hetzelfde bedoelen
  state/               taken, Claude-sessie-id's, reviewer-response-id's
```

Deze indeling volgt exact de categorieën die jij noemde bij N1, zodat de import er direct
in landt.

**Isolatie is structureel, niet procedureel** — vier onafhankelijke sloten:

| Slot | Werking |
|---|---|
| Eigen werkmap | Claude draait met `cwd` in de projectmap; alleen die map is leesbaar |
| Eigen sessies | Eén Claude-sessie en één reviewer-keten per project; nooit een gedeelde keten |
| Verplichte sleutel | Elke query loopt via een laag die `project_id` verplicht meegeeft; een query zonder project is een programmeerfout die de test vangt |
| Contextopbouw | De prompt wordt uitsluitend opgebouwd uit bestanden onder `projects/<slug>/` |

---

## 6. Import uit de ChatGPT-export (N1)

### 6.1 De pipeline

```
orchestrator import chatgpt <export.zip>
```

1. **Uitpakken en inventariseren.** De export bevat je gesprekken in een machineleesbaar
   bestand. De exacte structuur verifiëren we op jouw echte export vóór we de parser
   schrijven — ik ga niet uit van een formaat dat ik niet gezien heb.
2. **Toewijzen aan projecten.** Per gesprek stelt de orkestrator een project voor, op basis
   van titel en inhoud. **Een gesprek dat niet met voldoende zekerheid aan één project toe
   te wijzen is, komt in de bak `niet-toegewezen` en wordt nooit gebruikt tot jij het
   toewijst.** Dit is de enige plek in het hele ontwerp waar projectvermenging zou kunnen
   ontstaan, en daarom is het hier expliciet dichtgezet.
3. **Extraheren.** Per toegewezen gesprek worden uitspraken gedestilleerd in de categorieën
   van §5: doel, architectuur, beslissingen, businessregels, voorkeuren, verboden aannames,
   bekende problemen, openstaande beslissingen, historische context.
4. **Statussen toekennen** (zie 6.2) en tegenstrijdigheden markeren.
5. **Gerichte vragenlijst.** Alleen wat onzeker, tegenstrijdig of onvolledig is, komt bij
   jou terecht — gegroepeerd per project, met per punt de bron (gesprek en datum) en het
   voorstel. Wat eenduidig is, hoef je niet opnieuw in te voeren.

### 6.2 Statusmodel — geïmporteerd is niet hetzelfde als waar

Elk item in de kennisbasis draagt een status. Dit is de mechanische invulling van jouw
instructie dat historische informatie niet blind als actuele waarheid mag gelden:

| Status | Betekenis | Bruikbaar als bron voor AUTO? |
|---|---|---|
| `bevestigd` | Door jou bevestigd, of voortgekomen uit jouw antwoord op een PARK/BLOCK | **Ja** |
| `te bevestigen` | Geëxtraheerd en eenduidig, maar nooit door jou bekrachtigd | **Nee** — leidt tot PARK |
| `tegenstrijdig` | Twee of meer uitspraken over hetzelfde onderwerp spreken elkaar tegen | **Nee** — leidt tot PARK, met beide varianten getoond |
| `mogelijk verouderd` | Uitspraak is oud en er is later over hetzelfde onderwerp gesproken | **Nee** — leidt tot PARK |
| `vervallen` | Vervangen door een nieuwere bevestigde beslissing; blijft bewaard voor de geschiedenis | Nee |

Een latere uitspraak wint dus **niet** automatisch van een eerdere. Ze wordt een
*hypothese* die jij bevestigt. Zo kan de import het systeem niet stilletjes een verouderde
regel laten toepassen.

### 6.3 Eerlijke verwachting

Ik wil je hier niet te veel van voorspiegelen. Een chatgeschiedenis bevat naast genomen
beslissingen ook: ideeën die je verkend en verworpen hebt, voorstellen van het model die je
nooit hebt overgenomen, en tussenstanden die later zijn omgegooid. Automatische extractie
kan die niet betrouwbaar onderscheiden van vaststaand beleid — de tekst ziet er hetzelfde
uit.

Verwacht daarom dat een **aanzienlijk deel** van de items als `te bevestigen` of
`tegenstrijdig` uit de import komt, en dat je validatiepas langer duurt dan "een korte
vragenlijst". Dat is geen fout in het systeem; het is de eerlijke prijs van niet gokken.

**Mitigatie, en meteen mijn voorstel voor de volgorde:** we importeren **eerst één project**
en meten de verhouding tussen eenduidig en onzeker. Valt die goed uit, dan doen we de rest
op dezelfde manier. Valt die tegen, dan is de korte intake per project sneller en beter, en
schakelen we om zonder dat je tijd verloren hebt. Dit sluit ook direct aan bij B5.

### 6.4 Wat de import met je gegevens doet

De extractie vereist dat een model de gesprekken leest. Standaardinstelling, tenzij je
anders zegt:

- De import draait op jouw machine of jouw VPS; de export zelf wordt nergens opgeslagen
  buiten jouw omgeving.
- Alleen gesprekken die jij aan een project hebt toegewezen worden verwerkt. De rest wordt
  niet gelezen.
- Extractie gebeurt door **Claude**, de leverancier die je uitvoerder toch al is — zodat de
  volledige historie niet ook nog bij een tweede leverancier terechtkomt.
- Redactie van sleutels, tokens en wachtwoorden gebeurt vóór verzending, onvoorwaardelijk.
- De ruwe export wordt na de import niet bewaard in de orkestrator; alleen de geëxtraheerde
  items, met verwijzing naar het bron-gesprek.

### 6.5 Projecten zonder historie

`orchestrator project add <slug> --intake` start een korte gestructureerde intake langs
dezelfde categorieën. Het resultaat krijgt direct status `bevestigd`, want jij hebt het
zelf zojuist gezegd.

### 6.6 Bijhouden tijdens de ontwikkeling

Elke definitieve beslissing die tijdens het werk valt — jouw antwoord op een PARK of BLOCK,
of een door jou overgenomen beter alternatief — wordt automatisch als `bevestigd` item
toegevoegd, met datum, jouw formulering en de taak waaruit het voortkwam. **Alleen jouw
antwoorden schrijven de kennisbasis bij; een model kan dat nooit zelf** (zie §14, punt 5).

---

## 7. Nooit gokken: AUTO / PARK / BLOCK

| Uitkomst | Wanneer | Wat er gebeurt |
|---|---|---|
| **AUTO** | Aantoonbaar afleidbaar uit een controleerbare bron met status `bevestigd` | Antwoord gaat de prompt in, met bronvermelding in het logboek |
| **PARK** | Geen bevestigde bron, maar er kan veilig aan ander werk verder gegaan worden | Vraag geparkeerd, de afhankelijke taak wacht, andere taken lopen door |
| **BLOCK** | Een beslissing is noodzakelijk, of fout implementeren is te riskant | Taak stopt, GitHub-issue aangemaakt, directe e-mail |

Twijfelregels: AUTO versus PARK → **PARK**. PARK versus BLOCK → BLOCK als er in dit project
geen veilig, onafhankelijk werk overblijft; anders PARK.

### De citatieplicht

Een zekerheidsscore ("beantwoord automatisch boven 85%") werkt niet: een taalmodel is het
meest zelfverzekerd op precies het punt waar het een plausibele businessregel verzint. De
score meet vloeiendheid, niet juistheid. De poort is daarom verifieerbaarheid:

> AUTO is alleen toegestaan als het antwoord ten minste één bron noemt die de orkestrator
> zelf kan terugvinden **en die status `bevestigd` heeft**: een beslissing-ID, een regel uit
> `businessregels.md`, een bestand met regelnummer in de repo, of een testuitslag. Klopt de
> verwijzing niet, of heeft de bron een andere status, dan degradeert het antwoord
> automatisch naar PARK.

### Categorieën die nooit AUTO mogen zijn

Ongeacht bron of zekerheid: geldbedragen en prijzen · btw en fiscaliteit · juridische en
contractuele punten · klant- en persoonsgegevens · beveiliging en toegangsrechten ·
onomkeerbare datamodel- of migratiebeslissingen · alles wat naar buiten zichtbaar is voor
klanten. Plus alles wat in `verboden.md` van het project staat.

### Claude dwingen om niet in te vullen

1. **Verplichte uitvoervelden** `open_questions[]` en `assumptions_made[]`. Een aanname
   zonder bron wordt een vraag; de commit wordt vastgehouden.
2. **Verzonnen-waarde-detector.** De diff wordt deterministisch gescand op nieuw ingevoerde
   harde waarden — bedragen, percentages, btw-tarieven, drempels, limieten. Elke waarde die
   niet terug te voeren is op de kennisbasis, bestaande code of de taakspecificatie,
   blokkeert de commit en wordt een vraag.
3. **Acceptatiecriteria als contract.** Een taak zonder toetsbare criteria komt de lus niet in.

---

## 8. Verificatiesterkte per project — de belangrijkste nieuwe waarschuwing

Het hele ontwerp leunt op één aanname: **dat er hard bewijs bestaat.** Draait er in een
project geen zinvolle testsuite, dan valt die poort weg en degradeert de lus precies tot
wat ik in versie 1 afraadde — twee modellen die het met elkaar eens worden. Je keuze voor
een VPS maakt dit concreet: de checks moeten dáár kunnen draaien, niet alleen op jouw
machine.

Daarom krijgt elk project een expliciete, in `project.yaml` vastgelegde inschatting:

| Sterkte | Kenmerk | Gedrag van de orkestrator |
|---|---|---|
| **Sterk** | Tests dekken het gedrag dat de taak raakt; build en typecheck draaien | Normale limieten. De lus mag zelfstandig itereren. |
| **Matig** | Alleen lint, build of een smoke-run; weinig of geen gedragstests | Minder iteraties, reviewer strenger, PR krijgt het label `zwakke verificatie` |
| **Zwak** | Niets machinaal toetsbaars | Geen zelfstandige iteratie. Elke wijziging gaat na één ronde naar een PR, met een expliciete waarschuwing dat er geen hard bewijs is. |

**Wat dit voor je betekent:** in een project met zwakke verificatie is de eerste zinvolle
taak vaak *"zet een minimale testsuite op voor het deel dat we gaan wijzigen"*. Dat voelt
als een omweg, maar het is de investering die alle latere automatisering in dat project
mogelijk maakt. Ik zal dat per project benoemen in plaats van stilzwijgend met een zwakke
poort door te werken.

**Praktisch gevolg voor de VPS:** per project moet vaststaan welke checks daar kunnen
draaien. Heeft een project een database, een browsertestsuite of een zware build nodig, dan
is dat een concreet installatiepunt op de VPS — of we accepteren bewust een lagere
verificatiesterkte voor dat project. Ik inventariseer dit bij het toevoegen van elk project.

---

## 9. Verplichte tegenspraak

Je wilt geen bevestigingsmachine, en een instructie als "wees kritisch" verdampt na twee
beurten. Daarom structureel:

1. **Verplicht veld** `better_alternative` bij elke stap van beide modellen: voorstel, waarom
   beter, welk bewijs dat steunt, wat het kost om te wisselen, en een aanbeveling
   (*nu doen* / *later* / *afgewogen en verworpen omdat…*). "Geen" moet expliciet ingevuld
   worden en telt als bewuste uitspraak.
2. **Een voorstel verandert nooit stilzwijgend het werk.** Een beter alternatief is een
   beslissing, en beslissingen gaan via PARK of BLOCK naar jou. Tegenspraak en "nooit
   gokken" botsen dus niet.
3. **De beoordelaar betwist ook de taak zelf**: is dit het juiste probleem, bestaat er een
   eenvoudiger oplossing, maakt bestaande code dit overbodig.
4. **Meetbaar.** Het aandeel voorgestelde alternatieven dat jij overneemt wordt geteld
   (§17).

---

## 10. Architectuur

Eén Python-daemon, één repository, één SQLite-bestand. Geen microservices, geen
berichtenbus.

| Component | Verantwoordelijkheid |
|---|---|
| Projectregister | `project.yaml` + kennisbasis; toevoegen is één commando |
| Backlog | Taken met acceptatiecriteria, status, afhankelijkheden, `project_id` |
| Scheduler | Kiest de volgende taak; in V1 sequentieel, één taak tegelijk |
| Runner | De toestandsmachine hieronder, voor één taak |
| ClaudeAdapter | Start of hervat een sessie, dwingt het uitvoerschema af |
| VerifyAdapter | Draait de projectchecks, classificeert het falen |
| ReviewAdapter | Beantwoorder- en beoordelaarsaanroepen, structured outputs |
| TriageEngine | AUTO/PARK/BLOCK, citatiecontrole, statuscontrole, categoriepoort |
| KnowledgeStore | Lezen, doorzoeken, statusbeheer, append-only bijschrijven |
| **ImportEngine** | ChatGPT-export uitpakken, toewijzen, extraheren, statussen zetten (§6) |
| CostGuard | Meten, begrenzen, waarschuwen, vooraf remmen (§11) |
| GitAdapter | Worktree per run, branch `orch/<taak-id>`, commit, push, PR (§12) |
| **Notifier** | Modulaire meldlaag: e-mail en GitHub in V1; Telegram/Slack later inplugbaar |
| **AnswerWatcher** | Volgt GitHub-issues op antwoorden en voert ze terug de kennisbasis in (§12) |

### Toestandsmachine

```
QUEUED → BASELINE → ANSWERING ─┬─(AUTO)──→ IMPLEMENTING
                               ├─(PARK)──→ PARKED
                               └─(BLOCK)─→ BLOCKED
IMPLEMENTING → VERIFYING ─┬─(rood, poging < N)→ IMPLEMENTING
                          ├─(rood, poging = N)→ BLOCKED
                          └─(groen)───────────→ REVIEWING
REVIEWING ─┬─(pass)────→ COMMITTING → PR_OPEN → DONE
           ├─(revise)──→ IMPLEMENTING   (max M rondes)
           └─(escalate)→ BLOCKED
PARKED / BLOCKED → (jouw antwoord) → QUEUED
elke toestand → FAILED  (budget op · time-out · herhaalde fout)
```

### Stopcondities

| Conditie | Startwaarde |
|---|---|
| Iteraties implementeren ↔ verifiëren | 5 bij sterke verificatie, 2 bij matige, 1 bij zwakke (§8) |
| Reviewrondes | 3 |
| Budget per taak | instelbaar, standaard €2 |
| Wandkloktijd per run | 30 min |
| **Geen-vooruitgang-detector** | Tweemaal dezelfde falende testhandtekening of een identieke diff → direct BLOCKED |

---

## 11. Kostenbewaking (B1)

**Meten.** Elke modelaanroep logt project, taak, run, fase, model, rol, invoertokens,
uitvoertokens, cachehits, kosten en tijdstip. Daaruit rolt elke doorsnede: per project,
model, taak, dag of taaksoort.

**Begrenzen** — vier niveaus, instelbaar per project en globaal:

| Niveau | Gedrag bij bereiken |
|---|---|
| Per run | Run stopt, taak → FAILED met reden `budget` |
| Per taak | Taak stopt, melding |
| Per project per dag | Project pauzeert tot middernacht; andere projecten lopen door |
| **Globaal per dag** | **Alles pauzeert. Harde noodrem.** |

**Waarschuwen.** Bij 50%, 80% en 100% van elk dagbudget, plus het dagrapport.

**Vooraf remmen, niet achteraf constateren.** Vóór elke aanroep wordt de verwachte kosten
geschat uit de tokentelling; past die niet binnen het resterende budget, dan gaat de aanroep
niet door. Eén dure run kan dus niet over een limiet heen schieten.

**In het ontwerp zelf:** promptcaching op de stabiele projectcontext en kennisbasis; de
beoordelaar krijgt de diff plus testuitslag, nooit de hele repo; verificatie draait zonder
model; triage en samenvatten op het goedkoopste model.

---

## 12. Uitlevering en meldingen (B4, N3)

### 12.1 De pull request

Elke afgeronde taak levert een PR op `orch/<taak-id>` op. Nooit een merge naar `main` — ook
niet als alles groen is. De PR-omschrijving wordt volledig voorbereid:

- **Wat** er gewijzigd is, in gewone taal, en **waarom** — met verwijzing naar de taak en de
  acceptatiecriteria
- **Welke verificatie** gedraaid heeft en met welk resultaat, inclusief de
  verificatiesterkte van het project (§8)
- **Welke vragen automatisch beantwoord zijn** en op welke bron — zodat je een verkeerde
  AUTO kunt terugdraaien
- **Resterende risico's** en wat er bewust niet gedaan is
- **Geparkeerde vragen** die aan deze wijziging raken
- **Het voorgestelde betere alternatief**, indien er een was (§9)

**Auto-merge** wordt als schakelaar in `project.yaml` ontworpen (`auto_merge: false`), maar
niet geïmplementeerd in V1. Zo kunnen we hem later per project aanzetten als de meetgegevens
het rechtvaardigen, zonder herbouw.

### 12.2 BLOCK → GitHub-issue

Bij een BLOCK maakt de orkestrator een issue aan in het juiste projectrepo, met label
`orch:block`, en verstuurt een korte directe e-mail. Vaste inhoud, zoals je vroeg:

1. Waar Claude mee bezig was — taak, doel, de stap waarin het vastliep
2. Welke beslissing nodig is
3. **Waarom AUTO niet verantwoord was** — geen bevestigde bron, tegenstrijdige items, of
   een verboden categorie
4. Welke opties er zijn, met de gevolgen per optie
5. Wat de orkestrator zelf aanbeveelt, en waarom
6. Welke werkzaamheden ondertussen wél veilig doorgaan

**Antwoordherkenning.** De `AnswerWatcher` volgt de issue. Zodra jij reageert:

1. Je antwoord wordt geïnterpreteerd en de orkestrator plaatst **eerst een bevestiging** in
   de issue: *"Ik heb dit vastgelegd als D-018: … Klopt dat?"*
2. Is het antwoord ambigu of dekt het de vraag niet volledig, dan stelt hij één gerichte
   vervolgvraag in plaats van te kiezen. Ook hier: niet gokken.
3. Bij bevestiging gaat het item als `bevestigd` de kennisbasis in, keren de wachtende
   taken terug naar QUEUED en sluit de issue.

Eén BLOCK legt nooit meer stil dan de taken die er daadwerkelijk van afhangen. Andere
projecten en onafhankelijke taken binnen hetzelfde project lopen door.

### 12.3 Dagrapport per e-mail

Eén e-mail per dag naar info@padelmq.be met, gegroepeerd per project: geparkeerde vragen
met voorgestelde keuze, nog openstaande BLOCK's, afgeronde taken, geopende PR's, opgetreden
problemen, en het kostenoverzicht van die dag.

### 12.4 Modulariteit

`Notifier` is één interface met per kanaal een adapter. V1 levert `email` en `github`.
Telegram of Slack is later één extra adapter plus een regel configuratie — geen wijziging
aan de lus.

---

## 13. Draaiomgeving: de VPS (B2)

**Productie is de VPS.** Ontwikkelen mag lokaal, mits deployen niets meer is dan de code
kopiëren en de configuratie zetten. Daarvoor:

| Ontwerpregel | Reden |
|---|---|
| Alle instellingen via omgevingsvariabelen en `project.yaml`; nul absolute paden in de code | Lokaal en VPS draaien identiek |
| Alle veranderlijke gegevens onder één datamap (`data/`): database, projectmappen, kennisbasis, logboek | Eén map om te back-uppen en te verhuizen |
| Draaien als systemd-service met automatische herstart | Overleeft een herstart van de VPS |
| Geen afhankelijkheid van sessie-hervatting voor de correctheid | De database is de waarheid; sessies zijn snelheidswinst |
| Alle geheimen in een `.env` met beperkte rechten, nooit in git | Standaardpraktijk, en de VPS is bereikbaar vanaf internet |

**Wat de VPS moet kunnen draaien:** de orkestrator zelf is licht, maar de **projectchecks**
draaien er ook — zie §8. Bij elk project inventariseren we wat daarvoor nodig is. Ik geef
pas een concrete specificatie als ik weet welke projecten er komen; voor een project als
`padelmq-teller` (Python plus `requests`) volstaat de kleinste maat ruimschoots.

**Back-up van de kennisbasis.** Dit is het waardevolste dat het systeem opbouwt — jouw
bevestigde beslissingen. Voorstel: de map `data/projects/*/kennis/` is zelf een git-repo die
na elke wijziging naar een **privé** GitHub-repo wordt gepusht. Gratis, versiebeheerd,
buiten de VPS, en je kunt de geschiedenis van elke beslissing teruglezen. De database wordt
dagelijks als bestand mee geback-upt.

---

## 14. Veiligheid

1. **Nooit rechtstreeks naar `main`.** Worktree per run, branch `orch/<taak-id>`, PR.
2. **Commit alleen na groene verificatie.** Geen uitzonderingen.
3. **Rechten expliciet** per project, plus `--permission-prompts none` zodat een onbewaakte
   run niet eeuwig wacht.
4. **Geheimen buiten de lus.** `.env`, tokens en secrets worden onvoorwaardelijk
   geredigeerd. Voor PadeLMQ concreet: de Shopify Client ID en Secret staan als
   GitHub-secret en mogen niet in diffs, prompts of logs belanden.
5. **Promptinjectie.** Repo-inhoud, issues, geïmporteerde gesprekken en webpagina's zijn
   *data*, nooit opdracht. De lus mag zijn eigen budget-, rechten- of doelinstellingen nooit
   wijzigen op grond van gelezen tekst, en **de kennisbasis krijgt de status `bevestigd`
   uitsluitend door jouw antwoord — nooit door een model.** Dit geldt ook voor teksten in de
   GitHub-issue: alleen een reactie van de repo-eigenaar telt als antwoord.
6. **Noodstop.** Eén commando pauzeert alle runs.
7. **Alles gelogd.** Elke prompt, elk antwoord, elke bronverwijzing, elke kostenpost.

---

## 15. Wat V1 wordt

**Wel in V1**

1. `project add` met kennisbasis, en `import chatgpt` met toewijzing, extractie, statussen
   en validatievragenlijst (§6)
2. De volledige lus van §4, sequentieel: één taak tegelijk
3. Reviewer in beide rollen, met structured outputs
4. Triage AUTO/PARK/BLOCK met citatie-, status- en categoriepoort (§7)
5. Verificatiesterkte per project, met aangepaste limieten (§8)
6. Claude-controles tegen invullen, inclusief verzonnen-waarde-detector
7. Geparkeerde vragen, dagrapport, GitHub-issues met antwoordherkenning, automatisch
   hervatten (§12)
8. Volledige kostenbewaking en limieten (§11)
9. Worktree, branch, commit, push, voorbereide PR (§12)
10. Stopcondities inclusief geen-vooruitgang-detector
11. Draaiend als service op de VPS, met back-up van de kennisbasis (§13)
12. Volledig logboek

**Bewust niet in V1** — zonder verlies van je doelen:

| Uitgesteld | Waarom dit nu niets kost |
|---|---|
| Parallelle uitvoering | Onbeperkt projecten werkt ook sequentieel; parallellisme is doorvoer, geen functionaliteit |
| Auto-merge | Schakelaar wordt ontworpen, staat uit; jij wilde hem sowieso uit |
| Webdashboard | Dagrapport, issues en logboek volstaan |
| Automatische taakontleding uit een roadmap | Je schrijft taken zelf; daar ontstaan ook de acceptatiecriteria |
| Telegram/Slack | Eén extra adapter, later |
| Tweede uitvoerder (Codex), A/B-vergelijking | Pas zinvol met meetgegevens |

**Afkaplijn.** Heeft een onderdeel de eerste volledig automatische taak niet nodig, dan gaat
het naar V1.1. Ik meld het je op het moment dat ik iets verplaats, met de reden.

---

## 16. Wat er nog open staat

### B5 — het pilotproject

V1 heeft één project nodig om zich op te bewijzen. Dat beperkt de architectuur niet; die is
projectonafhankelijk (B6). Ik zoek het project waar je op dit moment de meeste
Claude↔GPT-iteraties op doet, want daar is de tijdwinst het grootst en wordt het snelst
zichtbaar of het werkt.

Ik ken alleen `padelmq-teller`, en dat is als pilot niet ideaal: het is één afgerond
HTML-bestand met een uurscript, er is weinig doorlopende ontwikkeling en de
verificatiesterkte is laag (§8). Het bewijst V1 dus maar half.

**Wat ik van je nodig heb:** de naam van het project, waar de repository staat, en globaal
wat er machinaal getest kan worden (tests, typecheck, build, of niets van dat alles). Op
basis daarvan bepaal ik de verificatiesterkte en de eerste taken.

### Praktische voorbereidingen — geen beslissingen, wel randvoorwaarden

Deze kun je alvast klaarzetten; ze zijn nodig vóór de eerste run, niet vóór het ontwerp:

| Wat | Waarvoor |
|---|---|
| Anthropic API-sleutel met eigen budgetplafond | Claude als uitvoerder |
| OpenAI API-sleutel met eigen budgetplafond | De reviewer |
| VPS met SSH-toegang | De draaiomgeving (§13) |
| SMTP-gegevens of een transactionele mailservice | Het dagrapport en de directe BLOCK-melding |
| GitHub-token met toegang tot de betrokken repo's | Push, PR en issues |
| Privé GitHub-repo voor de back-up van de kennisbasis | §13 |
| ChatGPT-data-export | De import (§6) — begin met het pilotproject |

---

## 16b. Wat er nu gebouwd is

De projectonafhankelijke kern staat in `orchestrator/`. Dat kon zonder B5, want de
architectuur kent geen vaste projectlijst — dat is precies wat beslissing B6 garandeert.
Jouw pilotproject aankoppelen is één commando.

**Werkt en is getest** (72 tests, `python3 -m unittest discover -s tests -t .`):

| Onderdeel | Waar |
|---|---|
| Projectregister, `project add` met kennisbasis | `projects.py`, `knowledge.py` |
| Projectisolatie met verplichte `project_id` in elke query | `db.py` |
| Statusmodel van de kennisbasis; alleen `bevestigd` is citeerbaar | `knowledge.py` |
| Triage AUTO/PARK/BLOCK met citatie-, status- en categoriepoort | `triage.py` |
| Verzonnen-waarde-detector op de diff | `guards.py` |
| Aanname zonder bron houdt de commit tegen | `runner.py` |
| Geen-vooruitgang-detector | `guards.py`, `db.py` |
| Kostenbewaking, vier niveaus, rem vóór de aanroep, waarschuwingen | `cost.py` |
| Verificatiesterkte met meeschalende iteratielimieten | `verify.py`, `models.py` |
| De toestandsmachine, end-to-end getest met echte git en echte checks | `runner.py` |
| Redactie van geheimen vóór alles wat de machine verlaat | `redact.py` |
| Beoordelaar kan een testuitslag niet overrulen | `adapters/reviewer.py` |
| GitHub-issue bij BLOCK, antwoord met bevestigingsstap, taken hervatten | `answers.py` |
| Dagrapport en PR-omschrijving | `report.py` |
| Noodstop, opdrachtregel, systemd-units voor de VPS | `cli.py`, `deploy/` |

**Bewust nog niet af, met reden:**

| Onderdeel | Waarom |
|---|---|
| `import chatgpt` | Weigert te draaien. Het ontwerp legt vast dat we de structuur van de export op een echt bestand verifiëren voordat we de parser schrijven. Een parser op een geraden formaat is precies het giswerk dat we hier niet doen. |
| De reviewer-aanroep | De code staat er, maar de exacte parametervorm van de Responses API moet met één echte aanroep bevestigd worden vóór de eerste productierun. |
| PR automatisch openen | De omschrijving wordt al gebouwd en de GitHub-aanroep bestaat; de runner laat de branch nu klaarstaan. Kleine stap, wacht op een echt project. |
| Parallelle projecten, auto-merge, dashboard | Zoals afgesproken buiten V1. |

**Let op — deze repository is publiek.** De kern staat daarom bewust los van de
gegevens: de datamap (`ORCH_DATA_DIR`, standaard buiten de repository) bevat de
kennisbasis met je businessregels en hoort nooit in een publiek repo. Voordat dit in
productie gaat, verhuist de code naar een eigen repository.

---

## 16c. De pilot: PadeLMQ/padelmq-pro

### Waarom dit project

De README opent met: *"Een verbeterde heropbouw van het PadelMQ product-dashboard… bevat
deze versie een prijs- en voorraad-engine: automatisch stock en prijzen ophalen bij de bron
én bij concurrenten, en automatisch herprijzen."* Next.js 14, TypeScript, SQLite.

### De harde grens tijdens de pilot

De orkestrator automatiseert **softwareontwikkeling**, geen bedrijfsvoering. Alleen deze
commando's mogen automatisch draaien:

| Toegestaan | Verboden |
|---|---|
| `npm run test` · `npm run typecheck` · `npm run build` · `npm run lint` | `npm run sync` · `daily` · `scan:priority` · `scan:stock` · `scan:urgent` · `import:shopify` · `import:oldapp` · `setup:shops` · `discover:new` · `flag:bestsellers` |

Dat is niet alleen configuratie: de verboden lijst komt in `verboden.md` van het project,
zodat de triage elke vraag die daaraan raakt nooit automatisch beantwoordt.

**Gecontroleerd vóór er iets draaide:** de testsuite mockt `src/lib/shopify` in elk
testbestand, zet `DATABASE_PATH` naar een tijdelijke map en gebruikt alleen verzonnen
domeinen. `npm run test` raakt dus geen enkele echte winkel, prijs of voorraad.

### Verificatiesterkte: sterk

`test` (vitest), `typecheck` (tsc), `build` (next) en `lint` zijn alle vier aanwezig.
214 tests slaagden op de uitgangsstand.

### De coveragemeting — en wat die veranderde

Mijn eerdere inschatting was gebaseerd op bestandsnamen. De echte meting corrigeerde die
in twee richtingen.

| Module | Vóór (stmts / branch) | Na | Oordeel |
|---|---|---|---|
| `cost.ts` | 50,0% / 45,5% | **100% / 100%** | `isBallBox` en `tiendaCost` waren volledig ongedekt — de omzetting van de Tienda-prijs naar je kostbasis |
| `brandRules.ts` | 13,3% / 10,0% | **100% / 100%** | `brandFloor` was ongedekt — de MAP-vloer |
| `repricing.ts` | 75,6% / 52,4% | **100% / 97,6%** | alleen `match_lowest` was gedekt; `fixed`, `percent_below`, `beat_lowest` en de uitverkocht-regel niet |
| `brain.ts` | 82,4% / 87,5% | ongewijzigd | **beter dan ik dacht**; mijn bestandsnaam-inschatting was hier te somber |
| `shopify.ts` | 0% / 0% | **95,8% / 77,0%** | het externe schrijfpad; nu getest tegen een nagebouwde Admin-API op fetch-niveau |
| `stockSync.ts` | 0% / 0% | **79,2% / 74,4%** | de voorraadsync; de veiligheidsgaranties uit de kop van de module zijn nu bewezen |

Er staan nu 272 tests, allemaal groen. De nieuwe tests staan op branch
`orch/tests-geldmodules`; `main` is niet aangeraakt.

### Twee bevindingen, vastgelegd maar niet gerepareerd

Beide zijn beslissingen, geen bugs die een model even mag oplossen:

1. **De .99-afronding verlaagt ook ronde bedragen.** Een concurrent op €90 leidt tot
   €89,99, niet €90. Bedoeld of niet — het is nu vastgelegd in een test.
2. **De wijzigingsdrempel vergelijkt onafgeronde getallen.** `Math.abs(target -
   currentPrice) >= 0.01` levert voor 79,99 tegen 79,98 de waarde 0,00999999999999801 op:
   een verschil van precies één cent wordt niet gezien. Commercieel verwaarloosbaar, maar
   de drempel is niet wat hij lijkt. Voorstel: vergelijk in hele centen.

### Het schrijfpad naar Shopify

Twee pull requests, beide alleen tests, geen productiecode:

| PR | Inhoud |
|---|---|
| [#1](https://github.com/PadeLMQ/padelmq-pro/pull/1) `orch/tests-geldmodules` | `cost.ts`, `brandRules.ts`, `repricing.ts` |
| [#2](https://github.com/PadeLMQ/padelmq-pro/pull/2) `orch/tests-shopify-schrijfpad` | de Shopify-fake, `shopify.ts`, `stockSync.ts` |

**De fake werkt op fetch-niveau, niet op moduleniveau.** Zo draait de echte client mee —
inclusief authenticatie, tokenvernieuwing en foutafhandeling. Een mock van de module zelf
zou juist die code overslaan, en dat is precies de code die nergens getest was. De fake
weigert elk verzoek naar een andere host dan de verzonnen testwinkel: een echte aanroep
laat de test falen in plaats van er stil doorheen te glippen.

Wat er nu bewezen is voor `stockSync.ts`: alleen de Spanje-locatie wordt geraakt en
Kampenhout en ShopWeDo blijven staan; de dubbele poort (`live` én `ENABLE_STOCK_WRITE`,
en een andere waarde dan `"true"` telt niet); geen write bij een onbetrouwbare bron, bij
`próximamente`, bij een niet ondubbelzinnig gekoppelde maat of wanneer de tweede
bronmeting afwijkt; compare-and-swap die écht weigert als iemand er tussendoor schreef;
alarm wanneer de na-verificatie niet klopt; herhaalbaarheid; en een circuit breaker die
de hele ronde afbreekt zonder te schrijven.

`startStockSyncLoop()` blijft bewust ongetest: die start een echte tijdlijn en bewijst
weinig. De functie die hij aanroept is wel gedekt.

### De verboden-commandopoort

De afspraak "alleen veilige verificatie" staat niet alleen in de configuratie maar in de
**uitvoerder zelf** (`verify.assert_safe_checks`). Er is geen codepad waarlangs een
verboden commando alsnog gedraaid kan worden, ook niet met een gewijzigde `project.yaml`.

Geweigerd: `sync`, `daily`, `scan:*`, `import:*`, `setup:*`, `seed`, `migrate`,
`discover:*`, `flag:*`, `publish`, `deploy`, `release`, elke `--live`/`--push`/`--apply`-vlag,
`ENABLE_STOCK_WRITE=true`, `STOCK_SYNC_UP_ENABLED=true`, rechtstreekse
`myshopify.com`-aanroepen en `curl`/`wget` vanuit een check. Toegestaan blijven `test`,
`typecheck`, `lint` en `build`. Een project met een verboden check kan niet eens
toegevoegd worden.

### Openstaande beslissingen

De twee pricing-bevindingen zijn **niet** gewijzigd en staan vastgelegd in
[`openstaande-beslissingen-padelmq-pro.md`](openstaande-beslissingen-padelmq-pro.md),
met het commando om ze als geparkeerde vraag in de wachtrij te zetten zodra de datamap is
ingericht (`orchestrator question-add`).

---

## 16d. Voice Interaction — architectuur (P2)

### Het uitgangspunt

Spraak is **geen aparte werkstroom, maar een kanaal**. Alles wat bepaalt of een antwoord
voldoende is, staat in één machine (`answer_session.py`); GitHub, e-mail en spraak zijn
transportlagen eromheen. Daarom hoeft er niets herbouwd te worden wanneer spraak erbij
komt — en daarom kan P2 nu ontworpen zijn zonder P0 op te houden.

```
BLOCK ─► vraag in de wachtrij ─► melding op je iPhone
            │
            ▼
      voorlezen (TTS)  ──►  jij antwoordt  ──►  transcriptie (STT)
                                                     │
                                                     ▼
                                    ┌────────────────────────────────┐
                                    │  ONDUBBELZINNIGHEIDSPOORT      │
                                    └───┬──────────┬──────────┬──────┘
                            eenduidig   │   twijfel│          │ weet ik niet
                                        ▼          ▼          ▼
                              "ik leg vast: …   één ver-   BLOCK blijft,
                               klopt dat?"      duidelijking  geen gok
                                        │          │
                                        ▼          ▼
                                   ja ─► beslissing vastgelegd
                                         taken hervatten
```

### De poort — deterministisch waar het kan

Volgorde, en elke stap kan alleen afwijzen, nooit aanvullen:

| # | Controle | Bij afwijzing |
|---|---|---|
| 1 | Leeg of te kort antwoord | herhalen |
| 2 | "Weet ik niet / later" | BLOCK blijft staan, geen doorvraag |
| 3 | Transcriptiezekerheid onder 0,75 | herhalen, langzamer |
| 4 | **Heeft de vraag opties?** Koppel het antwoord er deterministisch aan. Precies één treffer = eenduidig; nul of meer dan één = doorvragen | doorvragen met de opties erbij |
| 5 | Open vraag: een lezer geeft `{lezing, eenduidig, alternatieven, ontbrekend}` terug. Ontbrekend niet leeg, of meer dan één lezing = doorvragen | doorvragen |

Stap 4 verdient toelichting: woorden die in **alle** opties voorkomen tellen niet mee.
Bij "inclusief btw" tegenover "exclusief btw" is "btw" betekenisloos; alleen "inclusief"
of "exclusief" beslist. En leestekens worden genormaliseerd, anders zou "inclusief of
eigenlijk exclusief," als eenduidig doorgaan. Dat is geen detail: het is precies het
geval waarin een systeem jouw twijfel als beslissing zou noteren.

### Het gesprek

Maximaal één verduidelijking, zoals gevraagd: vraag → antwoord → eventueel één
verduidelijking → antwoord → bevestiging → klaar. Daarna blijft de BLOCK staan. Een
correctie tijdens de bevestiging ("nee, exclusief") gaat opnieuw door de poort en wordt
**nooit samengevoegd** met het vorige antwoord.

De beslissing wordt pas `bevestigd` in de kennisbasis nadat jij "ja" hebt gezegd op de
terugkoppeling. Dat is hetzelfde punt waar GitHub- en opdrachtregelantwoorden uitkomen:
`record_human_decision`, het enige plek waar de status `bevestigd` ontstaat.

### Audit spoor

Elke beurt wordt vastgelegd in `answer_turns`: richting (gevraagd / geantwoord /
verduidelijking / bevestiging / afgesloten), kanaal, tekst, transcriptiezekerheid, reden,
tijdstip — gekoppeld aan sessie, vraag, taak en project. De oorspronkelijke vraag, jouw
gesproken antwoord, de eventuele verduidelijking en de uiteindelijke beslissing staan dus
alle vier terug te lezen.

### Het transport — twee routes, één aanbeveling

Het transport zit bewust **niet** in de kern. Het praat met precies twee handelingen:
`next_question()` en `submit(session_id, transcript, confidence)`.

| Route | Werking | Voor | Tegen |
|---|---|---|---|
| **Apple Shortcut** (aanbevolen) | Een Shortcut haalt de vraag op, spreekt hem uit met *Speak Text*, neemt je antwoord op met *Dictate Text*, en stuurt dat terug. Start met "Hey Siri" — handsfree met AirPods, geen app nodig. | Snelst te bouwen, geen App Store, werkt met je AirPods | *Dictate Text* geeft geen zekerheidsscore terug; controle 3 vervalt dan en de poort leunt zwaarder op de bevestigingsstap |
| **Telegram-spraakbericht** | Je spreekt een spraakbericht in; de orkestrator transcribeert het en antwoordt met tekst of audio | Geeft wél audio en een zekerheidsscore; werkt overal | Minder handsfree: je moet de app openen |
| *Eigen iOS-app* | — | — | **Afgewezen voor V1**: weken werk voor iets dat een Shortcut ook doet |

**Het eindpunt is gebouwd.** `orchestrator voice-serve` draait twee routes op de
standaardbibliotheek — geen webframework voor twee handelingen:

| | |
|---|---|
| `GET /voice/next[?project=…]` | de oudste openstaande blokkade over alle projecten heen |
| `POST /voice/answer` | `{sessie, transcript, zekerheid?}` → wat er nu gezegd moet worden |

Beide met de kop `X-Orch-Token`. Zonder deugdelijk token (minstens 24 tekens) start de
dienst niet; het token wordt in constante tijd vergeleken en staat nooit in een URL. De
dienst luistert standaard alleen op localhost en het aantal verzoeken is begrensd. Een
sessie draagt zelf welk project erbij hoort, dus een antwoord kan niet bij het verkeerde
project belanden — dat wordt opgezocht, niet geraden.

De Shortcut-handleiding staat in [`spraak-shortcut.md`](../spraak-shortcut.md), inclusief
de eerlijke kanttekening dat *Tekst dicteren* geen zekerheidsscore teruggeeft.

Wat nog open staat voor P2: de keuze voor een transcriptiedienst als je die score wél
wilt.

### Veiligheid

- **Geheimen worden nooit voorgelezen.** De vraagtekst gaat door dezelfde redactie als
  alles wat de machine verlaat — getest.
- Het spraakeindpunt is een inkomend oppervlak op je VPS. Het token heeft hetzelfde
  gewicht als je GitHub-token: wie het heeft, kan beslissingen namens jou vastleggen.
- Alleen `BLOCK`-vragen worden voorgelezen. Geparkeerde vragen blijven in het dagrapport;
  die hoef je niet in je oor.

---

## 17. Meetplan

| Meetpunt | Wat het aantoont |
|---|---|
| Doorlooptijd per taak | De kernbelofte |
| Menselijke interventies per taak | Of het knip- en plakwerk echt weg is |
| **Verdeling AUTO / PARK / BLOCK** | Of de kennisbasis rijk genoeg is; veel PARK = kennisbasis vullen |
| **Aandeel geïmporteerde items dat `bevestigd` wordt** | Of de ChatGPT-import zijn moeite waard was (§6.3) |
| **Onterechte AUTO's die jij achteraf corrigeert** | **De belangrijkste veiligheidsmeting.** Boven nul → citatieplicht aanscherpen |
| Onderbrekingen buiten het dagrapport | Of het bundelen werkt |
| Kosten per afgeronde taak, per project, per model | Of het economisch klopt (B1) |
| Aandeel taken dat groen wordt zonder reviewronde | Wat de beoordelaarsrol toevoegt |
| Aandeel voorgestelde alternatieven dat jij overneemt | Of de verplichte tegenspraak waarde levert (§9) |

Per taak levert `orchestrator report <project> <taak-id>` bovendien het volledige
runrapport met de twaalf afgesproken punten, waaronder — punt 4 — precies welke
kennisitems met welke status aan de reviewer beschikbaar waren, met een sha256 van de
exacte context. Dat is het verschil tussen "de reviewer had context" en aantoonbaar
wéten waarop een automatisch antwoord gebaseerd kon zijn.

---

## 18. Bronnen

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

*B5 is het enige dat nog ontbreekt om V1 op jouw echte project te richten.*
