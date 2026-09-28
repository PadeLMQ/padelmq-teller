# PADELMQ BRAIN · FAST TRACK V1 · SPRINT 1-PLAN

**Datum: 28 september 2026 · Status: ter goedkeuring vóór bouw · Sprintduur: 3 weken**

Dit plan verwerkt de 18 aanscherpingen op het masterplan. De kern van de wijzigingen: twee parallelle trajecten (bouwen en leren), een Conversation Importer vanaf dag één, de regel "oude gesprekken zijn geen actuele waarheid", een severity-model dat releases blokkeert, een geversioneerde Golden Set, een Training Lab dat zelf vragen genereert, een Knowledge Gap Queue, minimal pairs voor consistentie, en de Copilot als eerste dagelijkse interface. Geen avatar. Geen operationele writers.

---

## 0. Twee beslissingen die dit plan afwijkend maakt van het masterplan

**0.1 SQLite in plaats van Postgres voor Sprint 1.** Eén operator, lage schrijfvolumes, en het patroon (`getDb()`-singleton, WAL, `CREATE TABLE IF NOT EXISTS` + `addColumn()`) is in Master en de Product Engine bewezen. De Engine heeft bovendien al een dual-dialect schema-in-code met Postgres-DDL-generatie; dat patroon nemen we over, zodat de overstap naar Postgres later een configuratiekeuze is (`DB_DIALECT=postgres`) en geen herbouw. Reden: nul infra-afhankelijkheid en dezelfde mentale modellen als de rest van PadeLMQ.

**0.2 De nieuwe repo kon ik niet aanmaken.** `POST /orgs/PadeLMQ/repos` geeft 404 via deze koppeling (geen org-rechten). Mathias maakt `PadeLMQ/padelmq-brain` (private) aan en koppelt hem; tot dan bouw ik op een aparte, losstaande branch die één-op-één naar die repo te pushen is. Belangrijk: de map `docs/ai-cx` staat nu in `padelmq-teller`, en die repo is **publiek** (GitHub Pages). Het masterplan en dit sprintplan zijn dus publiek leesbaar. Advies: verplaats `docs/ai-cx` naar `padelmq-brain` zodra die bestaat en verwijder ze uit de teller-repo.

---

## 1. Trajecten en sprintdoel

| Traject | Sprint 1-doel | Wat er nadrukkelijk NIET gebeurt |
|---|---|---|
| **A · Bouwen** | De service staat, de datamodellen bestaan, de adapters lezen (of zeggen eerlijk ONBEKEND), de Copilot toont een dossier per ordernummer, de importer slikt bestanden, het Training Lab genereert vragen en ondervraagt Mathias, de Knowledge Gap Queue werkt, elke AI-call is geaudit met kosten, de autonomiepoort en het severity-model staan in code met tests | geen klantgerichte UI live, geen verzending van antwoorden, geen enkele write naar Shopify/Master/onFact/tracking |
| **B · Leren en meten** | Historische gesprekken worden geïmporteerd, gepseudonimiseerd, geclassificeerd; Golden Set v1 groeit uit geïmporteerde + gegenereerde cases; eerste eval-run draait als poort | geen enkel historisch gesprek wordt als actuele waarheid gebruikt |

Definitie van "klaar" staat in §17.

## 2. Repo en service

- **Repo**: `PadeLMQ/padelmq-brain` (private). Nederlands in proza, commentaar, commits en UI; Engelse identifiers in het domeinmodel (zelfde afspraak als de Engine).
- **Stack**: Next.js 14 App Router (`runtime = "nodejs"`), TypeScript strict, Tailwind, `better-sqlite3`, zod, vitest, Playwright. Node 20. Railway met volume op `/app/data`.
- **Zone**: `basePath: "/brain"`; Master krijgt (later, één regel in `next.config.mjs`) een rewrite `/brain/*` → deze service, zoals `/product-engine/*`. Login = Master-sessie (gedeeld `SESSION_SECRET`, HMAC-cookie `padelmq_session`), letterlijk het `auth.ts`-patroon van de Engine.
- **Eigen Shopify-app** ("PadeLMQ Brain", custom app, client credentials): scopes `read_orders`, `read_fulfillments`, `read_customers`, `read_products`, `read_inventory`, `read_locations`. Geen enkele `write_*`.
- **Processen**: geen achtergrondlussen in Sprint 1. Eval-runs en imports zijn expliciet gestart (UI-knop of `npm run`), nooit cron.

### 2.1 Mappenstructuur

```
padelmq-brain/
  CLAUDE.md                     spelregels (fail-closed, geen writers, één feit één bron)
  src/app/
    copilot/                    dossier, wachtrij, training, hiaten, policy, golden set, imports, eval, kosten
    api/
      dossier/[ord]/            GET  dossier (read-only, sessie)
      copilot/concept/          POST concept-antwoord (sessie)
      copilot/beslissing/       POST approve|edit|takeover (sessie; verzendt NIET in Sprint 1)
      import/                   POST bestand(en) (sessie)
      import/[batch]/           GET status; POST normaliseren
      golden/                   GET/POST cases; POST export; POST import
      eval/                     POST run; GET resultaten
      lab/genereer/             POST varianten|minimal-pairs|misleidend|onvolledig|samengesteld|tegenstrijdig
      lab/training/             POST start|antwoord (Training Mode)
      hiaten/                   GET queue; POST antwoord JA|NEE|AANPASSEN|UITZONDERING
      policy/                   GET/POST documenten en versies
      regels/                   GET/POST adviesregels en versies
      intenties/                GET catalogus; POST niveau-wijziging (GO-log)
      rem/                      GET/POST vrij|pauze|stop
      gezondheid/               GET (health-token)
  src/lib/
    db.ts, schema/tabellen.ts   schema-in-code, dual-dialect
    auth.ts                     Master-SSO + machine-secret
    ai/denker.ts                provider-agnostische LLM-wrapper met audit + kosten
    ai/modellen.ts              taak → model-mapping, prijstabel
    feiten/                     Fact Brain-interface + bronnen (engine, metafields, master)
    advies/                     Advice Brain-interface, delta-regels, regelset
    policy/                     Policy Store
    operationeel/               adapters: shopify, master, tracking, factuur
    dossier/                    dossierbouwer per ORD
    intenties/                  catalogus, router, ontleding van samengestelde vragen
    autonomie/                  poort, niveaus, GO-log
    severity/                   fouttaxonomie, release-blokkade
    importer/                   parsers, normalisatie, pseudonimisering, classificatie
    golden/                     model, versies, groepen, export
    eval/                       runner, evaluator (regels + LLM-judge), consistentie/minimal pairs
    lab/                        generator, training mode, gap-detectie
    hiaten/                     Knowledge Gap Queue
    audit/                      ai_calls, kosten, incidenten
  integraties/
    master/klant-route.patch    voorstel: GET /api/klant in padelmq-pro (niet toegepast)
    engine/feiten-route.patch   voorstel: GET /api/feiten/[gid] in product-engine (niet toegepast)
    tracking/order-route.patch  voorstel: GET /api/order/<ORD> in padelmq-tracking (niet toegepast)
  eval/                         golden set als JSON (gepseudonimiseerd), adversariële set
  tests/                        vitest, incl. structurele broncodetests
  e2e/                          Playwright: copilot-flows tegen wegwerp-DB
```

## 3. Componenten (overzicht)

