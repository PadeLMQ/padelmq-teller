# Inventarisatie PadeLMQ Master (`/home/user/padelmq-pro`), met het oog op een AI-klantenservice-assistent en "Mathias Copilot"

Alles hieronder komt uit de code op `main` (HEAD `4a3de56`, werkboom schoon). Wat ik niet kon zien: de runtime-env van Railway (welke flags aan staan) en de productie-database.

## Samenvatting vooraf
- **Master is volledig intern.** Het is een prijs-, voorraad- en VIP-engine voor één operator (Mathias). Er is geen enkele klant-facing interface, geen klantdata en geen orderdata per klant.
- **Willie is een interne pricing-collega.** Hij draait op OpenAI chat-completions met function calling, een browser-microfoon en OpenAI TTS. Hij is een sterk vertrekpunt voor de "Mathias Copilot" en is niet geschikt als klantassistent.
- **Wat een klant-AI wel kan gebruiken:** productzoeken, de actuele prijs en VIP-prijs, de verkoopbaarheid per variant (fail-closed), de Tienda-brontoestand en het patroon van feitenbewaking ("ONBEKEND is een antwoord", de assistent rekent niet zelf).
- **Wat volledig ontbreekt:** orders per klant, fulfilments en tracking per order, een levertijdbelofte in dagen, retour- en garantiebeleid, een e-mailinbox en klantgesprekken.

---

## 1. WILLIE

**Wat is het?** "Willie Lizier, de pricing-medewerker van Mathias". Hij is intern: alle `/api/willie`-routes eisen `isAuthed()` (een ingelogde sessie), zelfs lezen. Het sync-secret is daar niet genoeg. Een gesprek hangt altijd aan een "vraag" (`willie_vragen`), die Willie zelf aanmaakt of die Mathias start vanuit elk scherm.

**Bestanden en belangrijkste exports**
- `src/lib/willie/gesprek.ts`
  - `praat(vraagId, vanMathias, kanaal, denker=openaiDenker, kijktNu)` → `GesprekUitslag`
  - `systeemPrompt(v, policyVersie, taal, kijktNu)`
  - `openaiDenker({systeem, gesprek, ctx})`
  - `denkStand()`, `gesprekVoor(vraagId)`, `voegBeurtToe(...)`
- `src/lib/willie/gereedschap.ts` (1384 regels): `GEREEDSCHAP[]`, `gereedschapSchema()`, `gebruik(naam, args, ctx)`
- `vraag.ts`
  - `stelVraag`, `beantwoord`, `magAfsluitenVia(vraag, kanaal)`, `openVragen`, `teMelden`, `willieStatus`
  - kanalen: `chat | voice | telegram | master`. Voor Telegram bestaan alleen kolommen, er is geen bot-code.
- `gesprekStarten.ts`: `startGesprek({productId, opening})` en `productContext(productId)`. Dat laatste is het cijferblok per variant: kostbasis, vloer, eigen voorraad, vaste overrides van Mathias.
- `policy.ts`: `maakConcept`, `keurPolicyGoed(versie, door, "master")`, `actievePolicy`, `mandaatVoor(categorie)`, `rondAfB2C`, `b2cStaartToegestaan`. Dit is het versioned mandaat per categorie. Een ontbrekende regel heet `onbepaald` en blokkeert de autonomie.
- `rem.ts`: `remStand`, `zetRem(stand, door, reden, "master")`, `magSchrijven()`, `magAnalyseren()`. Drie standen (`vrij`, `pauze`, `stop`), opgeslagen in de DB, fail-closed naar STOP.
- `regelBevestiging.ts`: `vingerafdrukVoor`, `legVoorstelNeer`, `neemBevestiging(vingerafdruk, beurtId)`. Een voorstel moet in een eerdere beurt gedaan zijn dan de bevestiging, is 60 minuten geldig en werkt maar één keer.
- `uitvoeren.ts`: `voerBeslissingUit({vraagId, productId, b2c, vip, beslissing, reden, live, risico})`. Loopt via `zetHandmatigePrijs` → `zetPrijsExact`, gegate op `live && WRITE_ENABLED()`, en `bevestigVip` → `zetVipExact`. Doet een verse lezing, compare-and-swap en een na-verificatie, en schrijft een audit in `willie_uitvoering`.
- `les.ts`: `noteerLes`, `vulRedenAan`, `bevestigLes`, `spreekLesTegen`, `lessenVoor`, `lessenOverzicht`, `contextVoorProduct`. Dit is de leerlaag: observatie → kandidaat_regel → bevestigde_regel / uitzondering, met een confidence en `DREMPEL_BEVESTIGD` = 0,65. Lessen worden alleen als overweging gebruikt, bedragen nooit.
- `bewijs.ts`: `betwistBewijs`, `bevestigBewijs`, `betwisteSleutels`. Wat Mathias afkeurt (bijvoorbeeld `concurrent:41`) valt weg uit de benchmark, aan de bron.
- `herkomst.ts`: `toets()`, `magGedragslimietOverslaan`, `ECONOMISCHE_GRENZEN`. Een menselijke opdracht mag stap-limieten passeren, maar nooit break-even, MAP of een onvolledige kostbasis.
- `modelKennis.ts`: `leerUitCorrectie`, `soortVanWoord`, `BEWEZEN_RUIS`. Leert welke woorden een ander racketmodel betekenen (tabel `model_kennis`).
- `identiteit.ts`: `vergelijkIdentiteit(onsTitel, hunTitel)` → `zelfde | anders | te_controleren`.
- `categorie.ts`: `onderzoekCategorie`, `categorieVoorstellen(limiet)`. Stelt een producttype voor uit titel en merk, met een drempel `CATEGORIE_DREMPEL` van 0,75.
- `instelling.ts`: `leesInstelling`, `zetInstelling`, `spreekTaal`, `zetSpreekTaal` (tabel `willie_instelling`).
- `afsluiting.ts`: `klinktAlsAfsluiting(tekst)`. Een vaste lijst afscheidszinnen: sluit het gesprek (de microfoon), nooit de vraag.
- `spraak.ts`: `stemInstelling`, `stemToegestaan` (gekloonde stem alleen met `WILLIE_STEM_TOESTEMMING`), `korteSpreektekst`, `spreekTempo` (1,25), `stilteVoorEindeBeurt` (2200 ms).
- `spreektekst.ts`: `veiligeSpreektekst(ruw)`. Een filter dat URL's, EAN's en codes wegknipt vóór TTS.

**Routes**
- `src/app/api/willie/route.ts`
  - GET: status, `?spreek=1`
  - POST: `?praat`, `?start`, `?antwoord`, `?uitvoeren`, `?rem`, `?intrekken`, `?vraag`, `?categorie`, `?lessen`, `?taal`
- `src/app/api/willie/stem/route.ts`: POST tekst → mp3 via `https://api.openai.com/v1/audio/speech`. Model `WILLIE_TTS_MODEL` (standaard `gpt-4o-mini-tts`), stem `WILLIE_TTS_VOICE` (standaard `onyx`), met een Vlaamse toon-instructie.

