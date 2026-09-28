# Inventaris van vijf PadeLMQ-repo's voor de AI-klantenservice en de interne Mathias Copilot

Ik heb de code gelezen en niets gewijzigd. Waar documentatie en code elkaar tegenspreken, vermeld ik dat.

Drie vaststellingen bepalen het ontwerp:
- **Racketspecificaties staan op de shop vandaag als vrije tekst in `custom.*`-metafields.** Alleen producten die de Engine zelf heeft aangemaakt, krijgen ook gestructureerde `padelmq_engine.*`-JSON met bron per feit.
- **Tracking van Tienda-dropship komt niet uit een Tienda-account.** Het komt uit ICP-verzendmails, via IMAP en een headless browser (Playwright). De koppeling staat alleen in een JSON-bestand, en de Railway-versie draait nog in droogtest.
- **Geen enkele repo heeft een klant-facing flow of een leesendpoint per order.** Dat bestaat voor orderstatus, tracking en "ik wil een factuur" nergens.

---

## A. `/home/user/padelmq-ai-product-engine` — AI Product Engine 2027

**Doel.** De Engine onderzoekt nieuwe padelproducten die nog niet op de shop staan. Ze haalt bronnen op, slaat feiten op mét herkomst, laat tegenspraken door een mens beslechten, berekent Racket DNA en maakt het product via een tweetraps publicatiepoort aan in Shopify.

- **Documentatie loopt achter.** CLAUDE.md en MASTER_BUILD_STATUS §1 zeggen nog "geen Shopify-client". Sinds ronde 16/27 bestaan `src/lib/shopifyTransport.ts` (Admin GraphQL 2024-10) en een publicatiepad, maar alleen voor create en Engine-eigen producten.

**Stack en hosting**
- Next.js 14 App Router, TypeScript, Tailwind, Zod, Cheerio.
- Database: SQLite via `better-sqlite3` (`src/lib/db.ts`, `getDb()`/`haalDb()`).
- Hosting: Railway (`railway.json`, `Dockerfile`), SQLite op een volume.
- Inloggen: geen eigen login. De sessie komt van Master (`SESSION_SECRET` gedeeld, `src/lib/auth.ts`).
- Machine-naar-machine: `ENGINE_ACCESS_TOKEN`, header `x-engine-secret`.

**Postgres-pad**
- Gebouwd: async adaptercontract (`src/lib/dbAdapter.ts`), één schema voor beide dialecten (`src/lib/schema/tabellen.ts`), gegenereerde DDL (`migrations/postgres/001_initial.sql`).
- Aanzetten gaat via `DB_DIALECT=postgres` en `DATABASE_URL`.
- **De DDL is nooit tegen een echte PostgreSQL gedraaid** (DATABASE.md, "Wat er NIET bewezen is").

### Datamodel (`src/lib/schema/tabellen.ts`)

- **`product_candidates`**
  - Kolommen: brand, model, year, category, tienda_url (NOT NULL), sku, ean, status.
  - Later toegevoegd: tienda_product_id, sport, archived.
  - Status: DRAFT → RESEARCHED → CONFLICTS_PENDING → READY_FOR_REVIEW / NEEDS_ATTENTION → APPROVED.
- **`source_documents`**
  - Kolommen: url, domain, source_type, source_tier (1–5), fetched_at, content_hash, raw_text, extraction_status.
  - Later toegevoegd: source_role, generation_exactness.
- **`knowledge_objects`**: één per model, niet per kleurvariant.
- **`facts`**
  - Kolommen: field, value, normalized_value, datatype, unit, source_tier, confidence, criticality, status (`verified`/`inferred`), inferred_from, extractor, snippet, claim_type.
  - `source_document_id` is NOT NULL met `CHECK (>0)`.
- **`conflicts`**: severity, status, candidates_json, selected_value, reason, resolved_by. UNIQUE op (ko, field, kind).
- **`manual_overrides`**: menselijke correcties, overleven elke her-run.
- **`source_tier_config`**: domeinpatroon → tier. 1 fabrikant · 2 Tienda · 3 padel-specialist · 4 retailer · 5 overig. Amazon staat op 5 met `auto_allowed=0`.
- **Prompts**: `prompt_sets` en `prompt_versions` (DRAFT/TEST/ACTIVE/ARCHIVED).
- **`racket_dna_scores`**
  - Oorspronkelijke kolommen: `{power,control,spin,agility,comfort,forgiveness}_{raw,norm}`.
  - Later toegevoegd: `sweet_spot_*`, `maneuverability_*`, `*_pres`, `niet_gescoord`, plus inputs_json en scoring_version.
- **Overige tabellen**: `product_variants` (met shopify_variant_gid, tienda_option_value_id), `product_publications` (met shopify_product_gid, source_status, laatste_voorraad_sync_at), `product_publication_events`, `product_images`, `price_observations`, `stock_observations`, `tienda_variant_stock_observations`, `content_blocks`, `content_quality_reviews`, `content_generation_audit`, `review_watch_state`, `evidence_deltas`, `content_update_proposals`, `tienda_sessies`, `size_charts`, `field_waivers`, `fetch_log`, `status_transitions`.

### Geëxtraheerde racketvelden (`RACKET_VELDEN`, `src/lib/schema/racket.ts:749`)

- **Identiteit (altijd critical):** brand, model, year, ean, sku.
- **Specificaties:**