| # | Component | Doel in Sprint 1 | Traject |
|---|---|---|---|
| C1 | Datalaag + schema | alle tabellen van §4, migratiepatroon, dual-dialect | A |
| C2 | Auth + secrets | Master-SSO, machine-secrets, health-token | A |
| C3 | AI-wrapper (`denker`) | één ingang voor elk LLM-gebruik: provider, model per taak, tool-calling, audit, kosten, retries, kill switch | A |
| C4 | Fact Brain-interface | `haalFeiten(gid)`, `haalFeit(gid, veld)` met bronketen en UNKNOWN | A |
| C5 | Advice Brain-interface | regelset (geversioneerd), delta-calculator, DNA-lezing | A |
| C6 | Policy Store | documenten + versies + geldigheid + taal; `haalPolicy()` | A |
| C7 | Operationele adapters | Shopify orders/fulfilments/klant; Master klant-API; tracking; factuurstatus | A |
| C8 | Dossierbouwer | één ORD → volledig dossier (§9) | A |
| C9 | Intentiecatalogus + router + ontleding | 62 intenties uit het masterplan als data; router; samengestelde vraag → deelintenties | A |
| C10 | Autonomiepoort + GO-log | niveaus per intentie, poort vóór elke actie, degradatie | A |
| C11 | Severity-model | fouttaxonomie, incidenten, release-blokkade in eval | A |
| C12 | Conversation Importer | upload → parse → normaliseer → pseudonimiseer → classificeer | B |
| C13 | Golden Set | model, groepen, versies, export/import | B |
| C14 | Eval-runner | run per versie (model/prompt/regelset/toolflow), scoring per severity, consistentie | B |
| C15 | Training Lab | generator (6 soorten), Training Mode, ontleding van Mathias' antwoord | B |
| C16 | Knowledge Gap Queue | detectie + gerichte vragen + JA/NEE/AANPASSEN/UITZONDERING → regelversie | B |
| C17 | Copilot-UI | dossier, wachtrij, concept, beslissing (zonder verzending), training, hiaten, policy, golden, imports, eval, kosten | A |
| C18 | Audit + kosten | `ai_calls`, dagtotalen, per taak, per gesprek | A |
| C19 | Tests | unit, structureel, eval als poort, e2e | A |

## 4. Database-objecten (SQLite, schema-in-code)

Conventie: `id INTEGER PRIMARY KEY AUTOINCREMENT`, `created_at TEXT DEFAULT (datetime('now'))`, JSON in `*_json`-kolommen (gevalideerd met zod bij lezen én schrijven). Persoonsdata alleen waar expliciet vermeld.

### 4.1 Gesprekken en Copilot
```sql
CREATE TABLE gesprekken (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  kanaal TEXT NOT NULL CHECK (kanaal IN ('copilot','site','email','whatsapp','training','eval','import')),
  klant_ref TEXT,                 -- gehasht e-mail of shopify customer gid; NULL voor anoniem
  order_ref TEXT,                 -- 'ORD89162026' of NULL
  taal TEXT,                      -- 'nl'|'fr'|'en'|NULL
  status TEXT NOT NULL DEFAULT 'open',   -- open|wacht_op_mathias|afgerond|geescaleerd
  autonomie_niveau TEXT,          -- hoogste niveau dat in dit gesprek nodig was
  created_at TEXT DEFAULT (datetime('now')),
  updated_at TEXT
);
CREATE TABLE beurten (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  gesprek_id INTEGER NOT NULL REFERENCES gesprekken(id),
  rol TEXT NOT NULL CHECK (rol IN ('klant','ai','mathias','systeem','tool')),
  tekst TEXT,
  objecten_json TEXT,             -- antwoordobjecten (LeverBelofte, DeltaCard, OrderTijdlijn, ...)
  intenties_json TEXT,            -- [{intentie, zekerheid, deelvraag}]
  bronnen_json TEXT,              -- [{bron, sleutel, gemeten_op, versheid_ok}]
  onbekend_json TEXT,             -- [{veld, reden}]  -> UNKNOWN is een antwoord
  ai_call_id INTEGER,             -- REFERENCES ai_calls(id)
  created_at TEXT DEFAULT (datetime('now'))
);
CREATE TABLE beslissingen (        -- APPROVE / EDIT / TAKE OVER op een concept
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  gesprek_id INTEGER NOT NULL REFERENCES gesprekken(id),
  concept_beurt_id INTEGER NOT NULL REFERENCES beurten(id),
  beslissing TEXT NOT NULL CHECK (beslissing IN ('approve','edit','takeover','afwijzen')),
  eindtekst TEXT,                 -- wat Mathias werkelijk zou versturen
  diff_json TEXT,                 -- gestructureerd verschil concept ↔ eindtekst
  reden TEXT,
  door TEXT NOT NULL DEFAULT 'mathias',
  verzonden INTEGER NOT NULL DEFAULT 0,   -- Sprint 1: altijd 0 (geen verzending)
  created_at TEXT DEFAULT (datetime('now'))
);
```

### 4.2 Import en historiek (traject B)
```sql
CREATE TABLE import_batches (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  bron TEXT NOT NULL,             -- tidio|chatgpt|claude|email|whatsapp|tekst|json|csv|onbekend
  bestandsnaam TEXT, bytes INTEGER, sha256 TEXT UNIQUE,
  status TEXT NOT NULL DEFAULT 'geupload',  -- geupload|geparsed|genormaliseerd|geclassificeerd|fout
  fout TEXT, documenten INTEGER DEFAULT 0, gesprekken INTEGER DEFAULT 0,
  created_at TEXT DEFAULT (datetime('now'))
);
CREATE TABLE import_documenten (   -- ruwe eenheid uit het bestand, ongewijzigd bewaard
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  batch_id INTEGER NOT NULL REFERENCES import_batches(id),
  volgnummer INTEGER NOT NULL,
  ruwe_tekst TEXT NOT NULL,
  ruwe_meta_json TEXT,            -- alles wat de parser vond (timestamps, deelnemers, onderwerp)
  parser TEXT NOT NULL, parser_versie TEXT NOT NULL
);
CREATE TABLE historische_gesprekken (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  document_id INTEGER NOT NULL REFERENCES import_documenten(id),
  bron TEXT NOT NULL,
  datum TEXT,                     -- ISO; NULL als onbekend (dan nooit als recent behandeld)
  taal TEXT,
  klantvraag TEXT NOT NULL,
  antwoord TEXT,
  antwoord_door TEXT,             -- mathias|ai_chatgpt|ai_claude|ai_tidio|onbekend
  correctie_mathias TEXT,         -- als een AI-antwoord door Mathias is gecorrigeerd: de correctie
  intentie_json TEXT,             -- [{intentie, zekerheid}] uit classificatie
  producten_json TEXT,            -- [{genoemd, gid?, zekerheid}]
  order_ref TEXT,
  kwaliteit TEXT NOT NULL DEFAULT 'ongekeurd', -- ongekeurd|goed|matig|fout|niet_bruikbaar
  historische_context TEXT,       -- vrije notitie: "beleid toen: 14 dagen", "Tienda-levering toen 5 dagen"
  leerbaar_json TEXT,             -- {toon, redeneerpatroon, vervolgvraag, nuance, afraden, escalatie, formuleringen}
  NIET_ACTUEEL_json TEXT,         -- {prijs, voorraad, levertijd, retour, garantie, test, korting, specs} die in het gesprek staan en NOOIT als waarheid mogen dienen
  pseudoniem INTEGER NOT NULL DEFAULT 0,  -- 1 = persoonsdata vervangen; alleen dan bruikbaar voor eval/golden
  created_at TEXT DEFAULT (datetime('now'))
);
CREATE INDEX hg_intentie ON historische_gesprekken(kwaliteit, pseudoniem);
```
De kolom `NIET_ACTUEEL_json` is bewust luid genoemd: elke lezer van dit gesprek ziet dat die waarden verlopen zijn. De structurele test §14.2 bewaakt dat geen enkele module deze kolom als bron voor een antwoordobject gebruikt.