**UI**
- `src/app/willie/page.tsx`
- `src/components/WilliePaneel.tsx` en `WillieStrip.tsx`: een globaal paneel via `Zijbalk.tsx` en `Dashboard.tsx`.
- `src/components/willie/useWillie.ts` en `stem.ts`: STT met de browser-`SpeechRecognition` (nl-BE); TTS via de serverroute, met de browserstem als terugval.

**LLM**
- `openai` SDK v4, `chat.completions.create`.
- Model: `WILLIE_MODEL` || `OPENAI_MODEL` || `gpt-4o-mini`, temperature 0,4.
- Gereedschapslus van maximaal 8 stappen; tool-output wordt afgekapt op 6000 tekens. Daarna volgt één laatste call met `response_format: json_object`.
- Antwoordcontract: JSON `{zeg, toestand: doorpraten|afgerond, nieuwe_regel, samenvatting, zeg_gesproken?}`.

**Gereedschap (21 tools)**
- **Lezend:** `prijsdossier`, `onderzoek_pagina`, `zoek_concurrenten`, `onderzoek_verzending`, `beoordeel_winkel`, `zoek_product`, `prijsbeeld`, `live_in_shopify`, `concurrenten`, `verkoop`, `zoek_concurrenten_opnieuw`, `eerdere_keuzes`, `vip_vloer`.
- **Muterend, alleen met `ctx.vanMens`:** `keur_bewijs_af`, `voeg_concurrent_toe`, `voorraadbel`, `zet_prijsregel` (met een bevestiging in twee beurten), `onthoud_keuze`, `onthoud_reden`, `voer_prijs_uit` (twee beurten, plus een aparte risicobevestiging onder de vloer of bij een onbewezen kost).
- `ctx.vanMens` en `beurtId` komen uit de gesprekslaag, niet uit de argumenten van het model.

**Kern van de systeemprompt** (`gesprek.ts:259` e.v., letterlijk ingekort):
```
Je bent Willie Lizier, de pricing-medewerker van Mathias bij PadelMQ.
HOE JE PRAAT: - Kort. Twee, hooguit drie zinnen. ...
- Stelt hij je een vraag, dan beantwoord je die met de gegevens hieronder.
  Weet je het niet, dan zeg je dat en niet iets plausibels.
JE HEBT GEREEDSCHAP. GEBRUIK HET. ... Pas antwoorden nadat je gekeken hebt.
GAAT HET OVER EEN PRIJS? ROEP prijsdossier AAN. ALTIJD, EERST.
VIER VRAGEN DIE JE NOOIT STELT: 'Welke concurrent zal ik eerst controleren?' ...
NOOIT HARDOP: webadressen, artikelnummers, EAN's ...
GETALLEN: REKEN NIET ZELF.
- Noem alleen bedragen en percentages die hieronder of in een
  gereedschapsantwoord LETTERLIJK staan.
- Staat een marge nergens, dan zeg je dat ze onbekend is -- niet nul.
- Staat er ... dat de kostbasis NIET definitief is, dan is dat onbewezen.
MEERDERE MATEN VAN HETZELFDE ARTIKEL: ... VRAAG het dan eerst.
  Kies er nooit zelf een ... Dezelfde SKU bewijst NIET dezelfde variant.
[schermBlok][lessenBlok][variantBlok] WAT JE WEET OVER DIT PRODUCT: ...
OORDEEL OVER DE TOESTAND: ... Bij twijfel: doorpraten. Een EERSTE antwoord rondt nooit af.
Geeft hij een commerciële regel ... zet die dan in 'nieuwe_regel' ... Verzin er nooit een.
Antwoord uitsluitend als geldige JSON: {"zeg": ..., "toestand": ..., ...}
```

**Feitenbewaking in de code, niet alleen in de prompt**
- De tools geven expliciet `null` of "ONBEKEND" met een `let_op`-reden, en rekenen marges zelf uit via `kostbasis()`.
- Betwist bewijs verdwijnt aan de bron (`telt_mee=false`); ingetrokken varianten worden geweigerd (`historischeRij()`).
- Verouderde concurrentprijzen worden gemarkeerd (`beoordeelVersheid`).
- Een eerste beurt kan niet afronden; `magAfsluitenVia` staat alleen het kanaal `master` toe om een GO af te ronden.
- Het URL-filter werkt op de output. Een bevestigde uitvoering komt als `gesprek_regel` letterlijk uit de na-verificatie.

**SQLite-tabellen (via eigen `ensure*Schema`)**
- `willie_vragen`: onder meer sleutel, product_id, variant_gid, grond, vraag, context_json, voorstel, spreektekst, zekerheid, mens_vereist, antwoord, antwoord_kanaal, status, gemeld_voice_op, gemeld_telegram_op, telegram_bericht_id.
- `willie_gesprek`: id, vraag_id, rol, tekst, kanaal, moment.
- `willie_policy`, `willie_rem`, `willie_rem_log`, `willie_regel_voorstel`, `willie_uitvoering`, `willie_les`, `willie_bewijs`, `willie_instelling`, `model_kennis`.

**Shopify:** leest via `leesVersePrijsEnVip` (productVariant price + `symo.vip_price`) en schrijft via de bestaande prijs- en VIP-schrijvers.

**Tests:** 10 `tests/willie*.test.ts` (349 it/test-aanroepen) met een geïnjecteerde nep-`Denker`, zonder netwerk. Daarnaast `e2e/master/willie.spec.ts` en `willieInMaster.spec.ts` (browser, server gestubd, `OPENAI_API_KEY` leeg).

**`scripts/acceptatieWillie.ts` is geen LLM-evaluatieset.** Het is een read-only script dat `onderzoekPagina` en `vergelijkIdentiteit` tegen zes echte concurrent-URL's van één racket draait. Er bestaat geen golden set voor Willie-antwoorden.

**Classificatie**
- Voor Mathias Copilot: **BESTAAT — AANPASSEN**. Gesprekslaag, gereedschap, rem, bevestiging in twee beurten, lessen en voice zijn precies het copilot-patroon, maar volledig op pricing gericht.
- Voor de klantassistent: **NIET HERGEBRUIKEN** als geheel. Het is een persona voor de interne operator; de tools geven kostprijzen, marges en concurrentie terug. Hergebruik wel het patroon: tool-loop, `let_op`/ONBEKEND-contract, `veiligeSpreektekst` en `klinktAlsAfsluiting`.

## 2. OpenAI-infrastructuur