| Veld | Criticality | Eenheid / waarden |
|---|---|---|
| shape | critical | enum rond/druppel/hybride/ruit; synoniemen in 4 talen |
| weight | optional | exact gewicht, g |
| weight_range | critical | bereik, g |
| balance_point | optional | cm |
| balance | critical | enum laag/medium/hoog |
| thickness | important | mm |
| core | important | vrije tekst (EVA-type) |
| core_hardness | important | enum zacht/medium/hard |
| face_material | important | — |
| frame_material | important | — |
| surface_finish | optional | — |
| roughness | optional | — |
| level | important | enum |
| playing_style | important | enum controle/polyvalent/aanval |
| sweet_spot, touch, grip_length | optional | — |
| technologies | optional | lijst, gefilterd op FAQ/navigatietekst |

- **Overige velden:** pro_players, twaalf `review_*_feel`-velden (power, control, comfort, manoeuvrability, forgiveness, defence, net_play, overheads, ball_output, touch, stability, limitations) en manufacturer_positioning.
- Er zijn aparte schema's voor schoenen, kleding, tassen, ballen, accessoires en pickleball (`src/lib/schema/*.ts`).

### Racket DNA (`src/lib/dnaModel.ts`, `src/lib/racketDna.ts`, `src/lib/dnaPubliekePresentatie.ts`)

**Zes dimensies:** power, control, sweet_spot, maneuverability, comfort, spin. Er is met opzet geen totaalscore (`HEEFT_TOTAALSCORE = false`). Huidige versie: `SCORING_VERSION = "dna-v5"`.

**Invoer:** elk feit wordt op een vaste schaal van 0 tot 1 gelegd.
- Balans en vorm: laag/rond = 0, druppel/hybride = 0,5, hoog/ruit = 1.
- Kernhardheid: zacht = 0 tot hard = 1.
- Gewicht: ankers 340–390 g. `weight_effectief` valt terug op het midden van `weight_range`.
- Dikte: ankers 36–39 mm.
- Oppervlak: regex ruw/glad.
- `face_stiffness`: stijfheid van het slagvlakmateriaal.
- Touch en playing_style.

**Gewichten dna-v5 (`DNA_GEWICHTEN_V5`):**

| Dimensie | Gewichten |
|---|---|
| power | balance 0,3 · shape 0,2 · core_hardness 0,2 · weight_effectief 0,15 · face_stiffness 0,15 |
| control | negatief: balance, shape, core_hardness, thickness, face_stiffness, touch, playing_style |
| maneuverability | weight_effectief −0,55 · balance −0,45 |
| comfort | core_hardness −0,32 · face_stiffness −0,3 · balance −0,05 · weight_effectief +0,25 · touch −0,08 |
| sweet_spot | shape −0,5 · balance −0,3 · thickness +0,2 (gewichten v1) |
| spin | surface 0,7 · shape 0,2 · core_hardness 0,1 (gewichten v1) |

**Berekening (`berekenDimensies()`):**
- Per dimensie: raw = Σ(gewicht × (waarde−0,5)×2) / bekend gewicht. Dat geeft een waarde van −1 tot 1.
- Is minder dan 60 % van het gewicht bekend (`MINIMALE_DEKKING = 0.6`), dan wordt de dimensie `null`.

**Drie schalen, allemaal absoluut** (vaste ankers, nooit geschaald tegen de catalogus):

| Schaal | Formule | Bereik | Bestemming |
|---|---|---|---|
| Ruw | 5 + 5·raw | 0,0–10,0 | analyse |
| Presentatie | 5 + 3,5·raw, één decimaal | 1,5–8,5 | intern |
| Publiek | aparte affiene mapping, `dna-public-v1` | ca. 70–100 % | winkelpagina |

- Naar de contentgenerator gaat alleen een kwalitatieve band (laag/gemiddeld/hoog), via `dnaKwalitatieveBand()`.
- Bewezen voorbeeld, Bullpadel Pearl 2027, publiek (ruw): Kracht 7,1 (7,9), Controle 2,5 (1,5), Sweet spot 1,5 (0,0), Wendbaarheid 3,4 (3,3), Comfort 4,1 (3,6), Effect 8,2 (9,5).

### LLM's en prompts

- **Feitextractie:** `src/lib/claudeExtractor.ts` gebruikt Anthropic `claude-sonnet-5` (`EXTRACTOR_MODEL`). Triagemodel: `claude-haiku-4-5-20251001`.
  - **De standaard is `EXTRACTOR=placeholder`**: regels en regex, zonder LLM.
- **Andere Claude-toepassingen:** bronontdekking, productweetjes, vertaling, contentcriticus en een review-watch-lus (`ENABLE_REVIEW_WATCH=false`).
- **Productietekst:** OpenAI in `src/lib/openaiContent.ts`, model `OPENAI_CONTENT_MODEL=gpt-5.6-sol` (fallback in de code: gpt-4o).
- **Promptsets** (`src/lib/prompts.ts`), de prompt komt altijd uit de database (ACTIVE-versie):
  - `racket-feitextractie`
  - `racket-content` (V2 t/m V23)
  - `racket-golden-example`
  - `shoes-content`, `clothing-content`, `bags-content`, `balls-content`, `accessories-content`, `pickleball-paddle-content`

