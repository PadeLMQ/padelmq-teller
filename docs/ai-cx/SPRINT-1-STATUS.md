# SPRINT 1 · STATUS NA BOUWSESSIE (28 september 2026)

Alles hieronder is gebouwd, getest en gecommit in de repo `padelmq-brain` (lokaal in de sessie; zie "Wat Mathias moet doen" voor hoe hij binnenkomt). Niets staat live. Niets schrijft naar Shopify, Master, de Product Engine, de tracking-service of onFact.

## Poort (allemaal groen, laatste run)

| Stap | Uitkomst |
|---|---|
| `tsc --noEmit` | 0 fouten |
| `vitest run` | 16 bestanden, 171 tests |
| `npm run eval` (Golden Set v1, stub-provider, deterministisch) | 18/18, release vrij; de geplante misleidende case ("De AT10 18K is toch rond?") wordt niet bevestigd |
| `next build` | 14 Copilot-pagina's, 19 API-routes |
| Playwright e2e (desktop + mobiel) | 18/18 |

Structurele tests bewaken: geen enkele mutatie of write-scope in `src/`; alleen `denker.ts` spreekt met een LLM-API; `NIET_ACTUEEL_json` alleen in importer/schema/Copilot-weergave; geen productgetallen in systeemprompts; elke API-route heeft een poort; `eval/` bevat geen persoonsdata.

## Wat er staat (per component uit het Sprint 1-plan)

| # | Component | Status |
|---|---|---|
| C1 | Datalaag, schema-in-code (24 tabellen), busy_timeout, verse DB begint met rem op STOP | klaar |
| C2 | Master-SSO (gedeeld `SESSION_SECRET`), health-token, geen eigen login | klaar |
| C3 | AI-wrapper `denker` (OpenAI + Anthropic + stub), tool-loop, audit per call met tokens en kosten, weigert bij rem STOP en bij model zonder prijs | klaar |
| C4 | Fact Brain: bronketen Engine → `padelmq_engine.spec` → `custom.*` (tier 5, "onbevestigd") → referentie-rackets → UNKNOWN; NL/ES/EN-normalisatie; `zoekAnker` | klaar |
| C5 | Advice Brain: deterministische delta's (zachter/harder, balans, gewicht, vorm, blad), regelset alleen bevestigd/uitzondering, DNA-banden | klaar |
| C6 | Policy Store: 27 sleutels × nl/fr/en als lege concepten, geldigheid op datum, letterlijk citeerbaar; activeren weigert lege tekst | klaar, inhoud in te vullen |
| C7 | Adapters read-only: Shopify (eigen app, orders/fulfilments/klant/metafields), Master `/api/klant`, Engine `/api/feiten`, tracking, onFact; time-out, herkansing, alles als `Feit<T>` | klaar; Master/Engine/tracking geven "bron niet gekoppeld" tot de patches zijn toegepast |
| C8 | Dossier per ORD: klant (gehasht), regels, fulfilments met tracking, split-detectie, factuur, retour/garantie-context, `ontbrekend[]`, hypothese gelabeld | klaar |
| C9 | Intentiecatalogus (62, allemaal `human`, voorstel apart), router (deterministisch + LLM), ontleding van samengestelde vragen, verwijzingen, premisse-check | klaar |
| C10 | Autonomiepoort (fail-closed in elke richting), GO-log, automatische degradatie | klaar |
| C11 | Severity-model (36 fouttypes), releaseblokkade per groep, incidenten | klaar |
| C12 | Conversation Importer: Tidio CSV/JSON, ChatGPT, Claude, .eml/.mbox/geplakte thread, WhatsApp, platte tekst, generiek CSV/JSON; pseudonimisering; normalisatie met `NIET_ACTUEEL_json` en `leerbaar_json`; classificatie; keuring | klaar |
| C13 | Golden Set: model, 25 groepen, versies, export/import (byte-gelijke round-trip), minimal pairs; seed v1 met 18 cases | klaar |
| C14 | Eval-runner: regel-evaluator, LLM-judge (optioneel), consistentie voor minimal pairs, verklaringen, rapport met tellingen eerst | klaar |
| C15 | Training Lab: generator (7 soorten), Training Mode `TRAIN MIJ` / `TEST MATHIAS AI` met ontleding en gerichte vervolgvragen | klaar |
| C16 | Knowledge Gap Queue: 7 detectoren, gerichte vragen met tellingen, JA/NEE/AANPASSEN/UITZONDERING → regelversie + minimal pair | klaar |
| C17 | Copilot-UI: dossier, wachtrij, concept met APPROVE·EDIT·TAKE OVER (nooit verzonden), training, hiaten, golden, eval, imports, historiek, policy, regels, autonomie, kosten, rem | klaar |
| C18 | Audit en kosten: `ai_calls`, dag- en taaktotalen, incidenten | klaar |
| C19 | Tests, e2e, CI-workflow, deploy-poort | klaar |
| — | Orkestrator: de echte `Beantwoorder` (tool-loop over Fact/Advice/Policy/dossier, objecten alleen uit tool-resultaten, deterministische terugval) | klaar |
| — | Integratiepatches (niet toegepast): Master `/api/klant` + Multi-Zone-mount, Engine `/api/feiten/[gid]`, tracking `/api/order/<ORD>` | klaar als voorstel |