- **`src/lib/openai.ts`:** alleen `generateDescription(input: GenerateInput): Promise<GenerateOutput>`. Shoptekst-generator: `OPENAI_MODEL` || `gpt-4o-mini`, temperature 0,7, JSON-mode, "Verzin geen specificaties die niet in de brondata staan". Aangeroepen door `src/app/api/import/generate/route.ts`.
- **Overige OpenAI-aanroepen:** `willie/gesprek.ts` (chat plus tools) en `api/willie/stem` (TTS via rauwe fetch).
- **Env:** `OPENAI_API_KEY`, `OPENAI_MODEL`, `WILLIE_MODEL`, `WILLIE_TTS_MODEL`, `WILLIE_TTS_VOICE`, `WILLIE_STEM_*`, `WILLIE_SPREEKTAAL`, `WILLIE_STILTE_MS`.
- **Audit en kosten:** er is geen log van AI-calls, geen tokengebruik en geen kostenregistratie (geen `usage`/`total_tokens` in de code). Alleen de gespreksbeurten staan in `willie_gesprek`. Een bruikbaar patroon is wel `provider_gebruik` in `src/lib/markt/provider.ts` (kost per externe zoekprovider-call).
- **onnxruntime-node** is geen LLM. Het wordt gebruikt voor ISNet-achtergrondsegmentatie van productfoto's (Mechelen): `src/lib/isnetSegmentatie.ts`, met het model `isnet-general-use.onnx` dat wordt gedownload naar `<data>/modellen` of `ISNET_MODEL_PATH`.
- **`achtergrondVerwijdering.ts`:** `verwijderAchtergrond(buffer)`, puur `sharp`-vloedvulling, geen AI. Gebruikt door `afbeeldingRouter.ts` en `winkel2Afbeeldingen.ts`.
- **Classificatie:** **BESTAAT — AANPASSEN.** Er is een dunne client, maar geen centrale wrapper, AI-audit of kostentracking.

## 3. Shopify-clients

**`src/lib/shopify.ts`**
- Exports: `shopifyQuery<T>(query, vars)`, `shopifyConfigured()`, `shopifyAuthDiagnostics()`, `createShopifyProduct(p)`, `updateShopifyPrice(...)`.
- Auth: `SHOPIFY_ADMIN_TOKEN` óf `SHOPIFY_CLIENT_ID`/`SECRET`; API-versie standaard `2025-10`.
- Gebruikt voor klassieke import, schrijvers en metafieldsSet (VIP).

**`src/lib/shopifyOrgAuth.ts`**
- Exports: `adminGraphql<T>(query, vars)`, `adminGraphqlWinkel(cfg, ...)`, `tokenVoor`, `HOOFDWINKEL`, `shopReadTest()`.
- Client-credentials met `SHOPIFY_WATCHDOG_CLIENT_ID`/`SECRET` (terugval op `SHOPIFY_CLIENT_*`), versie `2025-01`, in-memory tokencache, THROTTLED-retry.
- Dit is de aangewezen read-client voor nieuwe modules.

**`shopify2.ts` en `winkel2*.ts`: "winkel 2" is Tienda PadelPoint Mechelen**
- Een tweede Shopify van dezelfde vennootschap: een fysieke zelfservicewinkel in Muizen.
- Master spiegelt daar alleen B2C-prijzen en kopieert producten, vertalingen en afbeeldingen. Voorraad schrijft Master er nooit.
- OAuth-offline token staat in `winkel2_auth`; scopes via `GEVRAAGDE_SCOPES` = `read_products,write_products,write_publications,write_translations`.

**`shopifyImport.ts`**
- Leest `products { id title status handle vendor productType descriptionHtml tags featuredImage metafield(custom.tiendapadelpoint_url) metafield(custom.standaardlocatie) variants { id sku barcode price inventoryQuantity inventoryItem selectedOptions } }` → tabel `products`, één rij per variant (sinds 25-09).

**Scopes**
- `vipKeten.vipKetenOnderzoek()` leest runtime `currentAppInstallation.accessScopes`.
- Commentaar in `vipOrderDiagnose.ts` noemt als bewezen: `read_inventory, read_locations, read_orders, read_products, write_inventory`.
- **Tegenspraak:** CLAUDE.md zegt "read_orders is vandaag nog niet verleend; zie ACTIVATIEPLAN_READ_ORDERS.md". Dat bestand bestaat nergens in de repo. De gereedschapslaag noemt "Master heeft vandaag 72 dagen historiek", wat erop wijst dat orders gelezen worden.
- `read_all_orders` ontbreekt zeker, dus historie reikt maximaal 60 dagen terug.
- `read_customers` en `read_fulfillments` worden nergens gebruikt of gevraagd.

**Order-, fulfilment- en customer-readers**
- Er zijn precies twee order-readers:
  - `verkoop.ts` `ORDER_QUERY`: id, createdAt, cancelledAt, test, lineItems (sku, variant, bedragen), refunds.
  - `vipOrderDiagnose.ts`: lineItems met discountAllocations.
- Beide vragen bewust geen klant-, adres- of fulfilmentvelden.

**Tabel `products` (cache)**
- Basis: sku, title, brand, type, description, image_url, source_url, cost_price, source_price, stock (= LEVERANCIERSvoorraad), vip_price, price, min_price, currency, reprice_*, shopify_product_id/variant_id/inventory_item_id, sync_status, last_synced_at, created_at/updated_at.
- Via `addColumn`: shopify_handle, last_scanned_at, priority, laatste_marktronde, urgent, ean, on_promo, vaste_prijs(_op/_door), regular_cost, oos_strategy, oos_uplift_pct, max_auto_drop_pct, comp_shipping_counts, min_margin_pct, min_winst_eur, shipping_note, shipping_cost, tienda_below_*, shops_below_*, maat_optie, identiteit_ingetrokken_op.
- `price` en `vip_price` worden elke 180 minuten door `vipWatch` gelijkgezet en bij elke verse lezing via `prijsWaarheid.verzoenPrijs`.

**Classificatie**
- `adminGraphql`: **BESTAAT — DIRECT HERGEBRUIKEN** voor reads.
- De products-cache: **BESTAAT — AANPASSEN**. Dit is een operator-kopie en geen storefront-bron.

## 4. Orders en verkoop

- **`src/lib/verkoop.ts`** (2242 regels). Belangrijkste exports:
  - `refreshVerkoop(...)`, `productInzicht(productId, dagen)` → `ProductInzicht`
  - `tempoVoorProduct`, `historiekDagen`, `dagstatus(datum)`, `verkoopVergelijking`, `verkoopStatus`
  - `voorraadNiveau`, `VOORRAAD_WEKEN`
- **Tabellen:**
  - `verkoop_dag`: datum, sleutel, sku, variant_gid, titel, aantal, omzet.
  - `verkoop_dagstatus`: datum, volledig, reden, bereikbaar_vanaf, vastgesteld_op.
  - `verkoop_sync`: een rij met ~30 tellers.
  - `verkoop_lock`.
- **Wat er wordt opgeslagen:** alleen per dag × variant opgetelde aantallen en omzet, netto na annuleringen, testorders en refunds. Geen order-ID's per klant, geen klanten, geen fulfilments.
- **Flag:** `ENABLE_VERKOOP_SYNC` is opt-in (`scheduler.ts`); daarnaast kan de sync handmatig via `/api/verkoop`.
- **Route:** `src/app/api/verkoop/route.ts` (GET `?product=&dagen=`, `?bestsellers`, `?hardlopers`, `?vergelijk`, `?refresh`), met `authorizeRequest`.
- **Classificatie:**
  - Voor klantvragen ("waar is mijn order"): **ONTBREEKT**.
  - Voor Copilot ("hoeveel verkocht"): **BESTAAT — DIRECT HERGEBRUIKEN**.

## 5. Tracking

- **Code:**
  - `src/lib/tracking.ts`: `haalTrackingStatus(): Promise<TrackingStatus>`, een GET op `${TRACKING_URL}/api/status` met header `x-tracking-secret`.
  - `src/app/api/tracking/route.ts`: GET met `authorizeRequest`.
  - `src/app/tracking/page.tsx`.