**Hoe hallucinatie wordt tegengehouden:**
- Eén tool (`lever_feiten`) met `tool_choice` geforceerd en een veld-enum, zodat het model geen veldnaam kan verzinnen. Een tekstfragment is verplicht.
- Het model bepaalt zijn eigen bron niet; dat doet `pijplijn.ts`.
- Elke waarde gaat door `normaliseerWaarde()`. Kan het schema een waarde niet duiden, dan wordt er niets opgeslagen.
- Binnen één document mag een veld maar één betekenis hebben.
- Een inferentie moet naar echte fact-ids verwijzen, anders wordt ze geweigerd.
- `slaFeitOp()` (`src/lib/feiten.ts`) controleert dat de bron bestaat en bij dezelfde kandidaat hoort.
- De database-CHECK weigert een feit zonder bron.
- De conflictpoort (`status.ts`) laat niets door zolang er een critical-conflict openstaat.
- `contentPoort.ts` staat alleen getallen toe die gegrond zijn in feiten.

### Volumes
- **Golden set** (`tests/golden/snapshots/`): tien snapshots.
  - Zeven echte 2027-rackets: Pearl, Vertex 05, Neuron 02 Edge, Nitro Power, Nitro Control, Adidas Match 3.4 Blue, Metalbone 3.5.
  - Drei synthetische gevallen: archetype-aanval, archetype-controle, meertalig-tegenspraak.
- **Productie:** de code verwijst naar kandidaat-id's tot #46, onder meer een NOX 2027-batch en de "Rackets V1"-runs.
- **Pearl 2027** was de eerste echte publicatie (DRAFT, 24/24-audit).
- **Het precieze aantal verwerkte producten staat niet in de repo**, want de database is niet gecommit.
- Tests: 989 groen (CLAUDE.md).

### Metafields op de shop (`METAFIELD_AUDIT.md`, `src/lib/metafieldRegistry.ts`)

**Productniveau, namespace `custom`:**

| Key | Type |
|---|---|
| vorm, gewicht, balans, kern, racket_oppervlakte, niveau_speler, sweetspot, pro_players | single_line_text |
| type_spel | list.single_line_text |
| kracht, controle, comfort | single_line_text |
| overzicht_tagline, levertijd, label, kortingscode_pachanga, tiendapadelpoint_url | single_line_text |
| testracket, prijslijst | boolean |
| standaardlocatie | list |
| preorder_datum | date |

- `racket_oppervlakte` is in werkelijkheid het **slagvlakmateriaal**, geen oppervlakte.
- `kracht`, `controle` en `comfort` bevatten handmatige waarden als "10/10" of emoji-iconen ("💥💥💥💥💥"). **Dat is geen DNA**; sinds 11 sept. 2026 schrijft de Engine ze niet meer.

**Overige namespaces:**
- Shopify-taxonomie, lijst van metaobject-referenties: `shopify.racket-material`, `racket-head-shape`, `racket-balance`, `recommended-skill-level`, `age-group`, `best-uses`, `accessory-size`.
- Varianten: `symo.vip_price` en `symo.unit_cost` (money), `netwise.catalog_price` (json, eigenaar onbekend), `mm-google-shopping.*`.

**Conclusie over racketspecificaties in Shopify:**
- **Ja, maar als vrije tekst in `custom.*`.** Bij bestaande producten zijn die met de hand of door de Herschrijver gevuld, zonder bron.
- Alleen Engine-producten krijgen ook `padelmq_engine.spec` (json), `provenance` (json), `dna` (json), `dna_signatuur`, `engine_version`, `researched_at` en `content_provenance`. `METAFIELD_AUDIT.md` stelt die namespace voor; de code (`bouwProductMetafields()`) schrijft hem.
- **Beperking van de audit:** alleen metafield-definities zijn gelezen. Metafields zonder definitie, zoals `custom.logistiek_kost`, zijn onzichtbaar gebleven.

### Veilige readers
- `src/lib/kennis.ts`: `effectieveWaarden(knowledgeObjectId, categorie)` geeft per veld de waarde, bron, tier, override en conflictstatus. Verder `kennisSamenvatting()`.
- `src/lib/racketDna.ts`: `haalDnaProfiel()`, `dnaProfielen(koId)`, `dnaGereedheid()`.
- `src/lib/dnaModel.ts`: `berekenDna(waarden)` (zuiver) en `dnaKwalitatieveBand()`. `src/lib/dnaPubliekePresentatie.ts`: `naarPubliekePresentatie()`.
- `src/lib/productKennisProfiel.ts`: `bouwKnowledgeProfile(candidateId)`.
- `src/lib/tiendaVariantVoorraad.ts`: `laatsteTiendaVariantVoorraad(candidateId)` (leveranciersvoorraad per maat).
- HTTP: `GET /api/kandidaat/[id]/tienda-mapping` (machine-token), read-only.
- `shopifyTransport.leesProductVolledig()`.

### Writers en hun poorten
- `publicatiePoort.ts` en `publicatieVoorstel.ts`: tweetraps, verse identiteitscontrole plus "typ PUBLICEER".
- `stockSync.synchroniseerVoorraad`, `zetProductStatus`, variant-reconciliatie. Alleen voor Engine-eigen producten (`engineOwnership.ts`).
- Geen van deze writers hoort bij een AI-assistent.

