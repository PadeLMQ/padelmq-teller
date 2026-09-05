# Openstaande beslissingen — pilot `PadeLMQ/padelmq-pro`

Bevindingen uit de codebeoordeling die **niet** zijn gewijzigd. Het zijn
beslissingen, geen bugs die een model even oplost. Ze staan hier zodat ze niet
verdwijnen, en ze zijn met één commando in de wachtrij van de orkestrator te
zetten zodra de datamap is ingericht.

> Dit bestand bevat **geen** businessregels, bedragen, marges of geheimen —
> alleen waarnemingen over het gedrag van de code. De echte kennisbasis staat
> buiten git, in `ORCH_DATA_DIR`.

---

## OB-1 · De `.99`-afronding verlaagt ook ronde bedragen

**Waar:** `src/lib/repricing.ts`, `roundToCharm`.

Een concurrent op €90,00 leidt tot een doelprijs van €89,99, niet €90,00.
`roundToCharm(90)` geeft 89,99 omdat 90 niet ≥ 90,99 is. Hetzelfde geldt voor
elke ronde prijs: €10 wordt €9,99, €70 wordt €69,99.

**Vraag:** is dat bedoeld? Bij `match_lowest` betekent het dat je nooit exact
gelijk staat met de laagste concurrent, maar altijd een cent eronder.

**Status:** vastgelegd in `tests/repricing.test.ts`, gedrag ongewijzigd.

Registreren:

```
orchestrator question-add padelmq-pro \
  "Mag de .99-afronding ook ronde concurrentprijzen verlagen? Een concurrent op 90,00 wordt nu 89,99, ook bij strategie match_lowest." \
  --outcome park --category prijs \
  --option "ja, altijd een cent onder de laagste" \
  --option "nee, bij een rond bedrag exact gelijk blijven" \
  --why "raakt elke herprijzing; nu vastgelegd in een test, niet gewijzigd"
```

---

## OB-2 · De wijzigingsdrempel vergelijkt onafgeronde getallen

**Waar:** `src/lib/repricing.ts`, `computeReprice`.

```js
const changed = currentPrice == null || Math.abs(target - currentPrice) >= 0.01;
```

Voor `target = 79.99` en `currentPrice = 79.98` levert dat
`0.00999999999999801` op — net onder de drempel. Een verschil van precies één
cent wordt daardoor niet gezien. Commercieel verwaarloosbaar, maar de drempel is
niet wat hij lijkt, en het gedrag verschilt per bedrag.

**Voorstel (blijft staan tot jij beslist):** vergelijk geldbedragen en drempels
in **hele centen**, bijvoorbeeld
`Math.round(target * 100) !== Math.round(currentPrice * 100)`. Dat maakt de
drempel exact en haalt de drijvendekommaruis eruit.

**Status:** vastgelegd in `tests/repricing.test.ts` als het huidige gedrag,
inclusief het voorstel in commentaar. Niet gewijzigd.

Registreren:

```
orchestrator question-add padelmq-pro \
  "Mogen geldbedragen en de wijzigingsdrempel in hele centen vergeleken worden in plaats van in drijvendekommagetallen?" \
  --outcome park --category prijs \
  --option "ja, Math.round(x * 100) vergelijken" \
  --option "nee, huidige gedrag houden" \
  --proposed "ja, in hele centen" \
  --why "nu wordt een verschil van precies een cent niet gezien"
```

---

## Niet-beslissingen — wel het vermelden waard

**`startStockSyncLoop()` blijft ongetest.** Die start een `setInterval` met een
echte tijdlijn; hem aanroepen in een testsuite levert een draaiende
achtergrondtaak op en bewijst weinig. De functie die hij aanroept, `runStockSync`,
is wel gedekt.

**Een 200 met onleesbare JSON leidt tot een `TypeError`, niet tot een nette
API-fout.** In `src/lib/shopify.ts` vangt `res.json().catch(() => ({}))` de
ontleedfout af, waarna `json.data` `undefined` is en de aanroeper struikelt over
een ontbrekend veld. Het gedrag is **veilig** — er wordt niets geschreven en er
wordt geworpen — maar de melding is verwarrend. Vastgelegd in
`tests/shopify.test.ts`. Opruimen kan later; het is geen risico.

---

## P-1 · `dateShort()` toonde geen jaartal — **BESLIST, opgelost**

**Waar:** `src/lib/format.ts`, `dateShort`.

Zonder jaartal renderden `02/01/2019` en `02/01/2026` allebei als
`02/01, 08:05`. Een oude regel was daardoor niet van een verse te
onderscheiden.

**Beslissing (P0, goedgekeurd):** binnen het huidige jaar blijft het jaartal
weg, want daar is het ruis. Bij een datum uit een ander jaar wordt het jaartal
getoond: `02/01/2019, 08:05`.

**Status:** geïmplementeerd en getest in `tests/format.test.ts`, PR #3.
Dekking `format.ts` 0% → 100%. Geen betaalde AI-aanroep gebruikt.

---

## P-2 · Geen ESLint-configuratie — **PARK**

**Waar:** de repository als geheel.

`npm run lint` draait `next lint`, maar er staat geen ESLint-configuratie in de
repo en `eslint` staat niet bij de dependencies. Het commando vraagt interactief
om een setup en eindigt op exit 1.

Geverifieerd op onaangeraakte `main`: **identieke fout**. Dit is dus een
bestaande projectbrede configuratiekeuze en geen defect dat door de pilot is
veroorzaakt.

**Waarom geparkeerd:** welke configuratie (`strict` of `base`) en welke
regelset er komt, bepaalt hoeveel bestaande code er in één klap rood kleurt.
Dat is een keuze van de eigenaar, niet van een model.

**Gevolg zolang dit open staat:** `lint` kan nooit groen zijn. Zet het niet als
harde check aan in de orkestratorconfiguratie van dit project, anders faalt elke
run op een reden die niets met de taak te maken heeft.

---

## P-3 · `gpt-5.6-terra` is een niet-gedateerde alias — **PARK, na P0**

**Waar:** de kostenconfiguratie van de orkestrator, niet de pilotrepo.

In de modellenlijst hebben oudere modellen een gedateerde snapshot
(`gpt-5.4-2026-03-05`, `gpt-5.5-2026-04-23`). `gpt-5.6-terra` heeft die niet en
is dus vermoedelijk een alias die naar een nieuwe onderliggende versie kan
verschuiven.

**Het risico:** de tarieven staan statisch in de omgeving
(`ORCH_REVIEWER_PRICE_IN` en verwanten). Verlegt de aanbieder de alias en
wijzigen de tarieven mee, dan blijft de boekhouding stilzwijgend rekenen met
verouderde bedragen. Er is niets dat dat signaleert.

**Nog niet opgelost, bewust.** Een eenvoudige fail-safe hoort hier: bijvoorbeeld
het modelantwoord vergelijken met het model dat we dachten aan te roepen, en de
tarieven van een houdbaarheidsdatum voorzien. Dat ontwerp komt na P0 en mag de
hoofdroute niet blokkeren.