- **Welke data:** alleen geaggregeerd. `live_writes`, laatste run, aantallen `te_koppelen`/`gekoppeld`/`voorraad`/`manueel`, plus een lijst `aandacht_nodig` met klantnaam, postcode, stad, vervoerder en reden. Die lijst wordt getoond en niet opgeslagen.
- **De aparte service `/home/user/padelmq-tracking`** (Python/Flask) doet het echte werk:
  - leest leveranciersmails via IMAP en ICP-trackingpagina's (Playwright);
  - leest open Shopify-orders (`fulfillment_status:unfulfilled`);
  - maakt `fulfillmentCreateV2` met trackingInfo (UPS, DHL Express, GLS, Nacex);
  - bewaart zijn data in `mapping.json` op een eigen volume;
  - staat in dry-run (`TRACKING_LIVE_WRITES=false`); de lokale Windows-tool is nog de actieve.
- **Master kent geen trackingnummer per order.**
- **Classificatie:** **BESTAAT — AANPASSEN**, via de tracking-service en niet via Master. Master heeft enkel een statusproxy.

## 6. Voorraad

- **`src/lib/voorraadContext.ts`**
  - `voorraadbasis(productId): VoorraadBasis`
  - `eigenVoorraad(productId): number|null`: alleen Kampenhout/ShopWeDo; null bij dropship of bij een meting ouder dan 72 uur.
  - `beschikbaarNu(productId): number|null`: dropship telt mee. Telt op over `product_gid`, dus over alle maten samen.
- **`src/lib/voorraadWatch.ts`**
  - `veiligVerkoopbaar(b: Beschikbaarheid): boolean`: alleen `bevestigd_beschikbaar` of `eigen_locatie` geeft true.
  - Verder: `bronVoorVariant`, `probeTiendaSizes(url)`, `resolveAssigned`, `classify`, `oversellSignalen`, `startVoorraadWatch`.
- **Tabel `stock_check`** (per variant):
  - variant_gid, product_gid, titles, vendor, product_type, standaardlocatie, tienda_url, source, qty_es, qty_be, qty_sw, shop_qty, source_stock, source_ok, diff, status, reason, proposed_qty, last_source_check_at, shop_synced_at;
  - plus: sku, barcode, maat_optie, beschikbaarheid, beschikbaarheid_reden, bron_herkomst, enige_variant, es_gekoppeld, laatst_bron_ok_at.
- **Locaties:**
  - `voorraadPoort.ts`: `SPANJE_LOCATIE = gid://shopify/Location/109744292189`, `locatieSoort()`. Master schrijft uitsluitend naar Spanje.
  - `standaardlocatie.ts`: constanten ShopWeDo, Shopwedo Solo, Kampenhout, Spanje, en `bepaalStandaardlocatie(sw, be, es)`.
  - `locatieSnel.ts`: een snelle metafield-herberekening elke 10 minuten.
- **Antwoord op "kan een klant dit vandaag bestellen en wanneer geleverd?"**
  - Het eerste deel wel, per variant: `stock_check.beschikbaarheid` + `veiligVerkoopbaar()`. Product-breed kan het met `beschikbaarNu()`, maar dat is geen maatuitspraak.
  - "Wanneer geleverd" beantwoordt geen enkele functie. Zie 7.
- **Classificatie:** **BESTAAT — DIRECT HERGEBRUIKEN** voor verkoopbaarheid per variant, fail-closed. Let op de versheid van de data: bron maximaal 12 uur oud.

## 7. Levertijd en verzending

- **`shipping.ts`:** tabellen `shop_shipping` (per CONCURRENT-shop en land: standard_cost, free_threshold, delivery_min/max, delivery_raw, confidence) en `competitor_effective`. Exports: `effectiveForProduct(productId, land)`, `normalizeDelivery(raw)`, `besteVerzending`. Dit gaat over concurrenten, niet over PadeLMQ.
- **`concurrentVerzending.ts`:** `verzendingTeltMee()`, over concurrenten.
- **`shippingRefresh.ts`:** `probeShopCountry()`, winkelwagen-probe bij concurrenten.
- **Tabel `verzendoptie`** (`prijsParameters.ts`): PadeLMQ's eigen logistieke KOST per optie (label, bedrag_ex_btw, aard, drempel, vloer_bedrag). Dit is een kostenmodel, geen klantbelofte.
- **`custom.standaardlocatie`:** het metafield bepaalt de verzendtijdclaim op de website. Master berekent de waarde (Spanje, Kampenhout, …), maar de vertaling naar "X werkdagen" staat in het Shopify-thema en niet in Master.
- **Classificatie:** een klantgerichte levertijdberekening **ONTBREEKT**. Het locatielabel per product: **BESTAAT — AANPASSEN**.

## 8. Prijzen en VIP

- **Juiste actuele prijs + VIP van een variant:** `leesVersePrijsEnVip(variantGid)` in `src/lib/vipSchrijver.ts`.
  - Leest live `productVariant { price, metafield(symo.vip_price), product{id,status} }` via `adminGraphql`.
  - Verzoent tegelijk de lokale kopie (`prijsWaarheid.verzoenPrijs/verzoenVip`).
  - Cache-alternatief: `products.price` en `vip_price` (maximaal ongeveer 180 minuten oud).
- **Overige modules:**
  - `vipWatch.ts`: `refreshVip`, `classifyVip`, `vipAdvies`, `startVipWatch`. Tabel `vip_check`: variant_gid, price, purchase, vip, logistiek, gap, floor_hard, break_even, status, sku, test_beschikbaar, …
  - `vipKeten.ts`: `vipKetenOnderzoek` (scopes plus steekproef).
  - `vipVloer.ts`: `bewezenVipVloerVoorVariant`.
  - `prijsLezen.ts`: `leesPrijs` en `kiesVerkoopprijs`. Dit parseert concurrentpagina's, niet de eigen prijs.
  - `prijsAudit.ts`: `liveOpSku`, `auditVoorSku`, `prijsDriftSteekproef`.
- **Schrijven** gebeurt via `zetVipExact`/`schrijfVipVariant`, gegate op `VIP_SYNC_WRITE`.
- **VIP-kanttekening:** VIP is een klantgroepprijs (Symo `vip-club`). Welke klant VIP is, weet Master niet.
- **Classificatie:** `leesVersePrijsEnVip` is **BESTAAT — DIRECT HERGEBRUIKEN** (read-only). De rest is **NIET HERGEBRUIKEN**: het is interne marge-logica.

## 9. Productkennis

- **`productZoeken.ts`:** `zoekProducten(...)` → `Treffer[]` (score, `waarom`), fuzzy per woord over titel, merk, type, SKU en EAN, in het geheugen. Bruikbaar voor klantzoekvragen.
- **`catalogus.ts`:** `leesShopifyCatalogus`, `catalogusAudit`, `catalogusRonde`, `isUitgesloten`. Bepaalt welke producten in Master horen: ACTIVE en DRAFT, geen TESTRACKET.
- **`testracket.ts`:**
  - `isTestracketTitel`, `isTestracket(productId)`, `geenTestracketSql`.
  - 108 testracket-producten op EUR 10,00. Dat bedrag is de prijs van de testservice.
  - `custom.testracket=true` betekent "van dit model bestaat een testracket" (219 producten).