### Classificatie: FACT BRAIN — BESTAAT, AANPASSEN
- Het herkomstmodel is precies wat een fact brain nodig heeft.
- Maar het dekt alleen Engine-kandidaten, niet de bestaande catalogus.
- Er is geen read-API per Shopify-product. De koppeling bestaat via `product_publications.shopify_product_gid`, maar er ontbreekt een read-only endpoint.
- SQLite zit achter de Master-SSO.
- **Twee opties:**
  - een read-only endpoint in de Engine (bijv. per product-GID: effectieve waarden, bron en DNA), of
  - de AI laten lezen uit `padelmq_engine.spec`/`provenance`/`dna`.
- Voor bestaande producten bestaat alleen de bronloze `custom.*`-tekst. Een grondig fact-brain voor de oude catalogus **ONTBREEKT**.

---

## B. `/home/user/padelmq-tracking` — Tienda Tracking (Railway)

**Doel.** Het track & trace-nummer van een Tienda-dropshipzending automatisch op de juiste Shopify-order zetten; Shopify mailt daarna de klant en sluit de order. Daarnaast: carrierstatus volgen, afronden als "bezorgd", inbox-triage, een dagbrief en Tienda-inkoopfacturen uit de mailbox halen.

**Stack en hosting**
- Python, Flask (`app.py`), Playwright 1.47 (headless Chromium), IMAP/SMTP (one.com), requests, anthropic, pypdf.
- Railway via Dockerfile, volume op `/app/data`, healthcheck `/gezondheid`.
- `tienda_tracking_sync.py` is volgens de README byte-voor-byte gekopieerd van de lokale Windows-tool.
- **Status: droogtestperiode.** `TRACKING_LIVE_WRITES=false`, en de lokale Windows-versie blijft de live versie.

**Datamodel:** geen database, JSON-bestanden in `TRACKING_DATA_DIR`:
- `mapping.json`, sleutel = Tienda-ordernummer. Entry met:
  - status: `voorbereiding` / `fulfilled` / `voorraad` (eigen voorraad) / `manueel`
  - shopify_order, consignee, zip, city, carrier, tracking (kommagescheiden), icp_url, products (ICP-productlijnen), shipped_at, order_url (statusPageUrl)
  - ups_status (Onderweg / In levering / Afhaalpunt / Probleem / Geleverd), ups_est, delivered, confirmed, merged, reason, best_guess
- Verder: `processed.json`, `status.json`, `triage.json`, `preview.json`, `laatste-run.txt`, `overzicht.html` en `facturen/<TiendaRef>.pdf`.

**Databron en werking**
- **Geen scraping van het Tienda B2B-account.**
- Bron: IMAP-mails van `no-reply@icp.es` ("Order 1010307 - Shipped"). De `sh.icp.es/<token>`-link wordt met Playwright gelezen (`_read_icp_page`, `parse_icp_text`): Carrier, Tracking Number(s), Customer Reference (= Tienda-ref), Delivery ID, Status, Consignee, adres, postcode, Packages en productlijnen.
- Matching (`score_order`) tegen `fetch_open_orders()`: unfulfilled orders van de laatste 45 dagen.
  - Score: postcode 0,55 + naam 0,30 + straat 0,15 + productwoorden 0,10.
  - Automatisch koppelen alleen bij score ≥ 0,75 en een voorsprong van ≥ 0,15 op de tweede kandidaat.
  - Anders → `manueel`.
- Zendingen naar PadeLMQ zelf (consignee bevat "padelmq") → `voorraad`, niets in Shopify.

**Carriers** (`CARRIERS`)
- UPS, DHL Express, GLS, Nacex. Alleen Nacex heeft een eigen URL-sjabloon.
- **Correos, bpost en SEUR komen niet voor.** Een onbekende carrier gaat als ruwe tekst door, zonder URL.
- Carrierstatus komt uit de onderwerpen van UPS/DHL/GLS-mails (`classify_ups`, `refresh_ups_status`), plus de geschatte leverdatum.

**Shopify-mutaties** (client credentials, API 2024-10)
- `fulfillmentCreateV2`:
  - `lineItemsByFulfillmentOrder` alleen met `fulfillmentOrderId`, dus het **hele fulfillment order**, niet per orderregel;
  - `trackingInfo` met `number` of `numbers[]`;
  - `notifyCustomer = NOTIFY_CUSTOMER`.
- `fulfillmentTrackingInfoUpdateV2` (notifyCustomer: true) op de eerste bestaande fulfillment.
- `fulfillmentEventCreate(status: DELIVERED)` via `mark_shopify_delivered`.
- **Scopes staan nergens in de code.** Afgeleid: `read_orders` en schrijfrechten op fulfillment orders/fulfillments (merchant-managed).

**Split shipments / gedeeltelijke fulfilment**
- Automatisch: meer dan één open fulfillment order → geweigerd en op `manueel` gezet met reden "split order".
- Handmatig (`cmd_koppel`, route `/koppel`): alle deelpakketten met dezelfde `best_guess` worden samengevoegd, en alle trackingnummers gaan op één fulfillment over alle open fulfillment orders.
- **Tracking per orderregel of een echte gedeeltelijke fulfilment: niet ondersteund.**