### 4.3 Intenties en autonomie
```sql
CREATE TABLE intenties (
  sleutel TEXT PRIMARY KEY,       -- bv. 'advies.upgrade_van_huidig'
  groep TEXT NOT NULL,            -- advies|beschikbaarheid|order|retour|intern
  omschrijving TEXT NOT NULL,
  benodigde_feiten_json TEXT,     -- ['shape','core_hardness',...]
  bronnen_json TEXT,              -- ['FE','AB','MA',...]
  niveau TEXT NOT NULL DEFAULT 'human' CHECK (niveau IN ('autonomous','assisted','human')),
  niveau_sinds TEXT, niveau_versie INTEGER NOT NULL DEFAULT 1,
  severity_bij_fout TEXT NOT NULL DEFAULT 'high',
  actief INTEGER NOT NULL DEFAULT 1
);
CREATE TABLE autonomie_log (       -- elke niveau-wijziging is een GO van een mens, met bewijs
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  intentie TEXT NOT NULL REFERENCES intenties(sleutel),
  van TEXT NOT NULL, naar TEXT NOT NULL,
  reden TEXT NOT NULL, bewijs_json TEXT,   -- {eval_run_id, score, assisted_weken, ongewijzigd_pct}
  door TEXT NOT NULL, created_at TEXT DEFAULT (datetime('now'))
);
CREATE TABLE rem (stand TEXT NOT NULL CHECK (stand IN ('vrij','pauze','stop')), door TEXT, reden TEXT, sinds TEXT);
CREATE TABLE rem_log (id INTEGER PRIMARY KEY AUTOINCREMENT, van TEXT, naar TEXT, door TEXT, reden TEXT, created_at TEXT DEFAULT (datetime('now')));
```

### 4.4 Policy Store en Advice Brain
```sql
CREATE TABLE policy_documenten (
  sleutel TEXT PRIMARY KEY,       -- 'retour.termijn', 'garantie.bullpadel', 'verzending.be', 'testservice', 'afhalen.mechelen', 'btw.b2b', ...
  onderwerp TEXT NOT NULL, omschrijving TEXT
);
CREATE TABLE policy_versies (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  sleutel TEXT NOT NULL REFERENCES policy_documenten(sleutel),
  versie INTEGER NOT NULL,
  taal TEXT NOT NULL,             -- nl|fr|en
  tekst TEXT NOT NULL,            -- LETTERLIJK citeerbare tekst
  gestructureerd_json TEXT,       -- machineleesbaar: {termijn_dagen: 14, uitzonderingen: [...], wie_betaalt: ...}
  geldig_van TEXT NOT NULL, geldig_tot TEXT,
  bron_url TEXT,                  -- de Shopify-pagina of het besluit van Mathias
  status TEXT NOT NULL DEFAULT 'concept' CHECK (status IN ('concept','actief','vervallen')),
  door TEXT NOT NULL, created_at TEXT DEFAULT (datetime('now')),
  UNIQUE (sleutel, versie, taal)
);
CREATE TABLE adviesregels (
  sleutel TEXT PRIMARY KEY,       -- 'elleboog.zachte_kern', 'gewicht.dropship_geen_selectie', ...
  groep TEXT NOT NULL,            -- speler|delta|tijdlijn|commercieel|escalatie|toon
  omschrijving TEXT NOT NULL
);
CREATE TABLE adviesregel_versies (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  sleutel TEXT NOT NULL REFERENCES adviesregels(sleutel),
  versie INTEGER NOT NULL,
  voorwaarde_json TEXT NOT NULL,  -- {als: {elleboog: true}, ...}
  gevolg_json TEXT NOT NULL,      -- {voorkeur: {core_hardness: ['zacht'], balance: ['laag','medium']}, max_gewicht: 370, disclaimer: 'medisch'}
  uitleg_mathias TEXT,            -- in zijn woorden
  herkomst TEXT NOT NULL,         -- 'training'|'hiaat'|'import'|'handmatig'
  herkomst_ref TEXT,              -- id van trainingssessie / hiaat / gesprek
  status TEXT NOT NULL DEFAULT 'kandidaat' CHECK (status IN ('kandidaat','bevestigd','uitzondering','verworpen','vervallen')),
  zekerheid REAL,                 -- lessenpatroon: drempel 0,65 voor 'bevestigd' zonder expliciete GO bestaat NIET; bevestigd = alleen door Mathias
  door TEXT NOT NULL, created_at TEXT DEFAULT (datetime('now')),
  UNIQUE (sleutel, versie)
);
```

### 4.5 Golden Set en evaluatie
```sql
CREATE TABLE golden_set_versies (id INTEGER PRIMARY KEY AUTOINCREMENT, label TEXT NOT NULL, omschrijving TEXT, bevroren INTEGER DEFAULT 0, created_at TEXT DEFAULT (datetime('now')));
CREATE TABLE golden_cases (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  set_versie_id INTEGER NOT NULL REFERENCES golden_set_versies(id),
  groep TEXT NOT NULL,            -- productfeiten|racketadvies|vergelijking|upgrade|gewicht|blessure|tennis_overstap|beginner|gevorderd|verzending|dropship|split_order|tracking|geleverd_niet_ontvangen|retour|garantie|factuur|btw_vies|vip|afhalen|testservice|boos|onduidelijk|onvoldoende_info|tegenstrijdig
  herkomst TEXT NOT NULL,         -- import|gegenereerd|training|incident|handmatig
  herkomst_ref TEXT,
  input_klant TEXT NOT NULL,
  context_json TEXT NOT NULL,     -- {pagina, product_gid, variant, anker, klant_profiel, order_fixture, taal, kanaal}
  intentie_json TEXT NOT NULL,    -- verwachte (deel)intenties
  benodigde_feiten_json TEXT,     -- velden die opgehaald MOETEN worden
  verplichte_bronnen_json TEXT,   -- ['FE','PO'] die geraadpleegd MOETEN zijn
  verboden_aannames_json TEXT,    -- ['premisse "18K is rond" bevestigen', 'levertijd noemen zonder LT']
  redeneerpatroon TEXT,           -- verwacht patroon in woorden
  gewenste_uitkomst_json TEXT,    -- {objecten: ['DeltaCard'], moet_bevatten: [...], mag_niet_bevatten: [...], escalatie: false}
  autonomie_verwacht TEXT NOT NULL,
  severity_bij_fout TEXT NOT NULL CHECK (severity_bij_fout IN ('critical','high','medium','low')),
  goedgekeurd_antwoord TEXT,      -- door Mathias goedgekeurd, indien beschikbaar
  fixture_json TEXT,              -- synthetische feiten/policy/order waar de case tegen draait (deterministisch)
  minimal_pair_van INTEGER REFERENCES golden_cases(id),  -- gekoppelde case die op één variabele verschilt
  variabele_verschil TEXT,        -- 'elleboog: false -> true'
  actief INTEGER DEFAULT 1, created_at TEXT DEFAULT (datetime('now'))
);
CREATE TABLE eval_runs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  set_versie_id INTEGER NOT NULL REFERENCES golden_set_versies(id),
  onder_test_json TEXT NOT NULL,  -- {model, prompt_versie, regelset_versie, policy_snapshot, toolflow_versie, code_sha}
  status TEXT NOT NULL DEFAULT 'bezig',
  totaal INTEGER, geslaagd INTEGER,
  critical INTEGER DEFAULT 0, high INTEGER DEFAULT 0, medium INTEGER DEFAULT 0, low INTEGER DEFAULT 0,
  release_geblokkeerd INTEGER NOT NULL DEFAULT 1,   -- fail-closed: 1 tot bewezen 0 critical
  kosten_eur REAL, created_at TEXT DEFAULT (datetime('now')), afgerond_op TEXT
);
CREATE TABLE eval_resultaten (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  run_id INTEGER NOT NULL REFERENCES eval_runs(id),
  case_id INTEGER NOT NULL REFERENCES golden_cases(id),
  antwoord_json TEXT,             -- wat het systeem produceerde (objecten + tekst + bronnen + onbekend)
  oordeel TEXT NOT NULL CHECK (oordeel IN ('geslaagd','gefaald','verklaard')),  -- 'verklaard' = fout, door Mathias als acceptabel verklaard met reden
  severity TEXT,                  -- alleen bij gefaald/verklaard
  redenen_json TEXT,              -- [{regel:'verplichte_bron_niet_geraadpleegd', detail:'FE'}, {regel:'premisse_bevestigd'}]
  judge_json TEXT,                -- LLM-judge-uitkomst met scores per dimensie (feit, order, hallucinatie, escalatie, advies, toon, bondig, vragen, policy, commercieel)
  consistentie_json TEXT,         -- voor minimal pairs: {partner_case, verschil_verwacht: true, verschil_gezien: true, ongewenste_inconsistentie: false}
  verklaring TEXT, verklaard_door TEXT, ai_call_ids_json TEXT
);
```