- **`bancontactApi.ts`/`bancontactStore.ts`:** betalingen voor de tester-top-up via de Bancontact Merchant API (alleen lezen), tabel `bancontact_testers` (payment_id, status, amount_cents, reference, … zonder naam of IBAN). Dit is de betaalkant van de testracket-service en wordt gelezen door de dagontvangsten-robot.
- **Overige:**
  - `racketDiagnose.ts`: `shopifyTrace`, `productTrace`, een live herkomsttrace met metafields(250), read-only.
  - `maatMatching.ts`: `maatGelijk`, `zoekMaatBijBron`.
  - `identiteit.ts`: `RUIS`, `KLEUREN`, `DOELGROEPEN`, `modelNummer`.
- **Product-type:** `src/lib/types.ts` volgt de kolommen van §3. Er zit geen enkel spec-veld in: geen gewicht, balans, vorm, EVA of materiaal.
- **Racketspecificaties** staan niet in Master. Ze bestaan in Shopify-metafields (`custom.vorm`, `custom.gewicht`, `custom.balans`, `custom.kern`, `padelmq_engine.spec_*`); dat blijkt uit `/home/user/padelmq-ai-product-engine/METAFIELD_AUDIT.md`, de aparte AI Product Engine.
- **Metafields die Master wél leest:** `symo.vip_price`, `symo.unit_cost`, `custom.standaardlocatie`, `custom.tiendapadelpoint_url`, `custom.testracket`, `mm-google-shopping.custom_label_0`.
- **`products.description`** bevat `descriptionHtml` uit de import, of een AI-shoptekst.
- **Classificatie:**
  - Zoeken en productidentiteit: **BESTAAT — DIRECT HERGEBRUIKEN**.
  - Specificaties en productadvies: **ONTBREEKT** in Master. De Product Engine en de metafields zijn de bron.

## 10. Tienda

- **`tiendaBron.ts`**
  - `tiendaStandVoorProduct(productId): BronStand`: toestand `bevestigd_beschikbaar | bevestigd_uitverkocht | niet_meer_gevonden | controle_mislukt`, met `magStemmen`, `reden`, `urenOud`, `varianten`, `beschikbaar`.
  - `tiendaOnlinePrijs(productId)`: actueel, `min10`, historisch.
  - Verder: `verdwenenLijst`, `linkControleLijst`.
- **`tiendaLeesdienst.ts`** + `GET /api/tienda-lees?url=&modus=anoniem|b2b`: één GET naar `tiendapadelpoint.com`, rauwe body. Eigen sleutel `x-tienda-lees-secret` (`TIENDA_LEES_SECRET` of een HMAC van `SESSION_SECRET`).
- **`tiendaKoppeling.ts`:** `tiendaKoppelingVerboden(gid)`, eigen artikelen zonder Tienda-bron (tabel `tienda_koppeling_verbod`).
- **`tiendaRol.ts`:** `tiendaRolAnalyse`, `tiendaVerzendMeting`. Tienda als leverancier versus als publieke concurrent; read-only.
- **`TIENDA_PROBE_PAUZE_MS`** (1200 ms) in `voorraadWatch.ts:2181` en `tiendaConcurrent.ts`. Tienda is de bottleneck.
- **Hergebruik voor "is het leverbaar bij de bron":** `tiendaStandVoorProduct()` en de per-variant `stock_check.beschikbaarheid`/`source_stock` (leveranciersvoorraad), maar alleen als interne indicatie. Live scrapen per klantvraag mag niet (CLAUDE.md verbiedt Tienda scrapen buiten de gecontroleerde scraper).
- **Classificatie:** **BESTAAT — DIRECT HERGEBRUIKEN** (DB-reads). De leesdienst: **NIET HERGEBRUIKEN** voor klantverkeer, vanwege rate-limit en B2B-sessie.

## 11. Policy, retour en garantie