**Endpoints** (allemaal achter `x-tracking-secret` of `?secret=`)
- `GET /api/status`: JSON voor Master met live_writes, bezig, laatste_run, laatste_succesvolle_run, laatste_fout, aantallen per bucket, en `aandacht_nodig[]` (klant, postcode, stad, vervoerder, reden, sinds). **Geen opzoeking per order.**
- `GET /status`, `GET /factuur/<ref>` (pdf).
- `POST /sync`, `/verrijk`, `/preview`, `/triage`.
- `POST /koppel/<ref>` en `/afvink/<ref>`: schrijven altijd live, geblokkeerd zolang `TRACKING_LIVE_WRITES=false`.

**Veilige readers:** `app.buckets()`, `load_json(MAPPING)`, `fetch_open_orders()`, `shopify_order_url()`, `shopify_is_delivered()`, `parse_icp_text()`, `classify_ups()`.

**Writers:** `create_fulfillment`, `cmd_koppel`, `mark_shopify_delivered`, `auto_finalize`, IMAP archiveren en als gelezen markeren.

**Classificatie: BESTAAT — AANPASSEN.**
- Dit is de enige bron voor de koppeling Tienda-ref ↔ ORD en voor de carrierstatus en ETA van dropship.
- Nodig: een read-only endpoint per ORD-nummer (tracking, carrier, status, ETA, deelpakketten) en een definitieve live-overgang.
- De AI mag nooit `/sync`, `/koppel` of `/afvink` aanroepen.
- Zodra het live staat, zijn de fulfillment-trackinggegevens ook rechtstreeks in Shopify leesbaar.

---

## C. `/home/user/dagontvangsten-robot` — Dagontvangsten-robot

**Doel.** B2C-ontvangsten per dag, land en btw-tarief uit Shopify berekenen en idempotent in Scrada boeken. Orders met een onFact-factuur worden uitgesloten, net als een dag zonder bewezen Bancontact-testerdekking. Een Railway-app (`app/server.py`) toont de resultaten en laat handmatige verkopen invoeren, maar boekt nooit.

**Stack en hosting**
- Python 3.12, requests, cryptography.
- GitHub Actions: `.github/workflows/dagontvangsten.yml`, cron `0 6 * * *`.
- Railway voor de app (Dockerfile, `python -m app.server`).

**Datamodel:** geen database. JSON-bestanden in `data/`:
- `booked_ledger.json`, `dagcorrecties.json`, `laatste_run.json`, `verkeerslicht.json`, `manuele_verkopen.json`
- `bancontact_testers.json`
- `lucy_invoices.json`, `facturen_boekhouder.json`, `scrada_q2_export.csv`

**Orderreader** (`src/shopify.py`, API 2026-07, client credentials)
- `ORDERS_QUERY` leest per order:
  - name, createdAt, displayFinancialStatus, cancelledAt, test, paymentGatewayNames, shippingLine.title
  - `fulfillmentOrders.deliveryMethod.methodType` en `assignedLocation{name,countryCode}`
  - lineItems (name, quantity, currentQuantity, requiresShipping, product.isGiftCard, discountedUnitPrice)
  - `shippingAddress.countryCodeV2` en `billingAddress.countryCodeV2`
  - bedragen: currentSubtotal, currentTotal, currentTotalTax, totalPrice, totalTax, totalRefunded, netPayment
  - `refunds{createdAt, totalRefunded, refundLineItems, refundShippingLines}` en `taxLines`
- Functies:
  - `fetch_orders(shop, version, target_dates)`: ruim UTC-venster, daarna exact filteren op winkeltijd, volledige paginering (100 per pagina).
  - `fetch_orders_by_name(shop, version, namen)`: in blokken van 20, filter `name:`.
  - `build_raw_order()` → dataclass `RawOrder`; `get_shop_timezone()`.
- **Er bestaat geen functie `read_all_orders`, en de code vermeldt geen scope.** Omdat order ORD64842026 van maart in september is opgevraagd, heeft de app waarschijnlijk `read_all_orders`, maar dat is een afleiding.
- Ordernamen hebben de vorm `ORDxxxx2026`. De fysieke winkel (SHOP2 "Tienda PadelPoint Mechelen") gebruikt `#1095`.

**Refunds en annuleringen** (`src/refunds.py`, `compute()`, zuiver en getest)
- Geannuleerd telt als 0, ongeacht de bedragvelden.
- Behouden bruto = min(currentTotalPrice, netPayment).
- Een bracketverificatie tegen de refundrecords voorkomt dubbel aftrekken.
- Btw wordt herberekend met het echte taxLine-tarief.
- Bij twijfel wordt het een uitzondering, geen boeking.
- Cadeaubon-verkopen gaan niet mee in de btw-grondslag. Een afhaling telt voor het land van de afhaallocatie.

**Boekhoudsystemen**
- **Lucy** (getlucy.ai): historische factuurexport, tot F260081 op 29/06/2026.
- **Boekhouder-register**: F260082 (14/07) tot aan de overgang.
- **onFact** (`api5.onfact.be/v1`): facturatie, primaire bron sinds 2026-08-14.
- **Scrada**: boekhouding. `PUT .../journal/{id}/lines` met `externalReference = DAGONTV-{datum}-{land}-{tarief}`. Alleen in stand `MODE=BOEKEN` en met een `SCRADA_VAT_MAP`.
- **Resend**: rapportmail naar Mathias.

**Facturen-index (zoeken op ORD-referentie)**
- `src/invoices.py`:
  - `normalize_ref()`
  - `InvoiceIndex.is_invoiced(order_name)` → `InvoiceRef(ref, number, date, amount, customer, source)`
  - `load_invoice_index()` (Lucy), `load_register()` (boekhouder), `index_van_onfact()`, `merge_indexes()`