### 4.6 Training Lab en hiaten
```sql
CREATE TABLE lab_generaties (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  soort TEXT NOT NULL CHECK (soort IN ('herformulering','onvolledig','samengesteld','misleidend','randgeval','tegenstrijdig','minimal_pair')),
  basis_json TEXT NOT NULL,       -- waaruit gegenereerd: intentie, product(en), regel, policy, historisch gesprek, incident
  resultaat_json TEXT NOT NULL,   -- de gegenereerde vragen/cases (kandidaten)
  overgenomen_case_ids_json TEXT, -- welke kandidaten Mathias in de Golden Set zette
  ai_call_id INTEGER, created_at TEXT DEFAULT (datetime('now'))
);
CREATE TABLE training_sessies (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  modus TEXT NOT NULL CHECK (modus IN ('train_mij','test_ai')),
  groep TEXT, status TEXT NOT NULL DEFAULT 'open',
  created_at TEXT DEFAULT (datetime('now')), afgerond_op TEXT
);
CREATE TABLE training_beurten (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  sessie_id INTEGER NOT NULL REFERENCES training_sessies(id),
  volgnummer INTEGER NOT NULL,
  klantvraag TEXT NOT NULL,       -- gesteld aan Mathias (train_mij) of aan de AI (test_ai)
  context_json TEXT,
  antwoord_mathias TEXT,
  antwoord_ai TEXT,
  ontleding_json TEXT,            -- {feiten_gebruikt, adviesregel, afweging, vragen_bewust_niet_gesteld, doorslaggevend, herbruikbaar: 'regel'|'testcase'|'geen', conflict_met: [regelsleutels]}
  vervolgvragen_json TEXT,        -- gerichte vragen van de AI aan Mathias
  antwoorden_vervolg_json TEXT,
  uitkomst_json TEXT,             -- {golden_case_id?, adviesregel_versie_id?, hiaat_id?}
  ai_call_ids_json TEXT, created_at TEXT DEFAULT (datetime('now'))
);
CREATE TABLE hiaten (              -- Knowledge Gap Queue
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  soort TEXT NOT NULL CHECK (soort IN ('regelconflict','ontbrekende_productkennis','inconsistente_antwoorden','terugkerende_uitzondering','onbegrepen_keuze','procedure_niet_machineleesbaar','nieuw_vraagtype','policy_ontbreekt','feit_ontbreekt')),
  vraag TEXT NOT NULL,            -- de GERICHTE vraag aan Mathias, met cijfers ("in 7 gesprekken … in 2 …")
  hypothese TEXT,                 -- de hypothese van de AI, als die er is
  bewijs_json TEXT NOT NULL,      -- [{soort:'historisch_gesprek', id}, {soort:'golden_case', id}, ...]
  betreft_json TEXT,              -- {regel?: sleutel, intentie?: sleutel, product_gid?, policy?: sleutel}
  prioriteit INTEGER NOT NULL DEFAULT 3,   -- 1 hoog … 5 laag; frequentie × severity
  status TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open','beantwoord','verwerkt','afgewezen')),
  antwoord TEXT CHECK (antwoord IN ('ja','nee','aanpassen','uitzondering')),
  toelichting_mathias TEXT,
  uitkomst_json TEXT,             -- {adviesregel_versie_id?, policy_versie_id?, golden_case_ids?}
  created_at TEXT DEFAULT (datetime('now')), beantwoord_op TEXT
);
```

### 4.7 Audit, kosten, incidenten
```sql
CREATE TABLE ai_calls (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  doel TEXT NOT NULL,             -- router|concept|advies|judge|generator|training|classificatie|ontleding|hiaat_detectie
  provider TEXT NOT NULL, model TEXT NOT NULL,
  gesprek_id INTEGER, eval_run_id INTEGER, sessie_ref TEXT,
  prompt_versie TEXT NOT NULL, prompt_sha TEXT NOT NULL,
  tokens_in INTEGER, tokens_out INTEGER, tokens_cache INTEGER,
  kosten_eur REAL NOT NULL,
  latency_ms INTEGER, tool_calls INTEGER DEFAULT 0,
  status TEXT NOT NULL,           -- ok|fout|geweigerd_rem|timeout
  fout TEXT,
  invoer_sha TEXT,                -- hash van de volledige invoer (geen inhoud; inhoud staat in beurten/import)
  created_at TEXT DEFAULT (datetime('now'))
);
CREATE INDEX ai_calls_dag ON ai_calls(created_at, doel);
CREATE TABLE incidenten (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  severity TEXT NOT NULL CHECK (severity IN ('critical','high','medium','low')),
  soort TEXT NOT NULL,            -- uit de taxonomie §11
  bron TEXT NOT NULL,             -- eval|copilot|training|import|productie
  ref_json TEXT NOT NULL,         -- {eval_resultaat_id?, beurt_id?, ...}
  omschrijving TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'open',  -- open|verklaard|opgelost
  verklaring TEXT, door TEXT, created_at TEXT DEFAULT (datetime('now'))
);
```

## 5. API-contracten (intern, allemaal achter Master-sessie tenzij anders vermeld)

Alle antwoorden: `{ ok: true, ... }` of `{ ok: false, fout: string, code: string }`. Alle feit-dragende velden hebben de vorm `Feit<T>`:

```ts
type Feit<T> =
  | { status: "bekend"; waarde: T; bron: string; bron_tier?: 1|2|3|4|5; gemeten_op: string | null; versheid_ok: boolean; zekerheid: number | null }
  | { status: "onbekend"; reden: string; bron_geprobeerd: string[] };
```
Er bestaat geen derde vorm. Geen `null` als "misschien".