## Bewuste afwijkingen van het plan

1. SQLite in plaats van Postgres (schema-in-code, Postgres later als configuratie).
2. Escalatie is inhoudelijk (retour, garantie, btw, schade, klacht, herroeping, onbevestigde klant, of het model escaleert) en staat los van het poortniveau; anders faalde op een verse database elke case op "onterechte escalatie".
3. Concept in twee fasen (vrije tool-lus, daarna geforceerde `lever_antwoord`), omdat een geforceerd gereedschap anders de feit-tools blokkeert.
4. Een extra tool `haal_levertijd` die vandaag eerlijk "levertijdregel nog niet gekoppeld" zegt.
5. Playwright gepind op 1.56.1 (de browser die in de omgeving beschikbaar was).

## Acceptatiecriteria (§17 van het plan)

| # | Criterium | Stand |
|---|---|---|
| 1 | poort groen, `geenWriters`/`geenPersoonsdata` bestaan | ja (in `tests/structureel.test.ts`) |
| 2 | dossier < 3 s tegen echte Shopify-app | nog niet: vereist de Shopify-app (Mathias) |
| 3 | importer verwerkt echte exports | code klaar, fixtures groen; echte exports nog te leveren |
| 4 | Golden Set ≥ 150 cases | 18 (seed); groeit via import, generator en training |
| 5 | eval-run met echte LLM | nog niet: vereist sleutel en rem op VRIJ |
| 6 | Training Mode ≥ 10 rondes | nog niet: vereist Mathias |
| 7 | elke AI-call geaudit met kosten | ja |
| 8 | poort geeft `human` bij rem/verificatie/blokkade | ja (tests) |
| 9 | geen klant heeft iets gezien, geen write | ja |
| 10 | drie patches klaar, geen toegepast | ja (vier, incl. Multi-Zone) |

## Wat Mathias moet doen om Sprint 1 af te ronden

1. **Repo**: maak `PadeLMQ/padelmq-brain` (private) aan en importeer de meegeleverde git-bundle (`git clone padelmq-brain-sprint1.bundle padelmq-brain`, remote zetten, pushen). Deze sessie kon geen repo in de org aanmaken en mocht de code niet naar een branch in `padelmq-pro` pushen.
2. **Publiek/privaat**: verplaats `docs/ai-cx` uit `padelmq-teller` (publiek) naar `padelmq-brain` en verwijder ze uit de teller-repo.
3. **Shopify**: custom app "PadeLMQ Brain" met alleen `read_orders, read_fulfillments, read_customers, read_products, read_inventory, read_locations`; client-id en secret in `.env`.
4. **Secrets**: `SESSION_SECRET` (identiek aan Master), `MASTER_ORIGIN`, één LLM-sleutel, en pas later `KLANT_LEES_SECRET`, `ENGINE_ACCESS_TOKEN`, `TRACKING_SECRET`, `ONFACT_*`.
5. **Rem**: op `/brain/copilot/rem` van STOP naar VRIJ, met reden.
6. **Exports**: Tidio, ChatGPT, Claude, mails, WhatsApp uploaden op `/brain/copilot/imports`.
7. **Policy Store**: de 27 sleutels invullen (retour, garantie per merk, verzending, levertijd, afhalen, testservice, btw, herroeping) en activeren.
8. **Training**: tien rondes `TRAIN MIJ`; hiaten beantwoorden.
9. **Beslissen** over de vier patches (Master, Engine, tracking) en over de twaalf open punten uit het masterplan.