- `src/onfact.py`:
  - `OnFactClient.check(order_name)` → found, classificatie DEFINITIEF (sent/paid) of IN_BEHANDELING (concept), status, nummer, endpoint (facturen of creditnota's); `is_invoiced()`
  - `lees_facturen()`: volledige limit/offset-paginering met controle op `count`
  - `definitieve_facturen_vanaf(client, vanaf)` → `LateFactuur(nummer, datum, ord, bedrag_incl, status, klant)`
- **Bekend gat:** `_find_document()` leest alleen de eerste pagina van 100. De API negeert het `order_reference`-filter (gemeten, README).

**Bancontact**
- Het gaat om racket-test-betalingen van €10: 316 transacties, allemaal €10,00, referentie "Test Racket Pachanga" of "PADELMQTESTER10". Dekking van 2025-05-14 tot 2026-09-26.
- `src/bancontact_gate.py` is een harde poort: geen dag wordt geboekt zonder bewezen dekking.
- `src/bancontact_cloud_sync.py` leest bij padelmq-pro `GET /api/bancontact/testers` en `/api/bancontact/poll` met header `X-Read-Token: BANCONTACT_READ_TOKEN` (dezelfde waarde als in de Railway-omgeving van padelmq-pro). Velden: payment_id, succeeded_at_bc, amount_cents, reference.

**Railway-app** (`app/server.py`)
- GET: `/api/overzicht`, `/api/dagen`, `/api/aandacht`, `/api/late-facturen`, `/api/verkeerslicht`, `/api/producten`.
- `/api/producten` roept `zoek_producten(term)` aan: read-only catalogus (titel, SKU, prijs, `inventoryQuantity` per variant, `totalInventory`). Geen voorraad per locatie.
- De app heeft een eigen login met rollen (`app/auth.py`).

**Writers:** Scrada-boeking (`src/scrada.py`, alleen `MODE=BOEKEN`), plus `data/*.json` voor handmatige verkopen en correctievoorstellen.

**Classificatie**
- **Facturen-index en onFact-check: BESTAAT — DIRECT HERGEBRUIKEN** voor de vraag "heeft ORD… een factuur (nummer, datum, status)?". Read-only.
- **Orderreader: BESTAAT — AANPASSEN.** Rijk aan financiële velden en refunds, maar zonder fulfillment- of trackingvelden en gebouwd voor datumvensters.
- **Scrada- en Bancontact-logica: NIET HERGEBRUIKEN** klant-facing. Hooguit voor de Copilot (dagtotalen, aandachtspunten via `/api/*`).

---

## D. `/home/user/padelmq-factuurmotor` — Factuurmotor

**Doel.** Automatische B2B-facturen voor Shopify-orders waarbij de klant een btw-nummer heeft opgegeven.
- `motor.py` loopt elke 120 s de betaalde orders van de laatste 14 dagen af.
- Hij zoekt het btw-nummer, valideert het bij VIES (inclusief naamvergelijking), maakt een concept aan in onFact, leest dat terug ter controle en verstuurt het via **Peppol** zodra de order FULFILLED is. Daarna zet hij de factuur op betaald.
- `app.py` is een lokale Flask-UI (127.0.0.1:8795) voor manuele voorstellen, correcties en creditnota's, plus afdrukken.

**Stack en hosting**
- Python, Flask, requests.
- Railway (Nixpacks) start **alleen** `python motor.py`, een worker zonder HTTP-server.
- **In de repo ontbreekt de map `templates/`**, terwijl `app.py` `render_template` gebruikt. De UI draait dus niet vanuit deze repo alleen.
- Er is één commit: "Add files via upload".
- **Docstring en code spreken elkaar tegen:** de docstring van `app.py` zegt "SCHRIJFT NOG NIETS naar onFact", maar de routes `/onfact/aanmaken`, `/onfact/verzenden` en `/correctie/uitvoeren` bestaan.

**Standen** (`motor.py`): MEEKIJKEN (standaard) / CONCEPTEN / VOLLEDIG. Alleen handmatig te wijzigen.

**Stopregels** (`beoordeel()`): de order komt op de aandachtslijst bij
- een refund,
- een ongeldig of onbekend VIES-resultaat terwijl de btw op 0 staat,
- een naam die niet overeenkomt met VIES (bij vrijstelling),
- een factuur die al bestaat (ook in onFact),
- een gedeeltelijk verzonden order.

**Btw-nummer zoeken** (`btw_uit_order`), in deze volgorde:
1. De tijdlijn van de order ("Er is een geldig btw-nummer opgegeven…", vastgesteld op ORD81752026).
2. `localizedFields` of `localizationExtensions`.
3. `customAttributes`.
4. `customer.taxSettings.taxId`.

**Shopify** (`shopify_client.py`, read-only, API 2026-07, client credentials of vast token)
- `ORDER_VELDEN`:
  - id, name, createdAt, processedAt, taxesIncluded, taxExempt, displayFinancialStatus, fullyPaid, email, note, customAttributes
  - customer (displayName, email, taxExempt), billingAddress en shippingAddress (company, landcode, telefoon), `purchasingEntity`
  - lineItems (sku, quantity, currentQuantity, prijzen, kortingen, taxLines), shippingLine, discountApplications, alle totalen, refunds, cancelledAt
  - **`displayFulfillmentStatus` en `fulfillments{status, createdAt, trackingInfo{number, company, url}}`**
- Functies: `order(ordernummer)`, `recente_orders()`, `order_gebeurtenissen()`, `klant_btw_nummer()`.

**Tabellen** (`db.py`, SQLite in `PADELMQ_DATA`)
- `documenten`: type FACTUUR/CREDITNOTA; status VOORSTEL/CONCEPT/GEFINALISEERD/VERVALLEN; shopify_order_naam, extern_nummer (bijv. F260104), klantgegevens, btw-nummer, btw_regime, bedragen, corrigeert/vervangt-keten, verzonden_op. Unieke index: één definitieve factuur per order.
- Verder: `documentlijnen`, `btw_controles` (VIES-bewijs met consultatienummer), `aandacht`, `motor_gezien`, `meldingen`, `audit`, `instellingen`.

**Externe koppelingen**
- VIES REST (`vies.py`): `controleer()`, `formaat_ok()`, `belgisch_mod97()`, `namen_komen_overeen()`.
- onFact (`onfact.py`): facturen, creditnota's, `zoek_op_ordernummer`, `verstuur_via_peppol`, `verstuur_per_mail` (**niet gebruikt door de motor**), `markeer_betaald`.
- `mail.py` via Resend of SMTP: **alleen meldingen aan Mathias, nooit aan klanten.**
- `printagent.py` (lokaal): PDF's van onFact afdrukken.

**Klant-facing flow: ONTBREEKT.**
- Er is geen formulier en geen webhook.
- Een factuur achteraf werkt vandaag zo: Mathias plakt de mail van de klant in `app.py`. `gegevens.ontleed(tekst)` herkent bedrijfsnaam, btw-nummer en adres met regex en VIES, en `/voorstel` bouwt het voorstel.
- De motor behandelt alleen btw-nummers die al bij de checkout zijn opgegeven.

**Veilige readers voor AI**
- `db.bestaand_document_voor_order(order_naam)`: bestaat er een factuur, met welke status en welk nummer, en is ze verzonden?
- `motor.beoordeel(order, …)`: waarom er (nog) geen factuur is. Schrijft zelf niets, maar roept wel VIES en onFact aan.
- `vies.controleer()`, `gegevens.ontleed()`, `Shopify.order()`.

**Writers:** `Motor._voer_uit` (gepoort door de stand), plus de `app.py`-routes voor onFact aanmaken, verzenden, verwijderen en corrigeren.

**Classificatie: BESTAAT — AANPASSEN.**
- De AI kan hierop aansluiten als **intake** voor "ik wil een factuur met btw-nummer": gegevens verzamelen, `vies.controleer` en `gegevens.ontleed` hergebruiken, en een aandachtspunt of voorstel klaarzetten voor Mathias.
- De AI mag nooit zelf een factuur aanmaken.
- Nodig: een HTTP-leesdienst of gedeelde database, want de motor op Railway heeft geen API. Ook de ontbrekende templates moeten erbij.

---

## E. `/home/user/padelmq/padelmq-stockprice` — Voorraad- en locatiegestuurde prijzen

**Doel.** Voor ballendozen (producten met de tag `auto-stock-price`) automatisch prijs, verzendprofiel en Europa-beschikbaarheid zetten op basis van de voorraad per locatie. Daarnaast twee nevenfuncties:
- een express-motor (tag `hide_express_be_nl` op producten met `stock_spain`);
- een dagelijkse scrape van de publieke Tienda-prijs voor 16 ballendozen.

**Stack en hosting**
- Eén bestand, `server.js`: Node ≥ 18, zonder dependencies, eigen HTTP-server.
- **Hosting is niet vastgelegd** (geen railway.json).
- Shopify via een statisch `SHOPIFY_ADMIN_TOKEN`, API 2026-01.
- `APPLY_CHANGES=true` is nodig om echt te schrijven. Scheduler via `RECONCILE_INTERVAL_MINUTES`.

**Datamodel:** geen database. Productmetafields in namespace `stockprice`: enabled, price_a, price_b, market_surcharge, eu_be_price, competitor, competitor_ship, cost, tienda_price, tienda_at, locked, state, eu_state, log.

**Locaties en verzendprofielen**
- België: Kampenhout (`gid://shopify/Location/99030794589`) en ShopWeDo (`111552692573`).
- Spanje, dropship (`109744292189`).
- Verzendprofielen: Algemeen (gratis vanaf €100) en Ballendozen (doostoeslag).
- Europa: aparte prijslijst en publicatie.

**Logica**
- `availableAt()` en `decideState()` geven `stock-be` (Prijs A), `stock-es` (Prijs B, doostoeslag) of `stock-leeg`.
- `decideEuropa()` bepaalt de Europa-prijs en -beschikbaarheid.
- De prijs wordt ook teruggezet als iets anders hem wijzigde.

**Mutaties:** `productVariantsBulkUpdate`, `deliveryProfileUpdate`, `priceListFixedPricesAdd`, `publicationUpdate`, `metafieldsSet`/`Delete`, `tagsAdd`/`Remove`.

**Endpoints**
- `GET /`: dashboard, zonder authenticatie.
- `GET` en `POST /api/products` (`?pw=`).
- `/api/reconcile`, `/api/express`, `/api/tienda` (`CRON_SECRET` of pw).
- **Beveiliging:** als `DASHBOARD_PASSWORD` leeg is, geeft `checkPw` altijd toegang, ook tot de inkoopprijs (`cost`).

**Classificatie**
- **De app zelf: NIET HERGEBRUIKEN** als AI-component. Het is een writer, alleen voor ballendozen, en hij toont kostprijzen.
- **De regel "voorraad in België vs dropship vanuit Spanje": BESTAAT — AANPASSEN.** Die is bruikbaar als levertijdregel: `availableAt`/`decideState`, of `stockprice.state` rechtstreeks uit Shopify lezen.
- **Wie de voorraad op de locatie "Spanje" in Shopify vult, staat in geen van de vijf repo's.** Vermoedelijk padelmq-pro of siemons.

---

## Samenvatting: klantvraag → welke repo of functie levert het feit

| Klantvraag | Bron vandaag (repo · bestand · functie) | Classificatie |
|---|---|---|
| **Orderstatus** | Beste reader: factuurmotor `shopify_client.py` `Shopify.order(ordernummer)` (financiële en fulfilmentstatus, refunds, cancelledAt, fulfillments). Alternatief: dagontvangsten `src/shopify.py` `fetch_orders_by_name` (alleen financieel). Er is nergens identiteitsverificatie van de klant. | AANPASSEN (klant-facing reader en verificatie ONTBREKEN) |
| **Tracking per orderregel** | Shopify-fulfillments hebben tracking per fulfillment, niet per regel. De tracking-tool zet één fulfillment over het hele fulfillment order. `mapping.json.products` bevat de ICP-productlijnen per Tienda-zending (heuristische koppeling). | ONTBREEKT (per regel); per order: tracking-repo AANPASSEN (read-endpoint per ORD) |
| **Split shipment** | tracking `siblings_for_order`, `auto_tracking_for`, `cmd_koppel`: deelpakketten samengevoegd, meerdere nummers op één fulfillment. Automatisch geweigerd en op "manueel" gezet. | BESTAAT deels — AANPASSEN |
| **Factuur aanvragen** | factuurmotor `db.bestaand_document_voor_order`, `motor.beoordeel`, `gegevens.ontleed`. dagontvangsten `invoices.InvoiceIndex.is_invoiced` en `onfact.OnFactClient.check`. Geen klant-facing intake. | Lezen: DIRECT HERGEBRUIKEN. Aanvraagflow: ONTBREEKT |
| **Btw (nummer, validatie, tarief)** | factuurmotor `vies.controleer`, `motor.btw_uit_order`, `gegevens.ontleed`. dagontvangsten `RawOrder.country`/`tax_lines` (OSS-leverland). | BESTAAT — AANPASSEN (dienst zonder API) |
| **Retour** | Geen retour- of RMA-logica, geen retourbeleid. Wel: refunds lezen (`src/refunds.py`), creditnota bouwen (`builder.bouw_creditnota`), inbox-triage die retourmails als "actie" markeert. | ONTBREEKT |
| **Racketspecificaties** | Engine `kennis.effectieveWaarden` en `padelmq_engine.spec`/`provenance` (alleen Engine-producten). Bestaande catalogus: alleen `custom.vorm/gewicht/balans/kern/racket_oppervlakte/niveau_speler/type_spel/sweetspot/pro_players` (vrije tekst, zonder bron) en `shopify.racket-*`-taxonomie. | Engine: AANPASSEN. Bestaande catalogus: ONTBREEKT (geen bron per feit) |
| **Racket DNA** | Engine `racketDna.haalDnaProfiel`, `dnaModel.berekenDna`, `naarPubliekePresentatie`, metafield `padelmq_engine.dna` (dna-v5, 1,5–8,5 intern / 70–100 % publiek). Oude `custom.kracht/controle/comfort` zijn handmatige iconen, geen DNA. | BESTAAT — AANPASSEN (alleen Engine-rackets) |
| **Voorraad bij de bron (Tienda)** | Engine `tienda_variant_stock_observations` via `laatsteTiendaVariantVoorraad(candidateId)` (alleen Engine-kandidaten). Shopify-voorraad op locatie "Spanje (dropship)" (stockprice `availableAt`); wie die synchroniseert staat niet in deze repo's. Master `/api/tienda-lees` wordt door de Engine gebruikt. | AANPASSEN / deels ONTBREEKT |
| **Levertijd** | Geen feit. Benaderingen: stockprice `decideState` (stock-be vs stock-es), metafields `custom.levertijd` en `custom.preorder_datum` (eigenaar onbekend), carrier-ETA `ups_est` in tracking `mapping.json`. | ONTBREEKT (regel en bron moeten ontworpen worden) |

**Voor de Mathias Copilot (intern, read-only) zijn deze bronnen er al:**
- tracking `GET /api/status`;
- dagontvangsten `/api/aandacht`, `/api/late-facturen` en `/api/verkeerslicht`;
- de aandachtslijst van de factuurmotor (`db.aandachtslijst()`, alleen via de database);
- Engine: conflicten en de reviewwachtrij.

**Schrijfacties die geen enkele assistent mag aanroepen:**
- tracking `/sync`, `/koppel`, `/afvink`;
- factuurmotor `_voer_uit` en de onFact-routes;
- Scrada-boeking;
- stockprice `POST /api/products` en `/api/reconcile`;
- de publicatiepoort van de Engine.