| Endpoint | Methode | Invoer | Uitvoer (kern) |
|---|---|---|---|
| `/api/dossier/[ord]` | GET | `ord` (ORD…2026 of #1095-vorm) | `Dossier` (§9) |
| `/api/copilot/concept` | POST | `{gesprek_id?, ord?, klanttekst, kanaal}` | `{gesprek_id, beurt_id, objecten[], tekst, intenties[], bronnen[], onbekend[], autonomie: {niveau, reden}, severity_max}` |
| `/api/copilot/beslissing` | POST | `{beurt_id, beslissing, eindtekst?, reden?}` | `{beslissing_id, diff, verzonden: false}` |
| `/api/import` | POST multipart | bestanden + `bron?` | `{batch_ids[]}` |
| `/api/import/[batch]` | GET / POST `{stap: 'normaliseer'|'classificeer'|'pseudonimiseer'}` | – | `{status, documenten, gesprekken, fouten[]}` |
| `/api/golden` | GET `?groep=&versie=` / POST case / POST `{actie:'export'}` / POST `{actie:'import', json}` | – | cases / `{id}` / JSON-bestand / `{aantal}` |
| `/api/eval` | POST `{set_versie_id, onder_test: {...}}` / GET `?run=` | – | `{run_id}` / run + resultaten |
| `/api/lab/genereer` | POST `{soort, basis: {intentie?, product_gids?, regel?, policy?, historisch_id?, case_id?}, aantal}` | – | `{generatie_id, kandidaten[]}` |
| `/api/lab/training` | POST `{actie:'start', modus, groep?}` / `{actie:'antwoord', beurt_id, tekst}` / `{actie:'vervolg', beurt_id, antwoorden}` | – | `{sessie_id, beurt}` / `{ontleding, vervolgvragen}` / `{uitkomst}` |
| `/api/hiaten` | GET `?status=` / POST `{id, antwoord, toelichting}` | – | queue / `{uitkomst}` |
| `/api/policy` | GET `?sleutel=&taal=&op=` / POST versie | – | versie / `{id}` |
| `/api/regels` | GET / POST versie (status alleen door mens) | – | – |
| `/api/intenties` | GET / POST `{sleutel, naar, reden, bewijs}` | – | catalogus / `{log_id}` |
| `/api/rem` | GET / POST `{stand, reden}` | – | `{stand}` |
| `/api/gezondheid` | GET (`x-health-token`) | – | `{versie, rem, db, adapters: {master, engine, shopify, tracking}, poorten: alles 'dicht'}` |

### 5.1 Externe contracten die Sprint 1 als voorstel-patch oplevert (niet toegepast)

**Master · `GET /api/klant?gid=…&variant=…&zoek=…`** (nieuw, `src/app/api/klant/route.ts` + `src/lib/klantLezing.ts`), auth: `x-klant-lees-secret` = `KLANT_LEES_SECRET` (eigen secret, alleen deze route, patroon `tienda-lees`). Antwoord:
```json
{ "product": {"gid":"…","titel":"…","merk":"…","type":"…","status":"ACTIVE","testracket_beschikbaar":true},
  "varianten": [{"gid":"…","titel":"43","sku":"…","prijs":{"status":"bekend","waarde":259.95,"bron":"shopify:vers","gemeten_op":"…","versheid_ok":true},
                 "vip":{"status":"bekend","waarde":244.95,"bron":"shopify:symo.vip_price"},
                 "verkoopbaar":{"status":"bekend","waarde":true,"bron":"master:stock_check.beschikbaarheid=bevestigd_beschikbaar","gemeten_op":"…","versheid_ok":true},
                 "eigen_voorraad":{"status":"onbekend","reden":"dropship","bron_geprobeerd":["master:eigenVoorraad"]},
                 "locatie":{"status":"bekend","waarde":"Spanje","bron":"master:stock_check.standaardlocatie"}}],
  "tienda_stand":{"status":"bekend","waarde":"bevestigd_beschikbaar","gemeten_op":"…","versheid_ok":true,"bron":"master:tiendaStandVoorProduct"},
  "zoek": [{"gid":"…","titel":"…","score":0.91}] }
```
Alleen `leesVersePrijsEnVip`, `stock_check`, `veiligVerkoopbaar`, `eigenVoorraad`, `tiendaStandVoorProduct`, `isTestracket`, `zoekProducten`. Nooit kost, marge, concurrent. `tests/veiligheid.test.ts` blijft groen (route heeft guard).

**Product Engine · `GET /api/feiten/[shopify_product_gid]`** (nieuw), auth: `x-engine-secret`. Antwoord: `{ knowledge_object_id, categorie, velden: EffectieveWaarde[] (field, waarde, herkomst, onderbouwing, confidence, conflict), dna: {scoringVersion, dimensies, publiek}, gereedheid }`. Alleen `effectieveWaarden()`, `haalDnaProfiel()`, `naarPubliekePresentatie()`.

**Tracking · `GET /api/order/<ORD>`** (nieuw), auth: `x-tracking-secret`. Antwoord: `{ ord, zendingen: [{tienda_ref, carrier, tracking[], status, ups_status, ups_est, delivered, shipped_at, products[]}], manueel: bool, reden }` uit `mapping.json`, read-only.

Tot die patches toegepast zijn, geven de adapters `{status:"onbekend", reden:"bron niet gekoppeld"}` en toont het dossier dat expliciet. Shopify-fulfilments (met trackingnummers, geschreven door de bestaande tracking-tool) zijn in Sprint 1 de primaire trackingbron.

## 6. Read-only adapters (`src/lib/operationeel/`)

| Adapter | Bron | Functies | Auth | Cache | Schrijft |
|---|---|---|---|---|---|
| `shopifyOrders.ts` | Shopify Admin GraphQL 2025-10, eigen app | `orderOpNaam(ord)`, `ordersVanKlant(email\|gid, limiet)`; query = `ORDER_VELDEN` van de factuurmotor + `fulfillmentOrders{assignedLocation, lineItems}` + `fulfillments{trackingInfo, fulfillmentLineItems{lineItem{id}}}` + `events(first:50)` (btw-tijdlijn) | client credentials, tokencache (patroon `shopifyOrgAuth`) | geen (live) | nooit |
| `shopifyKlant.ts` | idem | `klantOpEmail(email)` → gid, orders count, tags (VIP) | idem | geen | nooit |
| `masterKlant.ts` | Master `/api/klant` | `productLezing(gid)`, `zoek(term)` | `KLANT_LEES_SECRET` | 3 min (prijs), 10 min (beschikbaarheid) | nooit |
| `engineFeiten.ts` | Engine `/api/feiten/[gid]` | `feitenVoor(gid)` | `ENGINE_ACCESS_TOKEN` | 60 min | nooit |
| `shopifyMetafields.ts` | Shopify product metafields | `metafieldsVoor(gid)`: `padelmq_engine.*` (tier 2 "engine-metafield"), `custom.*` (tier 5 "legacy, onbevestigd") | eigen app | 60 min | nooit |
| `tracking.ts` | tracking-service | `status()` (bestaand), `zendingenVoor(ord)` (na patch) | `TRACKING_SECRET` | geen | nooit; roept nooit `/sync`, `/koppel`, `/afvink` |
| `factuur.ts` | onFact API (read) | `factuurVoor(ord)` → nummer, status, datum | `ONFACT_*` | 10 min | nooit |

Elke adapter: time-out 8 s, één retry bij netwerkfout, elke uitkomst als `Feit<T>`, elke fout → `onbekend` met reden, nooit een gok. Structurele test: geen adapter importeert een module met `mutation`, `fulfillmentCreate`, `metafieldsSet`, `PUT`/`POST` naar onFact/Scrada/stockprice.

## 7. Fact Brain-interface (`src/lib/feiten/`)

```ts
export type FeitVeld = "brand"|"model"|"year"|"shape"|"weight"|"weight_range"|"balance"|"balance_point"|"thickness"|"core"|"core_hardness"|"face_material"|"frame_material"|"surface_finish"|"roughness"|"level"|"playing_style"|"sweet_spot"|"technologies"|"pro_players"|"predecessor"|"successor"|"ean"|"sku";
export type OperationeelVeld = "prijs"|"vip"|"verkoopbaar"|"eigen_voorraad"|"locatie"|"tienda_stand"|"testracket";

export async function haalFeit(gid: string, veld: FeitVeld): Promise<Feit<string|number|[number,number]|string[]>>;
export async function haalFeiten(gid: string, velden?: FeitVeld[]): Promise<Record<FeitVeld, Feit<unknown>>>;
export async function haalOperationeel(variantGid: string, veld: OperationeelVeld): Promise<Feit<unknown>>;
export async function zoekAnker(tekst: string): Promise<{ kandidaten: {gid?: string, referentie_id?: number, titel: string, score: number}[] }>;
```
Bronketen per productfeit (eerste die `bekend` geeft wint; lagere bronnen worden als `alternatief` meegegeven):
1. Engine `/api/feiten` (herkomst per veld, conflictstatus; een open kritiek conflict → `onbekend` met reden "bronconflict").
2. Metafield `padelmq_engine.spec` (alleen Engine-producten).
3. Metafield `custom.*` (vorm, gewicht, balans, kern, racket_oppervlakte, niveau_speler, type_spel, sweetspot, pro_players) → altijd `bron_tier: 5`, `zekerheid: null`, label "onbevestigd". `custom.kracht/controle/comfort` worden **nooit** gelezen.
4. `referentie_rackets` (voor ankers buiten de catalogus; Sprint 1: tabel + handmatige invoer, geen pijplijn).
5. Anders: `onbekend`.

Harde regels in code: het LLM krijgt productfeiten uitsluitend als tool-resultaat; de prompt bevat geen spec-tabellen; een antwoordobject (`DeltaCard`, `Werkbank`) accepteert alleen `Feit`-waarden, geen vrije strings; een `onbekend` veld wordt als "onbekend" gerenderd of weggelaten, nooit ingevuld. De structurele test grept prompts op spec-woorden met getallen.

## 8. Advice Brain-interface (`src/lib/advies/`)

```ts
export type Delta = { veld: FeitVeld; richting: "meer"|"minder"|"gelijk"|"onbekend"; label: string; van: Feit<unknown>; naar: Feit<unknown> };
export function berekenDeltas(anker: Record<FeitVeld, Feit<unknown>>, kandidaat: Record<FeitVeld, Feit<unknown>>): Delta[];   // deterministisch, geen LLM
export function pasRegelsToe(profiel: SpelerProfiel, kandidaten: Kandidaat[], regelset: RegelsetVersie): { voorkeuren: ..., waarschuwingen: ..., afraders: ..., toegepaste_regels: string[] };
export async function actieveRegelset(op?: string): Promise<RegelsetVersie>;   // alleen status 'bevestigd' of 'uitzondering'
export function dnaBand(dna: DnaPubliek, dimensie): "laag"|"gemiddeld"|"hoog"|null;
```
Het LLM formuleert alleen de interpretatiezinnen binnen het skelet (zelfde DNA → wat veranderde → wat je voelt → voor wie wel/niet) en krijgt daarvoor de deltas, de toegepaste regels en de DNA-banden als tool-resultaat. Regels met status `kandidaat` worden nooit toegepast, alleen getoond in het Copilot-dossier als "kandidaatregel, niet actief". Persoonlijk advies staat in de intentiecatalogus op `assisted` en blijft dat tot de eval-poort én Mathias anders beslissen.

## 9. Dossier (`src/lib/dossier/`)

`bouwDossier(ord): Promise<Dossier>` verzamelt parallel, met per bron een eigen `Feit`/status, en faalt nooit als geheel:

```ts
type Dossier = {
  ord: string; winkel: "padelmq"|"mechelen";
  klant: { naam_weergave: string; email_gehasht: string; vip: Feit<boolean>; eerdere_orders: Feit<number> };   // geen adres in het dossier tenzij 'toon_adres' expliciet
  order: { datum, betaald: Feit<boolean>, status_financieel, status_fulfilment, totaal, land, regels: [{titel, variant, sku, aantal, locatie_verwacht: Feit<string>}] };
  fulfilments: [{ id, status, aangemaakt, regels: [line_item_ids], tracking: [{nummer, carrier, url}], carrier_status: Feit<string>, eta: Feit<string> }];
  split: { is_split: boolean; nog_te_verzenden_regels: [...] };
  factuur: Feit<{nummer, status, datum}>;
  communicatie: Feit<{threads: [...]}>;            // Sprint 1: 'onbekend: Gmail nog niet gekoppeld'
  retour_garantie_context: { leverdatum: Feit<string>, retourtermijn_resterend_dagen: Feit<number>, garantie_merk: Feit<string> };  // uit Policy Store
  ontbrekend: string[];                            // alles wat onbekend is, expliciet
  waarschijnlijke_situatie: string | null;         // LLM-hypothese, gelabeld als hypothese, alleen op basis van bekende feiten
  aanbevolen_actie: string | null;
  autonomie: { niveau, reden };
  bronnen: [{bron, gemeten_op, versheid_ok}];
  onzekerheden: string[];
};
```

## 10. Intenties, router, ontleding

- De 62 intenties uit het masterplan worden geseed als data (`intenties`), met niveau `human` als default en de V1-niveaus uit de matrix als **voorstel** in een aparte seed die Mathias per intentie activeert (GO-log).
- Router: eerst deterministische signalen (ordernummerpatroon, product-gid uit context, sleutelwoorden per taal), daarna een klein model met `tool_choice` geforceerd op `classificeer_intenties` (enum van intentiesleutels, zekerheid per intentie, deelvragen). Een samengestelde vraag levert een lijst deelintenties met voor elk: het tekstfragment, de benodigde feiten, en of ze van elkaar afhangen (profiel → advies → gewicht → logistiek).
- Verwijzingen ("die", "deze", "en deze?") worden opgelost uit de gesprekscontext (laatst genoemde producten, pagina-product); lukt dat niet, dan is de enige toegestane vervolgvraag "welke bedoel je?" met de kandidaten als chips.
- Premisse-check: elke klantbewering over een feit ("18K is toch rond?") wordt als `bewering` gemarkeerd en tegen het Fact Brain getoetst vóór er geantwoord wordt; de eval bestraft een bevestigde valse premisse als `critical`.

## 11. Severity-model en release-blokkade

| Severity | Definitie | Voorbeelden (taxonomie-sleutels) | Gevolg |
|---|---|---|---|
| **critical** | een fout die juridisch, financieel of qua vertrouwen direct schade doet | `feit.vorm_fout`, `feit.kern_fout`, `feit.gewicht_fout`, `prijs.fout`, `voorraad.valse_belofte`, `levering.valse_toezegging`, `retour.fout_recht`, `garantie.toezegging_zonder_bevoegdheid`, `medisch.claim`, `privacy.andere_klant`, `premisse.vals_bevestigd`, `korting.toegezegd`, `refund.toegezegd` | één niet-verklaarde critical in de relevante eval-groep → `release_geblokkeerd = 1` voor die intentiegroep; niveau van betrokken intenties automatisch terug naar `assisted` (of `human` als het al assisted was) |
| **high** | advies dat duidelijk ongeschikt is zonder direct juridisch/operationeel risico | `advies.ongeschikt`, `advies.afrader_gemist`, `escalatie.gemist`, `bron.verplicht_niet_geraadpleegd`, `onbekend.verzwegen` | > 2 % high in de groep → blokkade; elke high wordt een incident |
| **medium** | onnodige vraag, matige nuance, suboptimaal alternatief | `vraag.onnodig`, `nuance.zwak`, `alternatief.suboptimaal`, `escalatie.onterecht` | telt in de score; blokkeert niet |
| **low** | stijl, formulering, lengte | `toon`, `lengte`, `taalfout` | telt in de score |

Regels: de eval rapporteert **eerst** de tellingen per severity, pas daarna een gemiddelde; een gemiddelde verbergt nooit een critical. "Verklaard" kan alleen door Mathias, met reden, en blijft zichtbaar in de run. De autonomiepoort leest `release_geblokkeerd` van de laatste run voor de intentiegroep: geblokkeerd → geen `autonomous`, wat de intentietabel ook zegt.

## 12. Conversation Importer

- **Upload**: drag-and-drop van één of meer bestanden (`/copilot/imports`). Bron kiezen of "automatisch herkennen".
- **Parsers** (elk met `parser_versie`, elk met fixtures in `tests/importer/`):
  - Tidio: CSV/JSON-export (kolommen visitor/operator/timestamp/message) → één document per conversatie.
  - ChatGPT: `conversations.json` (mapping-boom; lineaire reconstructie via `current_node`) → één document per conversatie; `antwoord_door = ai_chatgpt`.
  - Claude: JSON-export (`chat_messages[]` met `sender`) → idem, `ai_claude`.
  - E-mail: `.eml`, `.mbox`, of geplakte thread-tekst (quote-stripping, `From:`/`Van:`-headers) → één document per thread.
  - WhatsApp: `.txt`-export (`[dd/mm/yyyy, hh:mm] Naam: tekst`) → één document per gesprek per contact per dag-cluster.
  - Platte tekst / Markdown: gesplitst op lege regels en "Klant:/Mathias:"-markeringen waar aanwezig; anders één document.
  - CSV/JSON generiek: kolommapping in de UI (vraag, antwoord, datum, taal, bron).
- **Normaliseren** (LLM, klein model, tool `segmenteer_gesprek`): splitst een document in (klantvraag, antwoord, antwoord_door)-paren, detecteert taal, herkent ordernummers/productnamen, markeert een AI-antwoord dat door Mathias gecorrigeerd werd (`correctie_mathias`), en vult `historische_context` en `NIET_ACTUEEL_json` (elke prijs, termijn, voorraadclaim, procedure die in het gesprek staat). Het model krijgt de instructie dat het niets mag beoordelen als waar.
- **Pseudonimiseren** (deterministisch, geen LLM): namen (uit deelnemerslijst + NER-lite), e-mail, telefoon, adres, IBAN → tokens; ordernummers blijven (nodig voor koppeling); `pseudoniem = 1`. Alleen gepseudonimiseerde gesprekken zijn bruikbaar voor Golden Set, generator en judge. Ruwe documenten blijven in `import_documenten` (alleen Copilot-inzage).
- **Classificeren**: intenties (router), producten (zoekAnker), groep (Golden-groepen), en een eerste `leerbaar_json` (toon, patroon, vervolgvraag, nuance, afraden, escalatie). Kwaliteit blijft `ongekeurd` tot Mathias of de judge het beoordeelt.
- **Wat de importer nooit doet**: policy-versies aanmaken, adviesregels bevestigen, feiten opslaan. Hij mag wél kandidaat-hiaten aanmaken ("in 7 gesprekken … in 2 …").

## 13. Training Lab

**Generator** (`/api/lab/genereer`), zes soorten, elk met eigen prompt-versie en tool-schema, altijd gegrond in échte catalogus-gids, regels en policy (nooit verzonnen producten):
1. *Herformulering*: één intentie + context → 5–10 formuleringen, expliciet gelabeld als dezelfde intentie (test voor de router).
2. *Onvolledig*: korte vragen ("En deze?", "Hoe snel?") met een gesprekscontext waaruit de verwijzing volgt, plus een variant zónder context (verwacht: wedervraag).
3. *Samengesteld*: profiel + blessure + huidig racket + probleem + vergelijking + gewicht + logistiek in één zin; verwachte ontleding meegeleverd.
4. *Misleidend*: valse premisse over een feit of beleid; verwacht: premisse corrigeren op basis van Fact Brain/Policy, severity critical bij bevestiging.
5. *Randgeval*: bijna-gelijke namen, ander modeljaar, oude naam, typo, alleen kleur, verkeerde merk-modelcombinatie, niet meer leverbaar, bronconflict, nieuwe collectie zonder data, exact gewicht bij dropship.
6. *Tegenstrijdig*: fixtures waarin Shopify, Tienda-stand, Engine-conflict en een oud historisch gesprek elkaar tegenspreken; verwacht: de actuele bron wint, het historische gesprek nooit, en onbekend waar bronnen conflicteren.
Plus **minimal pairs**: uit elke bestaande case één partner met precies één gewijzigde variabele (elleboog, niveau, huidig racket, budget, voorraad, modeljaar, positie, doel); `variabele_verschil` en de verwachting (advies moet/mag niet veranderen) worden vastgelegd.

**Training Mode** (`/copilot/training`, `TRAIN MIJ` / `TEST MATHIAS AI`):
- `train_mij`: het systeem kiest een vraag (uit hiaten, zwakke groepen, of gegenereerd), Mathias antwoordt; het systeem ontleedt (feiten gebruikt, adviesregel, afweging, bewust niet-gestelde vragen, doorslaggevende factor, herbruikbaar als regel of testcase, conflict met bestaande regels) en stelt maximaal drie gerichte vervolgvragen; uitkomst: kandidaat-adviesregel, golden case met `goedgekeurd_antwoord`, en/of hiaat.
- `test_ai`: het systeem antwoordt zelf op dezelfde soort vraag, Mathias beoordeelt (goed / fout + severity + correctie); uitkomst: golden case + incident + eventueel hiaat.
Alle ontledingen gebruiken het Fact Brain om de door Mathias genoemde feiten te toetsen; noemt Mathias een feit dat het Fact Brain niet kent, dan wordt dat een `feit_ontbreekt`-hiaat, geen nieuw feit.

## 14. Knowledge Gap Queue

- **Detectie** (batch, expliciet gestart; later ook live): (a) regelconflict: twee bevestigde regels met overlappende voorwaarde en tegengesteld gevolg; (b) inconsistente antwoorden: geclusterde historische gesprekken met dezelfde intentie en profiel maar afwijkende adviezen (embedding-cluster + regelvergelijking); (c) terugkerende uitzondering: ≥ 3 gesprekken die van een bevestigde regel afwijken; (d) onbegrepen keuze: judge kan de keuze van Mathias niet aan een regel of feit koppelen; (e) procedure niet machineleesbaar: policy met `gestructureerd_json = null` die in gesprekken voorkomt; (f) nieuw vraagtype: router-zekerheid < 0,5 in ≥ 3 gesprekken; (g) feit ontbreekt: `onbekend` op een kritiek veld voor een product dat ≥ 3× gevraagd wordt.
- **Vraagvorm**: altijd gericht, met tellingen en verwijzingen naar de bewijsstukken; met hypothese als die er is. Nooit "kun je meer uitleg geven".
- **Antwoord**: JA (hypothese wordt regelversie `bevestigd`), NEE (hypothese verworpen, regel blijft), AANPASSEN (Mathias formuleert; nieuwe versie), UITZONDERING (nieuwe regel met status `uitzondering` en expliciete voorwaarde). Elke uitkomst maakt automatisch een minimal pair aan in de Golden Set.

## 15. Autonomiepoort (`src/lib/autonomie/`)

```ts
export function poort(input: { intenties: string[]; feiten_onbekend_kritiek: boolean; klant_geverifieerd: boolean; kanaal: Kanaal; actie?: Actie }): { niveau: "autonomous"|"assisted"|"human"; reden: string; blokkades: string[] };
```
Regels, in deze volgorde en fail-closed: rem ≠ vrij → human; actie niet op allowlist (`concept_opslaan`, `dossier_bouwen`, `escalatie_aanmaken`, `golden_case_aanmaken`, `hiaat_aanmaken`) → geweigerd; laatste eval-run van de groep `release_geblokkeerd` → max assisted; een intentie `human` in de lijst → human; een intentie `assisted` → assisted; `feiten_onbekend_kritiek` → min assisted; orderdata zonder verificatie → human; anders het laagste niveau van de intenties. Sprint 1: de klantkant bestaat niet, dus `autonomous` betekent alleen "de Copilot toont het concept als autonoom-waardig"; er wordt niets verzonden.

## 16. Security

- Master-SSO (gedeeld `SESSION_SECRET`), geen eigen login; `MASTER_ORIGIN` verplicht; alle `/copilot`-pagina's en `/api/*` op sessie, behalve `/api/gezondheid` (health-token).
- Machine-secrets uitsluitend uitgaand: `KLANT_LEES_SECRET`, `ENGINE_ACCESS_TOKEN`, `TRACKING_SECRET`, `ONFACT_*`, Shopify client credentials van de eigen read-only app. Geen `SYNC_SECRET` van Master in deze service.
- Geen enkele uitgaande mutatie: structurele test (`tests/geenWriters.test.ts`) leest `src/` en faalt op `mutation`, `fulfillmentCreate`, `metafieldsSet`, `productVariantsBulkUpdate`, `PUT`/`POST` naar onFact/Scrada/stockprice/tracking-`/sync|/koppel|/afvink`, en op elk `write_`-scope-woord.
- LLM-invoer: klanttekst en geïmporteerde tekst zijn data (in tool-resultaten en user-berichten, nooit in system prompts); tool-resultaten worden gefilterd op URL's/codes waar ze in klanttekst terechtkomen; adversariële set in de eval-poort.
- Persoonsdata: ruwe imports alleen zichtbaar in de Copilot; eval/golden alleen gepseudonimiseerd; `tests/geenPersoonsdata.test.ts` grept `eval/` op e-mail-, telefoon- en IBAN-patronen.
- Audit: elke AI-call, elke beslissing, elke niveau-wijziging, elke rem-wijziging.
- Kill switch: `rem` fail-closed naar `stop` bij ontbrekende rij.

## 17. Tests en acceptatiecriteria

**Tests**
- Unit (vitest): adapters (mock-HTTP; bekend/onbekend/versheid/time-out), Fact-bronketen (volgorde, tier-5-label, conflict → onbekend), delta-calculator, regelset (alleen bevestigd/uitzondering), policy (geldigheid op datum, taal), router (deterministische signalen; LLM gestubd), ontleding, poort (waarheidstabel over alle regels), severity (blokkade-berekening), importer (elke parser met fixture), pseudonimisering (elk patroon), Golden-model (zod), eval-runner (met gestubde denker), consistentie/minimal pairs, kostenberekening.
- Structureel: `geenWriters`, `geenPersoonsdata`, `elkeRouteHeeftPoort`, `geenSpecsInPrompts` (prompts bevatten geen spec-getallen), `nietActueelNooitBron` (geen module leest `NIET_ACTUEEL_json` behalve de Copilot-weergave).
- Eval als poort: `npm run poort` = typecheck + vitest + build + eval-run op Golden Set v1 met gestubde denker (deterministisch) + adversariële set; een echte-LLM-eval draait apart (`npm run eval:echt`) en wordt handmatig beoordeeld.
- E2E (Playwright, wegwerp-DB, gestubde denker, `OPENAI_API_KEY`/`ANTHROPIC_API_KEY` leeg): dossier per ORD (fixture), concept + EDIT + diff, import van drie fixture-bestanden tot en met classificatie, Training Mode-ronde, hiaat beantwoorden → regelversie, eval-run → geblokkeerde release bij een critical-fixture.

**Acceptatiecriteria Sprint 1** (allemaal aantoonbaar, niet beweerbaar)
1. `npm run poort` groen; `tests/geenWriters.test.ts` en `geenPersoonsdata.test.ts` bestaan en slagen.
2. `GET /api/dossier/ORDxxxx` levert in < 3 s een dossier tegen de echte Shopify-app met minimaal order, regels, fulfilments met tracking, split-detectie, en per ontbrekende bron een expliciet `onbekend`.
3. De importer verwerkt één echte Tidio-export, één ChatGPT-export, één Claude-export, één e-mailthread en één WhatsApp-tekst tot gepseudonimiseerde, geclassificeerde historische gesprekken, met `NIET_ACTUEEL_json` gevuld.
4. Golden Set v1 bevat ≥ 150 cases over ≥ 20 groepen, waarvan ≥ 50 uit import, ≥ 50 gegenereerd en ≥ 20 minimal pairs; export/import JSON round-trip identiek.
5. Eén eval-run met echte LLM is uitgevoerd; het rapport toont tellingen per severity vóór het gemiddelde; een geplante critical-case blokkeert de release van zijn groep.
6. Training Mode: Mathias heeft ≥ 10 rondes gedaan; ≥ 3 kandidaat-adviesregels en ≥ 3 hiaten zijn ontstaan; één hiaat is via JA/AANPASSEN tot een bevestigde regelversie geworden en heeft automatisch een minimal pair gemaakt.
7. Elke AI-call staat in `ai_calls` met kosten; `/copilot/kosten` toont dag- en taaktotalen die optellen tot het totaal.
8. De poort geeft `human` bij rem ≠ vrij, bij ontbrekende verificatie en bij geblokkeerde groep, bewezen in tests.
9. Geen enkele klant heeft iets gezien; geen enkele write heeft plaatsgevonden (audit van Shopify-app: alleen read-scopes; Master/Engine/tracking ongewijzigd op `main`).
10. Drie voorstel-patches liggen klaar en zijn beschreven; geen ervan is toegepast.

## 18. Welke bestaande repo's en bestanden worden gewijzigd

| Repo | Wijziging | Wanneer | Hoe |
|---|---|---|---|
| `padelmq-brain` (nieuw) | alles hierboven | Sprint 1 | eigen repo/branch |
| `padelmq-pro` | `next.config.mjs`: één rewrite `/brain/*` (multi-zone) · `src/app/api/klant/route.ts` + `src/lib/klantLezing.ts` (read-only, eigen secret) · `.env`: `KLANT_LEES_SECRET`, `BRAIN_URL` | **niet in Sprint 1**; patch ligt klaar, Mathias beslist | PR op aparte branch; `npm run poort` van Master moet groen blijven |
| `padelmq-ai-product-engine` | `src/app/api/feiten/[gid]/route.ts` (read-only, `autoriseerMachineOfMens`) | niet in Sprint 1; patch ligt klaar | PR |
| `padelmq-tracking` | `app.py`: `GET /api/order/<ORD>` (read-only) | niet in Sprint 1; patch ligt klaar | PR |
| Shopify | één nieuwe custom app "PadeLMQ Brain" met read-scopes | Sprint 1, door Mathias | Dev Dashboard |
| `padelmq-teller` | alleen `docs/ai-cx` (dit plan); advies: verplaatsen naar de private repo | nu | – |

## 19. Wat expliciet NIET wordt aangeraakt

- Geen enkele writer: prijzen, voorraad, VIP, fulfilments, facturen, Scrada, stockprice, Engine-publicatie, Mechelen-spiegel.
- Masters SQLite, `instrumentation.ts`, achtergrondlussen, `goedkeuring`/`rem` van Willie, Willie zelf.
- Het Shopify-thema en de storefront (geen widget, geen chips, geen scripts).
- Tidio blijft ongewijzigd live.
- Gmail-verzending (Sprint 2), WhatsApp (later), klant-facing UI (na eval-bewijs en GO).
- Geen avatar, 3D, lipsync, realtime voice. De Copilot-UI reserveert wél een `Karakter`-slot (component met states idle/luisteren/denken/antwoorden) dat in Sprint 1 een statisch merkteken toont.
- Geen automatische regelbevestiging, geen automatische policy-wijziging, geen automatische niveau-verhoging.

## 20. Sprintplanning (3 weken)

| Week | Traject A | Traject B |
|---|---|---|
| 1 | repo, schema, auth, denker + audit + kosten, adapters (Shopify echt; Master/Engine/tracking als stub met contract), Fact/Advice/Policy-interfaces, poort, severity, intentie-seed | Mathias levert exports (Tidio, ChatGPT, Claude, mails, WhatsApp) en maakt de Shopify-app; parsers + pseudonimisering |
| 2 | dossierbouwer, Copilot-UI (dossier, concept, beslissing, wachtrij), Golden-model, eval-runner (gestubd), e2e | normaliseren + classificeren van de eerste batches; Golden v1 uit import; policy-store vullen (retour, garantie per merk, verzending, testservice, afhalen, btw) in 3 talen met geldig_van |
| 3 | Training Lab (generator 6 soorten + minimal pairs), Training Mode, hiaat-detectie + queue, eerste echte eval-run, patches voor Master/Engine/tracking | Mathias: 10+ trainingsrondes, hiaten beantwoorden, eval-resultaten verklaren; acceptatie §17 |

Daarna (Sprint 2, ter beslissing): Gmail-lezen en -verzenden via de Copilot; Master/Engine/tracking-patches toepassen; eerste intenties van `assisted` naar `autonomous` op basis van eval + vier weken bewijs; contextuele feiten op de site (Richting B) achter een feature-flag.