- Er is geen centrale beleidsbron. Grep op retour, garantie, herroep, voorwaarden en "14 dagen" levert niets klantgerichts op.
- Het enige spoor staat in `mechelenBestelblok.ts`. Die herkent via regex het PadeLMQ-blok onderaan productbeschrijvingen ("🛒 Alles weten over je bestelling?", "🚀 Deliveries", links naar `…verzenden-retourneren`, WhatsApp +32 468 25 86 89) en vervangt het in Mechelen.
- De beleidsteksten leven dus in Shopify (pagina's, policies, beschrijvingen).
- `willie/policy.ts` is een pricing-mandaat, geen klantbeleid.
- **Classificatie:** **ONTBREEKT** (bevestigd).

## 12. Auth en API

**`src/lib/auth.ts`**
- `checkToken(token)`: tegen `DASHBOARD_TOKEN`.
- `createSessionCookie()` / `clearSessionCookie()`: HMAC met `SESSION_SECRET`, 30 dagen.
- `isAuthed()`.
- `authorizeRequest(req)`: sessie óf `SYNC_SECRET` (header `x-sync-secret` of `?secret=`), constant-time.
- `authorizeHealthRead(req)`: `HEALTH_TOKEN`, alleen `/api/health`.
- Er is één gedeelde login, geen gebruikers of rollen. `SESSION_SECRET` wordt gedeeld met de Product Engine.

**API-routes (60)** — `S` = `isAuthed`, `A` = `authorizeRequest`

| Route | Methoden | Auth | Doel |
|---|---|---|---|
| alerts | GET, PATCH | S | aandachtscentrum |
| auth/login, auth/logout | POST | — | sessie |
| bancontact/callback | GET, POST | eigen secret | Bancontact-callback |
| bancontact/poll | GET | eigen secret | poll |
| bancontact/status | GET | eigen secret | configuratiediagnose |
| bancontact/testers | GET | eigen secret | lijst voor de dagontvangsten-robot |
| brand-rules | GET, POST, DELETE | S | MAP en marge per merk |
| catalogus | GET, POST | A / S | catalogus-audit en ronde |
| discover | GET, POST | S | bulk concurrent-ontdekking |
| geschiedenis | GET, POST | S | activiteitenlog en nulmeting |
| health | GET, POST | health-token / S | gezondheid en noodstop |
| import/generate, oldapp, scrape, shopify | POST | S | AI-tekst, import, scrape |
| inventory | GET, POST | S | inventaris verzendvelden |
| keuring | GET, POST | A / S | keuring voorgestelde concurrenten |
| nacontrole | GET, POST | A / S | nacontrolelijst |
| new-arrivals | GET, POST, PATCH | S | nieuwe Tienda-artikelen |
| onderzoek | GET, POST | A / S | onderzoeksronde |
| pending | GET, POST | S | goedkeuringswachtrij grote dalingen (`pending_changes`) |
| pricesync | GET, POST | A / S | veilige prijs-sync |
| prijsactie | GET, POST | A / S | tijdelijke acties |
| prijsbeheer | GET, POST | A / S | prijsbeheer, read-only |
| prijsdossier | GET, POST | A / S | dossier voor Mathias en Willie |
| prijsparameters | GET, POST | A / S | commerciële parameters |
| products | GET, POST | S | lijst en tellers |
| products/[id] | GET, PATCH, DELETE | S | product |
| products/[id]/competitors, discover, publish, suppliers, sync | div. | S | productacties |
| qc | GET, POST | S | QC concurrenten |
| quickprice | GET, POST | S | snelle prijs |
| report | GET | S | dagrapport |
| review | GET, POST | A / S | productcontrole |
| shipping | GET, POST | S | verzendregels concurrenten |
| shops, shops/[id] | div. | A / S | winkels |
| stats | GET | S | dashboardcijfers |
| status | GET, POST | S | scanner-status |
| stocksync | GET | A / S | voorraadsync |
| sync | GET, POST | S | cron/bulk-sync |
| tienda-lees | GET | eigen secret | Tienda-leesdienst |
| tienda/status | GET | S | Tienda-login-diagnose |
| tracking | GET | A | tracking-statusproxy |
| verkoop | GET, POST | A / S | tempo en historiek |
| vip | GET, POST | A / S | VIP-bewaking en orderdiagnose |
| voorraad | GET, POST | A / S | voorraadwaakhond, `?audit=1` |
| voorraad/handmatig | GET, POST | S | handmatige voorraad |
| voorraadprijzen | GET, POST | A | proxy naar stockprice-service |
| voorraadsignaal | GET, POST | A / S | terug-op-voorraad-bel |
| willie | GET, POST | S | gesprek |
| willie/stem | POST | S | TTS |
| winkel2 | GET, POST | A / S | Mechelen-beheer |
| winkel2/afbeeldingen | GET | A | afbeeldingen Mechelen |
| winkel2/oauth | GET | A | OAuth-start |
| winkel2/oauth/callback | GET | HMAC + nonce | OAuth-callback |

Er is geen publieke of klant-API.

**Classificatie:** **NIET HERGEBRUIKEN** voor klantverkeer (één gedeelde admin-login). Een Copilot kan `authorizeRequest`/sessie hergebruiken.

## 13. Audit en goedkeuring

- **`goedkeuring.ts` bestaat niet.** `git log --all -- src/lib/goedkeuring.ts` is leeg; BEVINDINGEN.md §2 bevestigt dat het untracked is, net als signalen, cockpit en de vier andere adviesmodules.
- **Het GO-patroon dat wél in code bestaat:**
  - Willie: `regelBevestiging.ts` (voorstel in beurt N, bevestiging in beurt > N, 60 minuten, eenmalig) → `voerBeslissingUit` → `willie_uitvoering` en `prijs_handmatig_log`.
  - `rem.ts` en `noodstop.ts` (DB-persistent, fail-safe, met log).
  - `vasteOverride.ts` (alleen een menselijke actor).
  - `alerts.ts` `addPending`/`setPendingStatus` (tabel `pending_changes`, route `/api/pending`).
  - `voorstelKeuring.ts` → `beslis()` (drie uitkomsten, alleen TWIJFEL gaat naar Mathias).
- **Audit-sporen:** `price_sync_log`, `stock_sync_log`, `vip_wijziging_log`, `prijs_handmatig_log`, `winkel2_*_log`, `rollback_log`.
  - `geschiedenis.ts` `geschiedenis(...)` voegt ze samen.
  - `aandacht.ts` `meld(...)`: gededupliceerde meldingen per sleutel.
  - `watchdog.ts` `hartslag(...)`, `watchdogStatus()`.
  - `poorten.ts` `poortenStand()`: alle schrijfpoorten in één meting.
  - `health.ts` `gezondheid()`.
  - `prijsAudit.ts`: vergelijkt Master met live Shopify.
- **Classificatie:** **BESTAAT — AANPASSEN.** Het patroon "voorstel → bevestiging in een latere beurt → uitvoering via een bestaande gegate schrijver → na-verificatie → audit" is de reële blauwdruk voor Copilot-acties. Een generieke goedkeuringsmodule ontbreekt.

## 14. Achtergrond-workers en scheduler

- `src/instrumentation.ts` start 22 lussen:
  - scheduler (node-cron: 06:00 sync + rapport + verkoop als `ENABLE_VERKOOP_SYNC=true`; 14:00 bestsellers)
  - discoveryDriver, competitorRefresh, voorraadWatch, shippingRecheck, stockSync, priceSync, concurrentNachtbatch
  - vipWatch (elke 180 minuten), vipBewaking, winkel2Beheer, vipKloofWacht, prijsActie, catalogus, rediscovery
  - shopHerkansing, hardlopers, versheid, voorraadmelding, onderzoek
- Vlaggen: `ENABLE_SCHEDULER`, `ENABLE_DISCOVERY_DRIVER`, `ENABLE_PRICE_REFRESH`, `ENABLE_STOCK_WATCH`, `ENABLE_SHIPPING_RECHECK`, `ENABLE_VIP_WATCH`, `ENABLE_VIP_BEWAKING`, `ENABLE_VIP_KLOOF_WACHT`, `ENABLE_WINKEL*`, `ENABLE_PRIJSACTIE`, `ENABLE_CATALOGUS`, `ENABLE_REDISCOVERY`, `ENABLE_SHOP_HERKANSING`, `ENABLE_HARDLOPER_SYNC`, `ENABLE_VERSHEID_AANZET`, `ENABLE_VOORRAADMELDING`, `ENABLE_ONDERZOEK`, `ENABLE_LOCATIE_SYNC`, `ENABLE_PRODUCT_ARCHIVE`.
- Schrijfpoorten: `PRICE_SYNC_WRITE`, `ENABLE_STOCK_WRITE`, `VIP_SYNC_WRITE`, `PRICE_MIRROR_WRITE`, `MECHELEN_IMAGE_WRITE`, plus de noodstop.
- `workerGates.ts` en `WORKERS_FAIL_CLOSED` uit CLAUDE.md bestaan niet in de code.
- Alle lussen draaien in hetzelfde Next-proces.
- **Classificatie:** **NIET HERGEBRUIKEN.** Een AI-assistent moet geen lus in dit proces toevoegen.

## 15. E-mail

- `email.ts`: `emailConfigured()` en `sendMail(subject, html, to?)`. SMTP via nodemailer (`SMTP_*`, `REPORT_EMAIL`), alleen verzenden.
- Gebruikt voor het dagrapport (`scheduler.ts`), urgente terug-op-voorraad-meldingen (`sync.ts`) en de voorraadbel (`voorraadSignaal.ts`), allemaal naar Mathias.
- `ochtendrapport.ts`: `ochtendrapport()` levert JSON (cutover-status) en verstuurt geen mail.
- Er is geen IMAP, inbox of threading. Alleen de tracking-service leest een IMAP-mailbox, voor leveranciersmails.
- **Classificatie:** verzenden **BESTAAT — AANPASSEN** (triviaal, zonder templates of audit); inbox **ONTBREEKT**.

## 16. Tests en e2e

- **Vitest:** 207 `tests/*.test.ts` (+ `helpers.ts`), ongeveer 3143 it/test-aanroepen. Eén fork (`vitest.config.mts`), Shopify gemockt, een verse SQLite per test.
- **Structurele broncode-tests:** `veiligheid.test.ts`, `workersGestart.test.ts`, `playwrightVeiligheid.test.ts`.
- **Playwright** (`playwright.config.ts`), projecten `desktop`, `mobiel`, `storefront`, `productie`:
  - 20 spec-bestanden; `e2e/master/` draait tegen een wegwerp-DB met zaad (`e2e/zaad`);
  - `e2e/onderzoek/ketenDossier.ts` is diagnosegereedschap.
- **Poort:** `npm run poort` = typecheck + vitest + build + keurbuild + e2e.
- `npm run keuring` uit CLAUDE.md staat niet in package.json; er is alleen `keurbuild`.
- **Golden set:** geen enkele LLM-evaluatieset. `acceptatieWillie.ts`, `acceptatiePricing.ts` en `acceptatieKeten.ts` zijn read-only scripts tegen echte winkels.
- **Classificatie:** harnas en veiligheidstests **BESTAAT — AANPASSEN**; evaluatieset **ONTBREEKT**.

## 17. Deploy

- `Dockerfile`: node:20-bookworm-slim, `npm run build`, `npm run start`, planner via instrumentation.
- `railway.json`: Dockerfile-builder, restart ON_FAILURE.
- Volume op `/app/data`, `DATABASE_PATH=/app/data/padelmq.db`; ISNet-model in `/app/data/modellen`.
- `DEPLOY.md`: één instantie, planner aan. `CUTOVER.md`: overname van Siemons, over het vermijden van dubbele schrijvers.
- **SQLite:** `getDb()` is een singleton met WAL en `foreign_keys=ON`, zonder `busy_timeout` en zonder read-only open-modus. Elke `getDb()` en elke `ensure*Schema()` voert DDL uit.
- **Ruimte voor een tweede service** (waarschijnlijk niet):
  - Een Railway-volume hangt aan één service, dus een tweede service kan dit SQLite-bestand niet delen.
  - Zelfs op hetzelfde volume zou die service bij het openen migraties draaien en schrijven, zonder busy-timeout, naast 22 schrijvende lussen.
  - De bewezen integratiepatronen zijn HTTP:
    - de Engine via `/api/tienda-lees` met een eigen secret;
    - `/api/tracking` en `/api/voorraadprijzen` als proxies;
    - het gedeelde `SESSION_SECRET` voor één login via de Multi-Zone-rewrite `/product-engine/*` in `next.config.mjs`.
  - Een AI-assistent hoort dus een aparte service met een eigen DB te zijn, die Master via read-only HTTP-endpoints bevraagt.
- **Classificatie:** DB delen **NIET HERGEBRUIKEN**; het Multi-Zone- en proxy-patroon **BESTAAT — DIRECT HERGEBRUIKEN**.

## 18. Klantdata en privacy

- Er is geen tabel met klant-e-mail, naam, adres of telefoon. `verkoop.ts` zegt het expliciet: "Dat zijn geen klantgegevens".
- `bancontact_testers` bewaart geen naam of IBAN (alleen paymentId, bedrag, status en referentie).
- `/api/tracking` toont klantnaam, postcode en stad live uit de tracking-service, maar slaat ze niet op.
- Geheimen in de DB: `winkel2_auth.access_token` (Mechelen-token).
- **Classificatie:** klantdata **ONTBREEKT** (bevestigd). Dat is gunstig voor privacy, maar alles moet uit Shopify zelf komen.

## 19. Tellingen

- **src/lib:** 168 top-level `.ts`-bestanden plus 5 submappen (markt 12, onderzoek 8, prijs 17, voorraad 1, willie 18) = **224 `.ts`**.
- **Tests:** 207 vitest-bestanden (~3143 cases), 20 Playwright-specs.
- **API-routes:** **60** `route.ts`.
- **SQLite-tabellen:** **130 unieke** `CREATE TABLE IF NOT EXISTS` (`price_sync_log` wordt twee keer gedefinieerd):

aandacht, aandacht_voorval, alerts, auto_prijs_pauze, bancontact_testers, brand_rules, bron_kapot_poging, bron_koppeling_log, catalogus_log, comp_price_history, competitor_effective, competitors, concurrent_afwijzing, concurrent_besluit, concurrent_kandidaat, concurrent_keuring, concurrent_versheid_stand, concurrent_zoekpoging, cutover_checkpoint, exact_vers, hardloper_spoor, herbevoorrading_wacht, identiteit_herstel_log, kampenhout_herstel_log, kandidaat_oordeel, keten_hartslag, koppel_log, kost_historiek, kost_observaties, master_uitsluiting, model_kennis, nacontrole, new_arrivals, noodstop, noodstop_log, nulmeting, nulmeting_log, onderzoek_log, pending_changes, price_history, price_proposals, price_sync_log, prijs_actie, prijs_actie_log, prijs_handmatig_log, prijs_parameters, prijs_uitsluiting, product_archief, product_status, products, provider_gebruik, reports, review_reactie, review_voortgang, rollback_log, scan_ritme, schema_stap, shop_herkansing, shop_leesstatus, shop_shipping, shop_uitkomst, shop_verkeer, shops, siemons_nulmeting, siemons_venster, standaardlocatie_log, standaardlocatie_ronde, standaardlocatie_vrijgesteld, stock_canary, stock_check, stock_sync_log, stock_watch_log, suppliers, sync_log, tienda_concurrent_poging, tienda_koppeling_verbod, tienda_prijs_check, tienda_verdwenen_bewijs, variant_ontbreekt_voorstel, variant_scan, vaste_override_log, vaste_vip_override, verhoging_proef, verkoop_dag, verkoop_dagstatus, verkoop_lock, verkoop_sync, verzend_meting, verzendoptie, vip_bevestiging, vip_bevestiging_log, vip_bevestiging_variant, vip_check, vip_correctie, vip_sync_log, vip_wijziging_log, voorraad_abonnement, voorraad_bezorging, voorraad_gebeurtenis, voorraad_handmatig, voorraad_pool, voorraad_sweep, voorraad_uitsluiting, watchdog_log, willie_bewijs, willie_gesprek, willie_instelling, willie_les, willie_policy, willie_regel_voorstel, willie_rem, willie_rem_log, willie_uitvoering, willie_vragen, winkel2_afbeelding_log, winkel2_auth, winkel2_beheer_log, winkel2_eigendom, winkel2_eigendom_spoor, winkel2_koppeling, winkel2_media, winkel2_oauth_state, winkel2_prijsbeheer_spoor, winkel2_product, winkel2_spiegel_log, winkel2_variant, winkel2_variant_koppeling, winkel2_vertaling_log, worker_ronde, zoekbatch.

## 20. Rapporten (`rapporten/*.md`, 14–15-09-2026)

Relevant voor klantvragen:
- **`voorraad-loskoppeling-2026-09-15.md`:** `custom.standaardlocatie` (de levertijdclaim op de website) stuurde vroeger de voorraadmeting en is nu ontkoppeld. Een klant-AI moet de levertijd dus uit dat label halen en de voorraad uit `stock_check`, nooit andersom.
- **`voorraad-xplo-2027-2026-09-15.md`, `voorraad-onderzoek-…`, `voorraad-prioriteit-en-fase1-…`:** concrete gevallen (Nenno Xplo 2027: Spanje stond op 0 terwijl de bron 98 had) waarin Master's opgeslagen titel en voorraad achterliepen. De les voor een assistent: noem de versheid en vertrouw geen verouderde kopie.
- **`vip-correctie-2026-09-14.md` en de andere VIP-rapporten:** VIP-prijzen zijn herhaaldelijk gecorrigeerd (293 van 1544). Een klant die naar "zijn" VIP-prijs vraagt, moet een live lezing krijgen.
- **`vertex-en-fase2-2026-09-15.md`:** spookvarianten of GID's die in Shopify niet meer bestaan. Productidentiteit loopt via het variant-GID.

---

## Wat de AI-assistent uit Master kan halen zonder nieuwe code

Via bestaande functies en routes. Let op: alle routes vereisen een sessie of `SYNC_SECRET`; een publieke klant-API bestaat niet.

| Functie of route | Vraag die het beantwoordt |
|---|---|
| `productZoeken.zoekProducten()` | "Hebben jullie de Nox AT10 18K 2026?" (fuzzy product- en variantzoeken) |
| `willie/gereedschap` `zoekProduct` (intern) | Welke maten of varianten bestaan er van dit artikel (maat_optie, variant-GID) |
| `vipSchrijver.leesVersePrijsEnVip(variantGid)` | Wat kost dit nu, en wat is de VIP-prijs (live uit Shopify) |
| `products.price` / `vip_price` (cache ≤180 min) | Dezelfde vraag zonder Shopify-call |
| `stock_check.beschikbaarheid` + `voorraadWatch.veiligVerkoopbaar()` | "Is maat 43 nu leverbaar?" (fail-closed per variant) |
| `voorraadContext.beschikbaarNu(productId)` | Verkoopbaar aantal over alle maten samen (dropship inbegrepen) |
| `voorraadContext.eigenVoorraad(productId)` | Ligt het fysiek in Kampenhout of bij ShopWeDo (afhalen of snel) |
| `stock_check.standaardlocatie` / `standaardlocatie.bepaalStandaardlocatie()` | Welk levertijdlabel (Spanje, Kampenhout, ShopWeDo…), zonder dagen |
| `tiendaBron.tiendaStandVoorProduct(productId)` | Is het bij de bron (Tienda) beschikbaar, uitverkocht of verdwenen, en hoe oud is dat bewijs |
| `voorraadSignaal.nieuwOpVoorraad(uren)` | Wat is recent terug op voorraad |
| `testracket.isTestracket()` / `waaromTestracket()` | Is dit een testracket (testservice EUR 10) |
| `verkoop.productInzicht()` / `GET /api/verkoop?product=` | (Copilot) verkooptempo, prijsbeweging, markttrend |
| `willie` gereedschap `prijsbeeld` / `concurrenten` / `prijsdossier` | (Copilot) marge, vloer, concurrentie, prijsvoorstel |
| `GET /api/tracking` | (Copilot) aantal zendingen dat handmatig tracking nodig heeft, met klant en stad |
| `racketDiagnose.productTrace(zoek)` | (Copilot) live herkomst van een product: metafields, locaties, Tienda |
| `geschiedenis.geschiedenis()` / `aandacht.aandachtLijst()` | (Copilot) wat is er vandaag veranderd of kapot |

## Wat ONTBREEKT in Master voor klantenservice (per item bevestigd)

- **Orders per klant: ontbreekt.** Er zijn twee order-queries (`verkoop.ts`, `vipOrderDiagnose.ts`) maar zonder customer- of e-mailvelden, en er worden alleen dagtotalen opgeslagen. Geen lookup op ordernummer of e-mail. `read_customers` wordt niet gebruikt. `read_orders`: code en CLAUDE.md spreken elkaar tegen; `read_all_orders` ontbreekt zeker, dus maximaal 60 dagen.
- **Fulfilments en verzendstatus per order: ontbreekt.** Er is geen `fulfillments`- of `fulfillmentOrders`-query. Die zit alleen in de aparte `padelmq-tracking`-service, die bovendien in dry-run staat.
- **Trackingnummer per order: ontbreekt** in Master. Alleen de geaggregeerde statusproxy `/api/tracking`.
- **Refunds en retouren per klant: ontbreekt.** Refunds worden alleen verrekend in de verkoopaantallen.
- **Retour-, garantie- en herroepingsbeleid: ontbreekt.** Het leeft in Shopify-pagina's en productbeschrijvingen; Master herkent alleen het blok via regex (`mechelenBestelblok.ts`).
- **Levertijd in dagen of datum: ontbreekt.** Er is alleen het label `custom.standaardlocatie`; de dagenbelofte staat in het thema. `shipping.ts` gaat over concurrenten.
- **Verzendkosten voor de klant (PadeLMQ-tarieven, gratis-drempel): ontbreekt.** `verzendoptie` bevat interne kost, geen klanttarief.
- **E-mailinbox (lezen, threads, antwoorden): ontbreekt.** Er is alleen SMTP-verzenden naar `REPORT_EMAIL`.
- **Klantgespreksgeschiedenis en tickets: ontbreekt.** `willie_gesprek` is intern en per pricing-vraag.
- **Klantidentiteit, VIP-lidmaatschap, klantdata: ontbreekt.** Er is geen klanttabel; VIP-prijs per variant bestaat wel, VIP-status per klant niet.
- **Racketspecificaties en productadvies (gewicht, balans, vorm, kern, EVA): ontbreekt** in Master. Ze staan in Shopify-metafields (`custom.*`, `padelmq_engine.spec_*`) en de AI Product Engine.
- **Publieke of klant-API met rate-limit en klant-auth: ontbreekt.** Er is één admin-login plus machine-secrets.
- **AI-audit, kostentracking en evaluatieset: ontbreekt.** Er is geen log van prompts, tokens of kosten en geen golden set; alleen tests met een gestubde denker.
- **Generieke goedkeuringsmodule (`goedkeuring.ts`): ontbreekt.** Nooit gecommit, bevestigd met git. Het werkende GO-patroon is Willie's `regelBevestiging` + `uitvoeren`.
- **Meertaligheid voor klanten: ontbreekt** in Master. Alleen de Willie-stem NL/EN en de Mechelen-vertaalspiegel.

## Discrepanties tussen docs en code

- `ACTIVATIEPLAN_READ_ORDERS.md` bestaat niet.
- `read_orders` heet in CLAUDE.md "niet verleend", maar de code zegt "bewezen" (`vipOrderDiagnose.ts:26`).
- `workerGates.ts` en `WORKERS_FAIL_CLOSED` bestaan niet.
- `npm run keuring` staat niet in package.json.
- CLAUDE.md zegt dat alleen login en logout geen guard hebben. Ook `bancontact/*`, `tienda-lees` en `winkel2/oauth/callback` hebben geen sessie-guard; zij gebruiken een eigen secret of HMAC.
- De README noemt `gpt-4o-mini` en een statisch `SHOPIFY_ADMIN_TOKEN`; productie draait op client-credentials.
