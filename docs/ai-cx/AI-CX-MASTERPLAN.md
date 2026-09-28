# PADELMQ AI CUSTOMER EXPERIENCE · MASTERPLAN

**Fase 0 · onderzoek, brainstorm en masterplan · 28 september 2026**
**Status: werkdocument voor beslissing. Er is geen productiecode geschreven en niets live gezet.**

Bijlagen bij dit plan:
- `mockups.html` – conceptschetsen desktop en mobiel (vier richtingen, servicebalie, Copilot, vergelijkingsmatrix). Ook gepubliceerd als artifact.
- `research/A1-inventaris-master-padelmq-pro.md` – volledige inventarisatie van Master (224 bestanden, 130 tabellen, 60 routes).
- `research/A2-inventaris-satellietrepos.md` – Product Engine, tracking, dagontvangsten, factuurmotor, stockprice.
- `research/B1-onderzoek-virtual-humans-avatars.md` – digital humans, uncanny valley, AI Act, performance.
- `research/B2-onderzoek-ai-shopping-assistants-en-failures.md` – Rufus, Klarna, Fin, Gorgias, failures, prijzen.
- `research/B3-onderzoek-padel-advies-en-interfaces.md` – racketfinders, attributen, modeljaar-evolutie, fitting-interfaces.

Beperkingen van dit onderzoek, eerlijk vooraf: de onderzoeksomgeving kon externe webpagina's niet volledig openen (alleen zoekexcerpten), padelmq.com zelf was niet bereikbaar, en de Gmail- en Shopify-koppelingen waren in deze sessie niet geautoriseerd. De klantenservicevolumes in dit plan zijn daarom aannames op basis van 3.703 orders in 2026 (stand 28 september), geen metingen. De eerste concrete stap van dit plan is die meting.

---


## Inhoud

1. Executive summary
2. Het probleem
3. De eindvisie
4. Principes
5. Analyse van de oorspronkelijke blueprint
6. Actuele Master-inventarisatie
7. Externe research: wat bewezen is, wat we zien, wat we vermoeden
8. Waarom klassieke chatbots dominant zijn
9. Kansen buiten de chat
10. Het digitale-medewerkerconcept
11. Kritische analyse van het concept
12. Drie fundamenteel verschillende UX-richtingen
13. Twintig-plus aanvullende innovatie-ideeën
14. Desktopervaring
15. Mobiele ervaring
16. Voice
17. Centrale architectuur
18. Fact Brain
19. Advice Brain
20. Silent Customer Intelligence
21. Mathias Copilot
22. Autonomiemodel
23. Klantintenties en matrix
24. Dataflows
25. Escalatiemodel
26. Privacy en security
27. Historische evaluatieset
28. Teststrategie
29. Performance en Core Web Vitals
30. Toegankelijkheid
31. Kostenmodel
32. KPI's
33. Fast Track V1: snel tijd terug, zonder spektakel
34. Verdere fases
35. Technische risico's
36. Commerciële risico's
37. UX-risico's
38. Wat we expliciet NIET bouwen
39. Open beslissingen voor Mathias
40. Concrete volgende stap

---

## 1. Executive summary

**Wat we willen.** PadeLMQ wil twee dingen tegelijk: Mathias drastisch minder klantenservice laten doen, en online padel kopen fundamenteel beter maken dan een traditionele webshop kan. Niet "PadeLMQ heeft ook een chatbot", maar "bij PadeLMQ word ik online écht geholpen, vóór, tijdens en na mijn aankoop".

**Wat het onderzoek zegt.** Vijf conclusies dragen dit plan:

1. **Het brein is het product, niet de avatar.** Elke zichtbare digitale mens die in het Westen als klantenservice is ingezet (ANZ, Air New Zealand, Mercedes, IKEA's Anna, Microsofts Ms. Dewey) is gestopt; de grootste leverancier ging in februari 2026 failliet. Mercedes' eigen onderzoek: "veel meer mensen hebben een hekel aan het menselijke gezicht." De assistenten die wél schalen (Rufus, Zalando, Erica) zijn tekst met een merkteken en zeer goede antwoorden.
2. **De failures hebben één mechanisme.** Air Canada, Cursor, NYC MyCity, Chevrolet: een taalmodel dat beleid of toezeggingen zelf verzint in plaats van ophaalt. Geen enkele was "het model is te dom". Allemaal architectuur en proces. Het antwoord is: elk feit uit één bron, beleid letterlijk citeren, geen bevoegdheid om iets te beloven, en "onbekend" als geldig antwoord.
3. **Master is een sterk intern brein zonder klantkant.** Master (padelmq-pro) kent productzoeken, live prijs en VIP-prijs, verkoopbaarheid per maat (fail-closed), Tienda-brontoestand, en heeft in Willie al het volledige copilot-patroon (tool-loop, rem, bevestiging in twee beurten, lessen, stem). Wat volledig ontbreekt: orders per klant, fulfilments en tracking per order, levertijd in dagen, retour- en garantiebeleid, e-mailinbox, gespreksgeschiedenis, en gestructureerde racketspecs voor de bestaande catalogus.
4. **Het onderscheid zit in relatief advies.** Geen enkele racketfinder ter wereld gebruikt "mijn huidige racket" als anker en legt uit wat er verandert. Reviewers doen dat wél, altijd met hetzelfde skelet. Dat skelet, plus per-stuk-gewicht van eigen voorraad en een modeljaar-tijdlijn, is een dataset die niemand anders heeft.
5. **De kosten zitten niet in het model.** Een supportgesprek kost aan modelkosten ongeveer één cent. Per-resolutie-SaaS (Fin, Gorgias, Zendesk) rekent 50 tot 500 keer meer en is gebouwd voor teams, niet voor één operator met naar schatting 125 tot 185 vragen per maand.

**Wat we aanbevelen.**

- **Bouw één centraal brein als aparte service naast Master**, met eigen database, dat Master, Shopify, de tracking-service en de Product Engine via read-only endpoints bevraagt. Deel nooit de SQLite van Master.
- **Fact Brain en Advice Brain strikt apart**: feiten met bron per veld (het herkomstmodel van de Product Engine bestaat al), interpretaties als gelabelde adviesregels met versie.
- **Drie autonomieniveaus per intentie** (Autonomous, Assisted, Human required), afgedwongen in code, met Willie's bevestigingspatroon als blauwdruk. Een correcte escalatie is een succes.
- **Fast Track V1 (6 tot 8 weken) is de Mathias Copilot plus contextuele antwoorden op de site**: draft-and-approve voor elke inkomende vraag, met een dossier per order; op de site levertijd, voorraad, verzendinfo, orderstatus, eenvoudige vergelijkingen. Dit levert vanaf week één tijd op en bouwt tegelijk de evaluatieset.
- **V2 is de zichtbare medewerker**: een gestileerd, duidelijk niet-fotorealistisch PadeLMQ-karakter met AI ASSISTENT-shirt, klein en op verzoek, met de virtuele werkbank en "vergelijk met mijn huidige racket" als kern. **Niet** de immersieve winkelvloer als hoofdinterface.
- **V3 en V4**: servicebalie met ordertijdlijn en retourwizard, per-stuk-weegbank, testservice-boeking, WhatsApp en e-mail als kanalen, push-to-talk als optie. Realtime voice en in-chat checkout bewust niet.

**Wat het oplevert (doelen, geen beloftes).** Binnen zes maanden: 50 tot 60 % van de inkomende vragen autonoom of met één klik goedgekeurd, first response onder 15 minuten op kantooruren, foutpercentage op feiten onder 1 %, en een meetbare stijging van conversie op adviessessies tegen een holdout. Modelkosten onder 50 euro per maand.

**De eerste stap** is geen code: vier weken het echte klantenservicevolume meten en 200 historische gesprekken labelen als evaluatieset, en drie beslissingen van Mathias (sectie 39).

## 2. Het probleem

Mathias behandelt vandaag zelf elke klantvraag, over vier kanalen (Tidio-chat, e-mail, WhatsApp, telefoon) en in drie talen. De vragen vallen uiteen in drie groepen:

| Groep | Voorbeelden | Wat het vandaag kost |
|---|---|---|
| **Eenvoudig, feitelijk** | levertijd, verzendkosten, voorraad, "waar is mijn pakket", factuur, afhalen, openingsuren Pachanga | Kort per vraag, maar hoog in aantal en versnipperd over de dag. Elke vraag is een contextwissel. |
| **Systemen combineren** | split order (ballen uit België, racket uit Spanje), "geleverd maar niets ontvangen", retour van een deel van een order, factuur achteraf met btw-nummer, gewicht 367–369 g | Shopify, tracking-tool, ICP-mails, onFact, Tienda openen, interpreteren, persoonlijk antwoorden. 5 tot 20 minuten per dossier. |
| **Advies** | welk racket, verschil 12K/18K, upgrade van Vertex 04 naar 05, elleboog, tennis-overstapper, kinderracket, schoenmaat | Het meest waardevolle werk en het meest tijdrovende. Lange mails die telkens opnieuw geschreven worden. |

Wat het structureel moeilijk maakt:
- **De waarheid staat op zeven plaatsen.** Prijs en voorraad in Shopify en Master; specs in vrije-tekst-metafields; beleid in Shopify-pagina's en onderaan productbeschrijvingen; tracking in een JSON-bestand van een Railway-tool in dry-run; facturen in onFact; testers in Bancontact; klanthistoriek in Tidio en Gmail.
- **Er is geen klantkant.** Master is één admin-login. Geen enkele repo heeft een leesendpoint per order of een klant-facing flow.
- **Dropship maakt elke belofte onzeker.** 2.971 van 3.000 varianten zijn dropship uit Spanje. Levertijd, split shipments en "staat geleverd" hangen af van een keten (Tienda → ICP → carrier) waarvan alleen de mails zichtbaar zijn.
- **Advies is niet vastgelegd.** De adviesmethode van Mathias zit in zijn hoofd en in duizenden verzonden mails, niet in een model dat een systeem kan toepassen.
- **Volume groeit sneller dan de tijd.** 3.703 orders in 2026 tegenover 579.030 euro omzet over heel 2025; de omzet is dit jaar al hoger dan vorig jaar. Klantenservice schaalt lineair mee, Mathias niet.

## 3. De eindvisie

> "PadeLMQ heeft een digitale padelmedewerker die je vóór, tijdens én na je aankoop werkelijk kan helpen."

Concreet, per fase van de klantreis:

**Vóór de aankoop: ontdekken → vergelijken → adviseren → kiezen.** De klant noemt waarmee hij speelt. Vanaf dan is alles relatief daaraan. De medewerker legt twee of drie rackets op de werkbank, toont alleen de verschillen die voor deze klant tellen, en durft er één af te raden. Bij twijfel: "wil je deze twee vijf dagen proberen?" en de testset wordt geboekt.

**Tijdens de aankoop: beschikbaarheid → maat/gewicht → levering → twijfel wegnemen.** Per maat en per locatie een eerlijke belofte: "morgen in huis", "uit Spanje, donderdag of vrijdag", "afhalen in Mechelen vanaf morgenmiddag". Gewichtsvoorkeur wordt een klik, geen mail. Gripadvies erbij zonder pushen.

**Na de aankoop: order → tracking → split shipment → retour → probleem → oplossing.** De klant ziet zijn order als tijdlijn per regel. Een split order is geen tekstantwoord maar een plaatje. Een retour vraagt alleen wat ontbreekt. Een probleem wordt een dossier dat bij Mathias al gevuld aankomt.

**Achter de schermen: leren → evalueren → escaleren → Mathias ontlasten → PadeLMQ beter maken.** Dezelfde intelligentie werkt intern als Mathias Copilot: één ordernummer geeft het hele dossier en een antwoord om goed te keuren. Elke EDIT is een les. Elke onbeantwoordbare vraag is een gat in de website. Elke week een lijst van wat ontbreekt.

**En altijd eerlijk.** De klant weet dat hij met AI praat. Het heet PadeLMQ AI Adviseur, ontwikkeld volgens de adviesmethode van PadeLMQ. Het doet zich nooit voor als Mathias. Het zegt "onbekend" in plaats van te gokken. Het escaleert graag.

## 4. Principes

Tien principes die elke ontwerp- en bouwbeslissing in dit project toetsen. Ze zijn geformuleerd zodat een test ze kan afdwingen, in de traditie van `tests/veiligheid.test.ts` in Master.

1. **Eén feit, één bron.** Elk feit heeft één gezaghebbende bron en de assistent rekent of verzint nooit zelf. Prijs → Shopify (via Master's verse lezing). Voorraad → `stock_check` + `veiligVerkoopbaar()`. Order en fulfilment → Shopify. Tracking → tracking-service/Shopify-fulfilment. Specs → Fact Brain. Advies → Advice Brain. Beleid → centrale policy-store, letterlijk. Levertijd → centrale levertijdregel.
2. **Onbekend is een antwoord.** Ontbreekt betrouwbare informatie, dan zegt de assistent dat, en escaleert indien nodig. Nooit een plausibel getal. (Willie's contract: "GETALLEN: REKEN NIET ZELF.")
3. **Feit en interpretatie lopen nooit stilletjes door elkaar.** Elk antwoordobject draagt een label: feit (met bron en versheid), advies (PadeLMQ-methode, versie), beleid (paragraaf).
4. **Intelligentie en betrouwbaarheid vóór spektakel.** Een visuele keuze is pas toegestaan als het antwoord er beter van wordt. Anders is het decor.
5. **Vraag alleen wat de onzekerheid materieel vermindert.** Geen verplichte vragenlijst. Het huidige racket, de order, de pagina en de historiek beantwoorden de meeste vragen al.
6. **Autonomie in uitvoering, nooit in beleid.** Elke intentie heeft een niveau (Autonomous, Assisted, Human required) dat in code staat. De assistent kan geen beleid, prijs, korting, garantie of levertijd beloven buiten wat de bron zegt. Een correcte escalatie is een succes; het escalatiepercentage is geen KPI om te minimaliseren.
7. **Eerlijk over AI, warm in toon.** Zichtbaar AI-label bij eerste contact en in elk paneel (EU AI Act art. 50, sinds 2 augustus 2026). Nooit "Mathias" als afzender van een AI-tekst. "Ik wil Mathias spreken" is altijd één tik weg met een eerlijke verwachting.
8. **Afraden is een dienst.** De assistent mag en moet een duurdere of ongeschikte optie afraden. Commerciële KPI's mogen hem nooit richting pushen of bluffen sturen.
9. **Context maakt slimmer, nooit enger.** Stille intelligentie (bekeken producten, eerdere aankopen, winkelmand) wordt gebruikt om minder te vragen, nooit benoemd met tijdstippen of frequenties, en alleen binnen toestemming.
10. **Bouw geen tweede systeem.** Als Master, de Product Engine, de tracking-service of Shopify het al oplost, wordt het hergebruikt via een read-only endpoint. De assistent is een aparte service met eigen database; hij deelt nooit Masters SQLite en voegt nooit een lus toe aan Masters proces.

## 5. Analyse van de oorspronkelijke blueprint

De eerdere blueprint (één PadeLMQ Brain, één feit = één bron, Fact Brain, Advice Brain, AI Adviseur, Mathias Copilot, Silent Customer Intelligence, progressieve autonomie, historische evaluatieset, centrale audit, escalatie, meerdere kanalen, meertaligheid, WhatsApp/e-mail later, leren uit gesprekken), getoetst aan de huidige stand van Master en de satellieten.

| Onderdeel blueprint | Klopt nog? | Al gebouwd? | Achterhaald of beter te ontwerpen |
|---|---|---|---|
| Eén centraal PadeLMQ Brain | Ja, als **orkestratielaag**, niet als één database | Nee. Wel: Master is de facto het brein voor prijs/voorraad/VIP; Product Engine voor nieuwe productfeiten | Het brein moet een aparte service zijn die bestaande breinen bevraagt. "Eén brein" betekende impliciet "één DB"; dat is met Masters 130 tabellen en 22 schrijvende lussen niet haalbaar of wenselijk. |
| Eén feit = één bron | Ja, en Master dwingt het al af voor prijs, kost, voorraad | Ja, voor het interne domein (`kostContext`, `voorraadContext`, `prijsWaarheid`) | Uitbreiden naar klantdomein: beleid, levertijd, tracking, specs. Daar bestaat vandaag géén bron. |
| Fact Brain | Ja | **Deels**: de Product Engine heeft het exacte herkomstmodel (feit → bron → tier → confidence → conflict → override), maar alleen voor nieuwe producten. Bestaande catalogus: vrije tekst in `custom.*` zonder bron | Fact Brain = Product Engine-model + een backfill voor de bestaande catalogus + read-endpoint per Shopify-GID. Niet opnieuw ontwerpen. |
| Advice Brain | Ja | **Deels**: Racket DNA (dna-v5, zes dimensies, absolute schaal) is een adviesmodel; de twaalf `review_*_feel`-velden en `manufacturer_positioning` ook. Maar: geen modeljaar-evolutie, geen "relatief aan anker", geen elleboog-/overstapper-regels, geen versiebeheer van adviesregels | Advice Brain als aparte, geversioneerde regelset + DNA. Opbouwen uit Mathias' historische mails. |
| PadeLMQ AI Adviseur (klant) | Ja | Nee. Niets klant-facing in enige repo | Zoals dit plan: contextueel (B) als V1, ambient medewerker (A) als V2. |
| Mathias Copilot | Ja, en **belangrijker dan gedacht** | **Grotendeels als patroon**: Willie heeft tool-loop, rem, bevestiging in twee beurten, lessen, stem, vragenwachtrij. Maar volledig op pricing gericht | Copilot = Willie-patroon toegepast op klantendossiers. Willie zelf niet ombouwen; hij blijft de pricing-collega. |
| Silent Customer Intelligence | Ja, met strengere grenzen | Nee. Master kent geen klantdata (bewust) | Alleen sessiecontext, ingelogde klantcontext met toestemming, en orderhistoriek via Shopify. Nooit opslag van gedragslogs buiten de sessie zonder toestemming. |
| Progressieve autonomie | Ja | **Ja, als patroon**: `PRICE_SYNC_WRITE`, dubbele gates, canaries, `rem.ts`, `regelBevestiging` | Overnemen als drie niveaus per intentie, met dezelfde fail-closed defaults. |
| Historische evaluatieset | Ja, cruciaal | Nee. Geen golden set voor Willie-antwoorden; `acceptatieWillie.ts` is geen LLM-eval | Ontwerpen vanaf dag één (sectie 27). Zonder evaluatieset is elke modelwissel een gok. |
| Centrale audit | Ja | Deels: veel logtabellen, `geschiedenis.ts`, `aandacht.ts`, maar **geen AI-audit** (geen prompts, tokens, kosten) | Elk AI-antwoord gelogd met bronnen, model, tokens, kosten, autonomieniveau, uitkomst. |
| Escalatie | Ja | Willie: `mens_vereist`, vragenwachtrij | Escalatie als eersteklas object met dossier, niet als "chat overdragen". |
| Meerdere kanalen | Ja | Nee (Telegram-kolommen in Willie zonder bot) | Site en Copilot eerst; e-mail via Gmail-API; WhatsApp via Business API later. Tidio vervangen of als kanaal koppelen: beslissing (sectie 39). |
| Meertaligheid | Ja | Nee voor klanten (wel nl/fr/en productteksten in Mechelen-spiegel) | Taal per gesprek uit de klant; beleidsteksten in drie talen in de policy-store; Shopify Magic is Engels-only, dus geen optie. |
| Leren uit gesprekken | Ja | Willie's `les.ts` (observatie → kandidaatregel → bevestigde regel, drempel 0,65) | Zelfde patroon voor adviesregels en antwoordstijl. Nooit automatisch feiten leren; alleen interpretaties, met bevestiging. |

Conclusie: de blueprint is in zijn principes intact en in zijn architectuur te abstract. De grootste verschuiving sinds toen: Master en de Product Engine hebben het interne fundament (bron-per-feit, gates, audit, copilot-patroon) al gelegd, maar niets daarvan is klant-facing, en de klantdomeindata (orders, tracking, beleid, levertijd) heeft nog helemaal geen bron.
## 6. Actuele Master-inventarisatie

Volledig rapport in `research/A1` (Master) en `research/A2` (satellieten). Hier de classificatie per onderdeel, met de code waar het staat.

### 6.1 Wat er is: zes repo's, één operator

| Repo | Wat | Stack / hosting | Rol voor AI CX |
|---|---|---|---|
| `padelmq-pro` (Master) | Prijs-, voorraad-, VIP-engine; Willie; Mechelen-spiegel | Next.js 14, SQLite (130 tabellen), Railway, 22 achtergrondlussen | Bron voor prijs, VIP, verkoopbaarheid per maat, productzoeken, Tienda-stand; copilot-patroon |
| `padelmq-ai-product-engine` | Onderzoek nieuwe producten: feiten met bron, conflicten, Racket DNA, publicatie | Next.js 14, SQLite, Railway, Claude (extractie) + OpenAI (content), SSO met Master | Het Fact Brain-model; DNA als Advice-input |
| `padelmq-tracking` | Tienda-dropship tracking → Shopify-fulfilment | Python/Flask, Playwright, IMAP, Railway, **dry-run** | Enige bron voor Tienda-ref ↔ ORD, carrierstatus, ETA |
| `dagontvangsten-robot` | Dagontvangsten Shopify → Scrada; Bancontact-testerdekking | Python, GitHub Actions + Railway-app | Facturen-index (Lucy/onFact), orderreader met refunds, Bancontact-testers |
| `padelmq-factuurmotor` | B2B-facturen met VIES-validatie via onFact/Peppol | Python worker, Railway | Factuurstatus per order, VIES, "ik wil een factuur"-intake |
| `padelmq-stockprice` | Ballendozen-prijzen per locatie; express-regel | Node, één bestand | Locatieregel BE vs ES als levertijdinput |

### 6.2 Classificatie per onderwerp

**BESTAAT — DIRECT HERGEBRUIKEN** (read-only, via een nieuw dun HTTP-endpoint in Master of de bestaande route)
- Productzoeken: `productZoeken.zoekProducten()` (fuzzy over titel, merk, type, SKU, EAN).
- Live prijs + VIP-prijs per variant: `vipSchrijver.leesVersePrijsEnVip(variantGid)`; cache ≤180 min in `products.price/vip_price`.
- Verkoopbaarheid per maat, fail-closed: `stock_check.beschikbaarheid` + `voorraadWatch.veiligVerkoopbaar()`; product-breed `voorraadContext.beschikbaarNu()`; eigen fysieke voorraad `eigenVoorraad()`.
- Locatielabel per product: `stock_check.standaardlocatie` / `standaardlocatie.bepaalStandaardlocatie()` (Spanje, Kampenhout, ShopWeDo).
- Tienda-brontoestand: `tiendaBron.tiendaStandVoorProduct()` (bevestigd beschikbaar / uitverkocht / verdwenen, met leeftijd van het bewijs).
- Testracket: `testracket.isTestracket()`, `custom.testracket`; Bancontact-testers (`bancontact_testers`, €10-betalingen, geen naam/IBAN).
- Shopify read-client: `shopifyOrgAuth.adminGraphql()` (client credentials, tokencache, throttle-retry). Nieuwe reads horen hier.
- Facturen-index: dagontvangsten `invoices.InvoiceIndex.is_invoiced()`, `onfact.OnFactClient.check()`; factuurmotor `db.bestaand_document_voor_order()`.
- Verkoopinzicht (Copilot): `verkoop.productInzicht()`, `GET /api/verkoop`.
- Multi-zone/proxy-integratiepatroon: `PRODUCT_ENGINE_URL`-rewrite, `/api/tracking`, `/api/voorraadprijzen`, gedeeld `SESSION_SECRET`.

**BESTAAT — AANPASSEN**
- **Willie** (`src/lib/willie/*`, 18 bestanden, 10 testbestanden): tool-loop met 21 gereedschappen, `let_op`/ONBEKEND-contract, rem (vrij/pauze/stop, fail-closed naar STOP), bevestiging in twee beurten (60 min, eenmalig), uitvoering via gegate schrijvers met CAS en na-verificatie, lessen (observatie → kandidaat → bevestigd, drempel 0,65), betwist bewijs, spraak (browser-STT nl-BE, OpenAI TTS `gpt-4o-mini-tts`), `veiligeSpreektekst`, `klinktAlsAfsluiting`. → Blauwdruk voor de Copilot. Willie zelf blijft pricing.
- **Fact Brain-model** in de Product Engine: `facts` (veld, waarde, bron NOT NULL, tier, confidence, criticality, status verified/inferred), `conflicts`, `manual_overrides`, `source_tier_config`, `RACKET_VELDEN` (vorm, gewicht, gewichtsbereik, balans, dikte, kern, kernhardheid, bladmateriaal, frame, oppervlak, niveau, speelstijl, sweet spot, touch, technologieën, twaalf review-feel-velden). Dekt alleen Engine-kandidaten (tot ±46). → Backfill bestaande catalogus + read-endpoint per Shopify-GID.
- **Racket DNA** (dna-v5): zes dimensies (power, control, sweet_spot, maneuverability, comfort, spin), absolute schaal, geen totaalscore, publiek 70–100 %. → Advice-input; per-dimensie bron labelen.
- **Tracking-service**: `mapping.json` per Tienda-ref (shopify_order, carrier, tracking, ups_status, ups_est, delivered, products), `GET /api/status` (alleen aggregaat). → Read-endpoint per ORD; live-overgang afronden. Split shipments: deelpakketten worden samengevoegd op één fulfilment, tracking per orderregel bestaat niet.
- **Factuurmotor**: `vies.controleer()`, `gegevens.ontleed()`, `motor.beoordeel()`, `Shopify.order()` met `displayFulfillmentStatus` en `fulfillments{trackingInfo}` (de rijkste order-reader van alle repo's). Geen HTTP-API; templates ontbreken in repo. → Leesdienst + intake.
- **Orderreader** dagontvangsten (`src/shopify.py`, refunds, land, fulfillmentOrders): financieel rijk, geen tracking. → Combineren met factuurmotor-query tot één orderdossier-query.
- **OpenAI-client** Master (`openai.ts`, `gesprek.ts`): dun, zonder audit/kosten. → Centrale AI-wrapper met log.
- **E-mail**: alleen SMTP-verzenden (`email.ts`). → Gmail-API lezen/threads voor Copilot.
- **Stockprice-locatieregel** (`availableAt`, `decideState`: stock-be / stock-es / leeg). → Onderdeel van de levertijdregel.
- **Testharnas**: 207 vitest-bestanden, Playwright desktop/mobiel/storefront, structurele broncodetests (`veiligheid.test.ts`). → Zelfde patroon voor de assistent; evaluatieset toevoegen.

**ONTBREEKT** (per item bevestigd in code)
- Orders per klant, lookup op ordernummer of e-mail; `read_customers` en `read_fulfillments` nergens gebruikt; `read_all_orders` ontbreekt (max 60 dagen).
- Fulfilments, trackingnummer en verzendstatus per order in Master.
- Levertijd in dagen of datum, klanttarieven en gratis-drempel (`verzendoptie` is interne kost; het thema toont de dagenbelofte uit `custom.standaardlocatie`).
- Retour-, garantie- en herroepingsbeleid als machineleesbare bron (leeft in Shopify-pagina's en het "🛒"-blok onderaan beschrijvingen).
- Racketspecs met bron voor de bestaande catalogus (`custom.vorm/gewicht/balans/kern/racket_oppervlakte` zijn vrije tekst zonder bron; `custom.kracht/controle/comfort` zijn handmatige "10/10" of emoji, geen DNA).
- E-mailinbox, klantgespreksgeschiedenis, tickets, klantidentiteit, VIP-status per klant.
- Publieke of klant-API met rate-limit en klant-auth.
- AI-audit (prompts, tokens, kosten), evaluatieset, generieke goedkeuringsmodule (`goedkeuring.ts` is nooit gecommit).
- Klant-facing flow voor "ik wil een factuur"; retour/RMA-logica.
- Meertaligheid voor klanten.

**NIET HERGEBRUIKEN**
- Masters SQLite delen met een tweede service (één Railway-volume per service; geen busy_timeout; elke `getDb()` migreert; 22 schrijvende lussen).
- Een lus toevoegen aan `instrumentation.ts`.
- Willie als persona voor klanten (tools geven kostprijs, marge, concurrentie terug).
- `/api/tienda-lees` voor klantverkeer (rate-limit 1200 ms, B2B-sessie); Tienda live scrapen per klantvraag.
- Masters admin-auth (één gedeelde login) voor klanten.
- Elke writer: prijs, voorraad, VIP, fulfilment (`/sync`, `/koppel`, `/afvink`), onFact, Scrada, stockprice, Engine-publicatie.
- Stockprice-dashboard (toont inkoopprijs, zwakke auth).

### 6.3 Discrepanties die het plan raken
- CLAUDE.md zegt `read_orders` niet verleend; de code (`vipOrderDiagnose.ts`) zegt bewezen. Te verifiëren via `currentAppInstallation.accessScopes` vóór V1.
- `ACTIVATIEPLAN_READ_ORDERS.md`, `workerGates.ts`, `npm run keuring` bestaan niet.
- De Product Engine heeft wél een Shopify-transport (create-only), anders dan zijn CLAUDE.md zegt.
- Master kent sinds 25-09 één rij per variant in `products` (de "2.223 van 5.876"-blocker uit BEVINDINGEN.md lijkt aangepakt; verifiëren).
- Tracking-repo's `README` zegt "byte-voor-byte kopie"; de live versie is nog de Windows-tool. Zolang dat zo is, is Shopify-fulfilment de enige betrouwbare trackingbron voor de assistent.

## 7. Externe research: wat bewezen is, wat we zien, wat we vermoeden

Het volledige onderzoek staat in drie bijlagen (`research/B1`, `B2`, `B3`). Hier de conclusies, strikt gescheiden naar bewijskracht. Belangrijke beperking: de onderzoeksomgeving kon de meeste webpagina's niet volledig openen (egress-proxy), dus de feiten komen uit zoekmachine-excerpten van de geciteerde pagina's. Vóór je een cijfer extern citeert, open je de bron.

### 7.1 Bewezen feiten (met bron in de bijlagen)

**Zichtbare digitale mensen als klantenservice zijn in het Westen vrijwel allemaal gestopt.**
- Soul Machines, de grootste "digital human"-leverancier (ANZ Jamie, Air NZ Sophie, Mercedes, Nestlé Ruth), ging op 5 februari 2026 in receivership na meer dan 135 miljoen dollar financiering.
- ANZ stopte Jamie voor klanten begin 2022. Air New Zealand zette Sophie nooit permanent in en koos een simpele tekstbot. Mercedes dumpte de technologie in 2024.
- Mercedes' CTO over hun eigen onderzoek voor de MBUX-assistent (CES 2024): "We dachten een gezicht te tonen. Na interne studies besloten we het niet te doen. Sommigen vinden het leuk, veel meer mensen hebben een hekel aan het menselijke gezicht." Ze kozen een abstracte "levende ster".
- UneeQ, de andere grote leverancier, positioneert zijn digitale mensen sinds november 2025 als trainingsplatform voor medewerkers, niet als klantenservice.
- IKEA's Anna (2D-avatar, 2005–2015) werd gepensioneerd omdat ze "geen directe vragen kon beantwoorden; door te focussen op menselijk klinken vergat ze haar doel: commercie." Microsoft Ms. Dewey (video-avatar, 2006–2009): afleidend en traag. Clippy: "betuttelend en irritant" in focusgroepen.

**Waar een gezicht wél overleeft, is het opt-in, in een app, bovenop een al goede tekstbot, of niet-menselijk.** Vodafone Duitsland gaf TOBi in december 2023 een avatar met de stem van een echte medewerker, ín de app, nadat de tekstversie al 65 % first-contact-resolutie haalde. Japan gebruikt 2D-anime-avatars in stations. China's AI-livestreamers zijn commercieel succesvol, maar dat is een broadcastformaat, hybride met mensen.

**De meest gebruikte assistenten ter wereld zijn tekst met een merkteken.** Bank of America Erica: 700 miljoen interacties in 2025, bewust zonder generatief model. Klarna: twee derde van de chats in maand één (2024), maar de CEO gaf in mei 2025 toe "te diep gesneden" te hebben en nam weer mensen aan voor complexe gevallen. Zalando Assistant: tekst, 25 markten.

**Academisch bewijs wijst dezelfde kant op.**
- Luo et al. (Marketing Science, 2019, >6.200 klanten): een onthulde chatbot verkocht bijna 80 % minder dan een niet-onthulde, omdat klanten hem als minder deskundig en minder empathisch zagen. Het effect verzwakte bij late onthulling en bij klanten met AI-ervaring. Late onthulling is precies wat de EU AI Act vanaf 2 augustus 2026 verbiedt.
- Song & Shin (2022/2024, e-commerce experiment): meer menselijkheid verhoogt de "eeriness", die vermindert vertrouwen, en vertrouwen stuurt de aankoop. Bekendheid met de avatar dempt het effect.
- Meta-analyses (Blut et al. 2021; MIP 2023) vinden dat gematigde antropomorfie (naam, toon, gestileerd merkteken) helpt, terwijl vormrealisme (realistische gezichten, animatie) de negatieve effecten versterkt.
- Er bestaat geen gepubliceerde, schone A/B-test "avatar versus dezelfde backend als tekst" in e-commerce. Het beste pro-avatar-cijfer (Deutsche Telekom, 5,8× conversie) is een leveranciersclaim zonder methodologie.

**Juridisch.** Moffatt v. Air Canada (februari 2024): het bedrijf is aansprakelijk voor wat zijn chatbot zegt. EU AI Act artikel 50: vanaf 2 augustus 2026 moet een klant weten dat hij met AI praat, tenzij dat voor een gemiddelde consument evident is. Een winkelassistent met een menselijk gezicht valt niet onder de "evident"-voorbeelden van de Commissie. Belgisch Wetboek Economisch Recht: precontractuele informatieplichten gelden ook als een chatbot ze geeft.

**Performance.** Een gewone chatwidget kost vandaag 100 tot 700 kB en 300 tot 600 ms main-thread-tijd, genoeg om INP van "goed" naar "moet beter" te duwen. Real-time videoavatars (HeyGen, D-ID) kosten circa 0,20 dollar per minuut met 600 tot 900 ms latentie per beurt. Een 2D-karakter in Rive kost circa 200 kB eenmalig en nul per minuut, met states (idle, luisteren, denken, antwoorden).

**Padel-domein.** Geen enkele bestaande racket-finder (PalaMatch, PadelVerdict, PadelZoom, X-Compare, Tennis-Point, HEAD, Wilson, TWU) gebruikt "mijn huidige racket" als anker met uitleg van wat er verandert. Alle twaalf onderzochte tools zijn quiz → lijst, N-up spec-vergelijking, of een "AI-chat"-schil daarop. Gewichtstolerantie is een echt probleem: Babolat en Wilson ±10 g, Kuikma ±5 g, Bullpadel/NOX/Siux geven een bereik van 10 tot 15 g; slechts enkele makers wegen per stuk. Een racket van 365 g weegt speelklaar 372 tot 377 g. PadeLMQ heeft al een testservice (100 euro waarborg, 5 dagen, Pachanga).

### 7.2 Observaties (patronen over bronnen heen)
1. Avatars sneuvelen om drie terugkerende redenen: het gezicht beloofde meer competentie dan de backend leverde; de aanwezigheid leidde af of was traag; de kosten per minuut versus bijna nul voor tekst.
2. Vertrouwen komt uit correcte antwoorden op domeinvragen, niet uit visuele vorm. Deutsche Telekoms uplift, als hij echt is, kwam waarschijnlijk uit guided-selling-logica die ook in tekst werkt.
3. De beste adviesinterfaces in andere sectoren (Tennis Warehouse "Similar Playing Racquets", Bike Insights geometrie-overlay, PING WebFit, Nike Fit, Warby Parker) beginnen bij een anker dat de klant al heeft en tonen deltas, geen absolute scores. Ze eindigen met een menselijke of fysieke stap (fitter, winkel, thuis passen).
4. Reviewers gebruiken voor "moet ik upgraden" altijd hetzelfde skelet: zelfde DNA → wat veranderde (1–3 dingen) → wat je voelt → voor wie wel en niet. Dat skelet is de template voor het antwoord van de adviseur.
5. Gaming-NPC-technologie (Inworld, NVIDIA ACE, Convai) levert infrastructuur (sub-500 ms voice loops, geheugen, guardrails), geen UX die naar retail overdraagt. Ubisofts NEO NPC is in maart 2026 nog niet uitgebracht.

### 7.3 Hypothesen (onze inferenties, te toetsen)
- H1. Een permanente, geanimeerde, mensachtige medewerker verhoogt de verwachting van menselijke expertise; elke fout wordt dan als menselijke fout beoordeeld, met meer vertrouwensschade en aansprakelijkheid.
- H2. Een gestileerd, duidelijk niet-fotorealistisch PadeLMQ-karakter haalt het meeste engagementvoordeel van antropomorfie (naam, warmte, aanwezigheid) zonder de vormrealisme-straf, en maakt "dit is AI" evident genoeg voor artikel 50 met een klein label.
- H3. Het onderscheidende data-asset voor PadeLMQ is per-stuk-data: het echte gewicht van elk racket op de plank, plus het speelklare gewicht na grip en protector. Geen mainstream finder biedt dit.
- H4. Het huidige racket van de klant is een sterkere input dan elke zelfinschatting van niveau of stijl. Quiz-afhaak komt vooral van vragen die het huidige racket al beantwoordt.
- H5. Nieuwigheidseffecten van een zichtbare avatar vervallen binnen weken. Tests moeten minstens 3 weken lopen.

## 8. Waarom klassieke chatbots dominant zijn

De chatballon rechtsonder is niet dominant omdat hij de beste interface is, maar om zes structurele redenen:

1. **Distributie.** Tidio, Gorgias, Intercom en Zendesk verkopen een script-tag. Eén regel in het thema, klaar. Een interface die in de pagina zelf leeft, vraagt themawerk per winkel.
2. **Ticket-metafoor.** De leveranciers komen uit helpdesksoftware. Een chat is een ticket met een ander jasje; hun datamodel, rapportage en prijsmodel (per gesprek, per resolutie) draaien erop.
3. **Veiligheid door vaagheid.** Een tekstantwoord kan hedgen. Een kaart met "morgen in huis" of een schuif met "zachter dan jouw racket" is een harde claim en vraagt betrouwbare data die de meeste shops niet gestructureerd hebben.
4. **Mobiel.** 68 % van het Europese e-commerceverkeer is mobiel. Een full-screen sheet is het enige wat daar generiek werkt; de ballon is de laagste gemene deler.
5. **Meetbaarheid.** "Deflection rate" en "resolved zonder mens" zijn makkelijk te tellen in een chatvenster. Inline antwoorden in de pagina zijn moeilijker te attribueren.
6. **Gebrek aan innovatiebudget bij kleine merchants.** Wie klantenservice als kost ziet, koopt een widget. Wie het als beleving ziet, bouwt.

Voor PadeLMQ is alleen reden 3 een echte drempel, en die valt weg zodra Master en de Product Engine de data structureel leveren. Redenen 1, 2, 4, 5 en 6 zijn géén argument om de ballon te kopiëren.

## 9. Kansen buiten de chat

Wat wordt met moderne AI mogelijk dat zonder AI praktisch onmogelijk was? Niet "sneller antwoorden", maar:

- **Relatief advies.** Alles uitdrukken ten opzichte van wat de klant kent: zijn huidige racket, zijn vorige aankoop, zijn elleboog. Vroeger een gesprek met een goede verkoper; nu berekenbaar uit specs plus een adviesmodel.
- **Antwoorden als objecten.** Een levertijd is een regel onder de prijs. Een vergelijking is een werkbank met drie rackets. Een split order is een tijdlijn per orderregel. Een retour is een checklist die alleen vraagt wat ontbreekt. De AI kiest en vult het object; hij schrijft geen tekst waar een object duidelijker is.
- **Contextuele aanwezigheid.** De vraag die op deze pagina waarschijnlijk is, staat er al, vóór de klant hem typt. Niet "heb je een vraag?" maar "verschil 12K en 18K?" op precies die productpagina.
- **Eén brein, vóór, tijdens en na de aankoop.** Dezelfde intelligentie kent de order van de klant én de specs van het racket dat hij overweegt als vervanger van het racket dat hij vorig jaar kocht.
- **Afraden als dienst.** "Die duurdere versie zou ik in jouw geval niet nemen." Dat is commercieel gezien de sterkste vertrouwensbouwer die een webshop heeft, en een tekstbot doet het nooit.
- **Stille intelligentie.** De assistent weet wat de klant al bekeek en vergeleek, en gebruikt dat om minder te vragen, zonder het ooit te benoemen.
- **Leren uit elk gesprek.** Elke EDIT van Mathias is een gelabeld voorbeeld. Elke terugkerende vraag is een gat in de website. De assistent maakt PadeLMQ beter, niet alleen sneller.

## 10. Het digitale-medewerkerconcept

Het concept dat Mathias voorstelt, uitgeschreven zoals het op zijn best zou werken:

Op desktop ziet de klant een PadeLMQ-medewerker in een padelwinkel of magazijn. Shirt met AI ASSISTENT. De klant begrijpt meteen: dit hoort bij PadeLMQ, dit kan me helpen, dit is AI, ik kan ermee praten. De medewerker haalt rackets uit het rek, legt ze op een werkbank, vergelijkt ze visueel, voegt toe aan een toonbank of raadt af. Na de aankoop blijft dezelfde medewerker relevant: hij toont de order, de tracking, de retour. Het voelt als een winkelmedewerker aanspreken.

De schetsen (`mockups.html`) tonen dit concept in vier gradaties:
- **C · Immersieve winkel**: de volle versie met winkelvloer, rekken, toonbank en een figuur die beweegt.
- **A · Ambient medewerker met werkbank**: een kleine buste met het shirt, in een paneel dat opent op verzoek, met de werkbank als kern.
- **B · Contextueel zonder avatar**: geen medewerker, de AI leeft in de pagina.
- **D · Vergelijk met mijn racket**: geen schil maar een interactie, die in A en B zit.

## 11. Kritische analyse van het concept

Beoordeeld op de redenen die Mathias zelf opsomt. Per reden: is dit werkelijk relevant, en wat zegt het bewijs?

| Reden | Relevant? | Bewijs |
|---|---|---|
| Performance | **Ja, structureel** | Widgets kosten al 100–700 kB; een 3D-scène of videostream voegt MB's en continue bandbreedte toe. CWV-schade op de productpagina raakt SEO en conversie op de héle winkel, niet alleen bij gebruikers van de assistent. |
| Conversie | **Ja, onbewezen richting** | Geen enkele schone A/B in het publieke domein. De enige positieve claim is van een leverancier. Luo et al.: onthulde bots verkopen slechter als ze menselijkheid suggereren. |
| Irritatie | **Ja, bij herhaald bezoek** | Clippy, Ms. Dewey, Anna: aanwezigheid die niet gevraagd wordt, wordt gehaat. Een terugkerende klant wil zijn racket, niet een scène. |
| Uncanny valley | **Ja, bij realisme** | Song & Shin; Mercedes' eigen studies. Verdwijnt grotendeels bij gestileerde, niet-fotorealistische karakters. |
| Afleiding | **Ja** | Alles buiten de werkbank is decor. De koopflow (prijs, maat, knop) verliest aandacht. |
| Toegankelijkheid | **Ja, oplosbaar** | WCAG 2.2.2 (pauzeren van bewegende content), 1.4.2 (geen autoplay-audio), 2.3.3 (reduced motion), 4.1.3 (statusmeldingen aan screenreaders). Een canvas-scène zonder semantiek is per definitie ontoegankelijk. |
| Development cost | **Ja, en terugkerend** | 3D-assets per racket (honderden per seizoen), rigging, animatiestates. Onderhoud stijgt met elk nieuw product. |
| Mobiele schermruimte | **Ja, dodelijk voor C** | 68 % van het verkeer. Een winkelvloer van 390 px breed betekent niets. |
| Latency | **Alleen bij voice/video** | 600–900 ms per beurt bij real-time avatars. Voor tekst en 2D irrelevant. |
| Vertrouwen | **Ja, tweesnijdend** | Een gezicht bouwt vertrouwen zolang het klopt en vernietigt het bij de eerste fout (H1). Tekst met bronvermelding is robuuster. |
| Privacy | **Nee, tenzij camera/mic** | Een avatar op zich raakt privacy niet. Voice wel (audio-opname, opslag). |
| Technische beperkingen | **Deels** | Shopify-thema (Liquid) kan geen WebGL-app hosten zonder app-embed; een aparte pagina kan wel. |
| Gebrek aan innovatie | **Nee** | Er is wél geïnnoveerd (Soul Machines, 135 miljoen dollar). Het is geprobeerd en gestopt. |

Conclusie in twee zinnen. De immersieve winkel (C) is het antwoord op de vraag "hoe maken we indruk", niet op de vraag "hoe helpen we een klant beter dan een gewone webshop". Wat de klant onthoudt, is dat hij écht geholpen werd: het juiste racket, het eerlijke afraden, de order die in één oogopslag klopte.

Maar stop daar niet. Het doel achter het idee (herkenbaar, aanspreekbaar, PadeLMQ-eigen, warm) is juist. De weg ernaartoe is:
- een **gestileerd karakter** (2D, Rive-state-machine, geen lipsync, geen video), klein en op verzoek;
- het **shirt met AI ASSISTENT** als eerlijk merkteken;
- de **werkbank en toonbank** als de eigenlijke innovatie;
- de **scène** hooguit als statische illustratie waarin het karakter zit, nooit als bewegend toneel;
- en waar een echt gezicht loont (uitleg over gripmaat, vormen, testservice): **opgenomen video van Mathias zelf**, die valt niet onder AI-regels en bouwt precies het vertrouwen dat een avatar mist.

Toetsvraag voor elke visuele keuze, ontleend aan Mercedes: "Wordt het antwoord er beter van?" Zo nee, dan is het decor.

## 12. Drie fundamenteel verschillende UX-richtingen

Alle drie staan getekend in `mockups.html`, desktop én mobiel.

### Richting A: Ambient medewerker met virtuele werkbank
Een kleine buste met het AI ASSISTENT-shirt als vast herkenningspunt (desktop: rechtsonder, of in de productpagina naast de koopknop; mobiel: chip naast de koopbalk). Op verzoek opent een zijpaneel (desktop, ±40 % breedte, overlay onder 1280 px) of een bottom sheet (mobiel). Het paneel is geen chat maar een werkbank: gesprek bovenaan, de betrokken producten eronder, vergelijkingsschuiven alleen voor de dimensies die voor deze klant tellen, en een toonbank waar producten op verschijnen en weer af gaan. Na aankoop wordt de werkbank een servicebalie met ordertijdlijn.

- Klantwaarde: hoog (relatief advies, zichtbaar antwoord, afraden).
- Tijdsbesparing: groot (advies- en vergelijkingsmails, split orders).
- Onderscheid: sterk en PadeLMQ-eigen.
- Risico: vraagt gestructureerde specs voor elk racket; anders lege schuiven. Paneelbreedte op kleine laptops.
- Kosten: midden. Onderhoud: portret en content.

### Richting B: Contextuele AI zonder avatar
Geen medewerker. De AI leeft in de pagina: een leveringsregel onder de prijs, contextchips onder de koopknop ("Verschil 12K en 18K?", "Vergelijk met mijn huidige racket"), antwoorden als inline kaarten met bronlabel. Op collectiepagina's een ankerbalk ("je referentie: Vertex 04 Hybrid") die alle kaarten relatief maakt. Na aankoop: de accountpagina toont de ordertijdlijn en retourflow.

- Klantwaarde: hoog (nul frictie, antwoord op de plek van de twijfel).
- Tijdsbesparing: groot (de meest gestelde vragen worden beantwoord vóór ze een mail worden).
- Onderscheid: alleen via kwaliteit; geen "medewerker"-gevoel.
- Risico: elke inline claim is een belofte; zonder levertijdbron mag het blok niets tonen.
- Kosten: laag. Onderhoud: laag. Performance: bijna nul.

### Richting C: Immersieve winkel
Winkelvloer, rekken, toonbank, een figuur die rackets uit het rek haalt. Aparte pagina (`/adviseur`), desktop-only, WebGL of geanimeerde 2.5D.

- Klantwaarde: hoog bij demo, onzeker in gebruik.
- Onderscheid: zeer sterk, sterk verhaal voor pers en social.
- Risico: performance, uncanny valley zodra er een gezicht animeert, afleiding, mobiel onbruikbaar, 3D-assets per product, en het slokt engineering op die het brein nodig heeft.
- Kosten: hoog. Onderhoud: per nieuw product.

### En een vierde, geen schil maar een interactie: D · Vergelijk met mijn huidige racket
De klant noemt zijn racket; vanaf dan is alles relatief daaraan (harder/zachter, hogere/lagere balans, makkelijker/technischer). Geen niveauvraag. Het anker wordt onthouden met toestemming. Dit zit in A én B en is waarschijnlijk het krachtigste onderdeel van het hele project.

### Wat het onderzoek suggereert als volgorde
Copilot (intern) en B leveren de snelste, veiligste waarde en bouwen precies de databronnen die A nodig heeft. A is waar PadeLMQ zich onderscheidt. C blijft een optionele "winkelmodus" voor later, als er ooit budget en bewijs voor is. Geen ranking om de ranking; de volgorde volgt uit afhankelijkheden.

## 13. Twintig-plus aanvullende innovatie-ideeën

Elk idee beoordeeld op de twee vragen: (1) welke taak neemt dit van Mathias over, (2) welke betere beleving ontstaat die een gewone webshop niet biedt. Plus de belangrijkste kanttekening. Ideeën die op beide vragen "geen" scoren, staan er niet in.

| # | Idee | Bron van inspiratie | (1) Taak van Mathias | (2) Betere beleving | Kanttekening |
|---|---|---|---|---|---|
| 1 | **Weegbank per stuk**: het echte gewicht van elk racket op de plank, plus het speelklare gewicht na gekozen grip/overgrip/protector. "Reserveer het exemplaar van 366 g." | Cork Padel, Royal Padel; Nike By You | De vraag "kunnen jullie 367–369 g leveren" (komt wekelijks) | Niemand anders biedt dit; verandert een mail in een klik | Vraagt wegen bij ontvangst + metafield per eenheid. Alleen voor eigen voorraad (Kampenhout), niet voor dropship. |
| 2 | **Modeljaar-tijdlijn**: Vertex 03 → 04 → 05 met per stap de 1–3 genoemde veranderingen en het review-consensusoordeel. | Reviewers' upgrade-skelet | "Is de 05 het waard?"-mails | Direct antwoord op de meest gestelde upgrade-vraag | Kleine gecureerde dataset (60–100 rijen, 7 merken × 2 seizoenen). Advice Brain, gelabeld als interpretatie. |
| 3 | **Delta-kaarten in plaats van radars**: zelfde zes rijen (vorm, gewicht, balans, kern, blad, oppervlak), waarde kandidaat vs waarde anker, een delta-chip ("+5 g", "zachter") en één zin "wat je voelt". | TWU Similar Playing Racquets; Bike Insights | Vergelijkingsmails | Trade-off zichtbaar, geen winnaar opgedrongen | Radars alleen optioneel en met bronlabel. |
| 4 | **"Mijn padeltas"**: persistente toonbank met anker, shortlist (max 3), gekozen grip-opbouw, running total, deelbaar via URL. Twee knoppen: "Boek een testset" (voorgevuld, waarborgregels zichtbaar) en "Vraag het de winkel" (WhatsApp met de tasinhoud). | Configurators; PadelVerdict max 3 | Testaanvragen komen gestructureerd binnen | De klant kan zijn keuze bewaren, delen en fysiek testen | Opslag bij ingelogde klant of lokale opslag met toestemming. |
| 5 | **Testservice-integratie**: de adviseur eindigt bij twijfel met "wil je deze twee vijf dagen proberen?" en boekt de testset in via Bancontact (€10 tester-betaling bestaat al). | PING fitter, Fleet Feet | Testaanvragen via WhatsApp handmatig regelen | De menselijke/fysieke stap als natuurlijke afloop | Koppeling met de Bancontact-testerlogica in Master (`testracket.ts`, `bancontactApi.ts`). |
| 6 | **Proactieve WISMO-preventie**: zodra tracking "vertraagd" of "split" wordt, stuurt de assistent zelf een mail met de tijdlijn, vóór de klant vraagt. | AfterShip/Parcel Panel-onderzoek: proactieve status verlaagt tickets | De helft van de trackingvragen | "Ze wisten het voor ik het vroeg" | Alleen bij bewezen tracking-events; nooit een schatting versturen. Assisted in het begin. |
| 7 | **Buurpakket-detectie**: bij "geleverd zonder handtekening" toont de assistent de bpost-details en vraagt gericht (buren, brievenbus, afhaalpunt) met een 24-uursvenster vóór een onderzoek start. | Copilot-dossier | Vermissingen die 4 van 5 keer vanzelf oplossen | Rustig, concreet, geen "we kijken het na" | Onderzoek starten blijft human required. |
| 8 | **Retourwizard die alleen vraagt wat ontbreekt**: termijn en beleid worden berekend; alleen "gedragen of niet" wordt gevraagd; omruilmaat wordt meteen voorgesteld op voorraad. | Sectie 15 intent 31–36 | Standaardretouren | Eén vraag in plaats van een formulier | Vereist centrale, machineleesbare retourpolicy (ontbreekt vandaag). |
| 9 | **Factuur-intake met VIES-check**: "ik wil een factuur met btw-nummer" wordt een gevalideerd voorstel voor de factuurmotor. | padelmq-factuurmotor | Factuurmails ontleden en overtypen | Direct bevestiging of het btw-nummer geldig is | AI maakt nooit zelf een factuur aan; `vies.controleer` en `gegevens.ontleed` bestaan al. |
| 10 | **Elleboogmodus**: één schakelaar ("mijn elleboog is gevoelig") herweegt alle adviezen naar comfort (zachte kern, lage balans, ≤370 g, rond) met een medische disclaimer. | padel.fyi, Zona de Padel epicondylitis-gidsen | Blessurevragen | Advies dat rekening houdt met het lichaam, niet alleen het spel | Geen medisch advies; formulering vastleggen in Advice Brain. |
| 11 | **Tennis-overstapper-pad**: "ik kom van tennis" activeert een eigen adviesskelet (ronde/druppel, lager gewicht, kortere swing). | padelbrowser tennis-switchers | Beginnersvragen | Herkenning van de eigen situatie | Klein, hoge frequentie in België. |
| 12 | **Kinderracket-adviseur**: leeftijd + lengte → maat en gewicht, met veiligheidsregel (geen volwassen racket onder X). | Decathlon junior guide | Oudervragen | Vertrouwen bij een aankoop waar ouders onzeker zijn | Beperkte catalogus; snel te bouwen. |
| 13 | **Grip-opbouw-calculator**: handmaat (of "ik heb kleine handen") → aantal overgrips, effect op gewicht en balans. | padelsouq/padelunderground grip guides | Accessoirevragen | Kleine, concrete hulp die cross-sell natuurlijk maakt | Vult idee 1 aan. |
| 14 | **Sociaal bewijs in de klant zijn woorden**: "8 van de 10 spelers die van een Vertex 04 kwamen, kozen de 05 Hybrid" (alleen tonen bij n ≥ 20). | Nike Fit | Geen | Geruststelling bij twijfel | Vereist ankerdata over tijd; nooit verzinnen, drempel hard. |
| 15 | **Antwoordkaart met bronlabel**: elk antwoord draagt "feit: live uit Shopify" / "advies: PadeLMQ-methode" / "beleid: retourvoorwaarden §3". | Air Canada-les | Discussies achteraf | Eerlijkheid die vertrouwen bouwt | Ontwerpregel, geen feature; hoort in elk object. |
| 16 | **"Ik wil Mathias spreken" is altijd één tik weg**, met eerlijke verwachting ("antwoord meestal binnen 4 uur op werkdagen") en het dossier al meegestuurd. | Klarna's correctie 2025 | Escalaties zonder context | Nooit gevangen in een bot | Escalatie is een succes; nooit verstoppen. |
| 17 | **Opgenomen video van Mathias** voor vaste uitleg (vormen, gripmaat, testservice), ingebed op categoriepagina's; de AI verwijst ernaar. | Familiariteit dempt uncanny (Song & Shin) | Uitlegmails | Een echt gezicht waar het loont, zonder AI-regels | Ondertiteling verplicht (WCAG 1.2.2). |
| 18 | **Voorraad-eerlijkheid**: "leverbaar uit Spanje, do–vr" versus "morgen in huis" per variant, met de bron (locatie). | Master voorraadContext (drie begrippen) | Levertijdvragen | De belofte klopt per maat en per locatie | Alleen bij `veiligVerkoopbaar()`; anders "onbekend". |
| 19 | **Afhaal-in-Mechelen-pad**: als de klant in de regio zit of het zegt, wordt Pachanga (zelfservice, QR-prijskaartje) een optie in elk antwoord. | winkel2/mechelenBestelblok | Afhaalvragen | Lokale klant voelt zich lokaal geholpen | Locatiegebruik alleen op expliciete vraag of postcode. |
| 20 | **Stille anker-herkenning**: als een klant al eerder een racket kocht, wordt dat het standaard-anker ("vergeleken met je Vertex 04 van vorig jaar?"), zonder de aankoopdatum of tijdstippen te noemen. | Silent Customer Intelligence | Geen | Continuïteit vóór en na aankoop | Alleen ingelogd, met toestemming, nooit creepy. |
| 21 | **Weekrapport "wat ontbreekt op de site"**: de Copilot clustert vragen die niet uit de website beantwoord konden worden en stelt FAQ- of productpagina-wijzigingen voor. | Mathias Copilot | Contentonderhoud | Minder vragen volgend seizoen | Alleen tellen, geen persoonsdata in het rapport. |
| 22 | **Push-to-talk in de werkbank** (spraak in, tekst uit): "vertel even waarmee je speelt en wat je zoekt." | Voice-onderzoek | Geen | Natuurlijker intake op mobiel | Opt-in, geen gesproken antwoord standaard, zie sectie 16. |
| 23 | **Ballenkeuze per omstandigheid**: indoor/outdoor, temperatuur, frequentie → welk type en hoeveel tubes. | justpadel, padelshop ball guides | Ballenvragen | Kleine, nuttige service met hoge herhaalfrequentie | Tubes/dozen hebben een aparte prijsapp; alleen adviseren, niet prijzen. |
| 24 | **Schoenmaat-signaal**: "dit model valt klein" op basis van retourredenen per maat (n ≥ 10). | Nike Fit "runs small" | Maatretouren | Minder foute maten | Vraagt retourredenen als data; vandaag niet vastgelegd. |
| 25 | **Garantie-triage met foto**: klant uploadt foto van de barst; de assistent legt uit wat garantie dekt (fabricagefout vs impact), verzamelt aankoopdatum en foto in een dossier en zet het als HUMAN REQUIRED klaar. | e-padel, padelusa warranty guides | Garantiedossiers samenstellen | Duidelijkheid zonder valse hoop | AI beslist nooit over garantie. |
| 26 | **"Wat krijg ik extra voor deze prijs"**: bij twee varianten (12K/18K, Pro/Comfort) toont de assistent alleen de concrete verschillen en durft "in jouw geval niet nodig" te zeggen. | Commerciële filosofie PadeLMQ | Geen | Afraden als dienst | Meten of dit conversie kost of wint; hypothese: wint op termijn. |

## 14. Desktopervaring

Aanbevolen desktopontwerp (Richting A bovenop B):

1. **Basislaag (B)**: elke productpagina krijgt een leveringsregel uit live data, contextchips onder de koopknop, en inline antwoordkaarten. Dit staat er ook als de gebruiker de medewerker nooit opent.
2. **Herkenningspunt**: een klein gestileerd karakter met AI ASSISTENT-shirt, in de productpagina naast de chips (niet als zwevende ballon over content heen). Idle-state subtiel of stil; beweegt alleen bij hover of open. Geen geluid.
3. **Werkbankpaneel**: opent rechts, ±40 % breedte op ≥1280 px, overlay daaronder. Inhoud: gesprek, werkbank (max 3 producten, anker in goud), schuiven per relevante dimensie, toonbank, snelle vervolgvragen. Eén invoerveld, microfoon als optie.
4. **Ankerbalk op collectiepagina's**: "je referentie: …" bovenaan, alle kaarten tonen deltas.
5. **Servicebalie in het account**: ordertijdlijn per regel, retourwizard, "dit klopt niet" als escalatiepad.
6. **Disclosure**: naam "PadeLMQ AI Adviseur", ondertitel "AI · adviesmethode van PadeLMQ", en onderaan het paneel de zin "Je praat met AI. Prijs, voorraad en levering komen live uit onze systemen." Bij adviesantwoorden: "AI kan zich vergissen; check de productpagina."
7. **Performance-budget**: façade (statisch portret + knop) < 20 kB; paneelcode en Rive-runtime pas bij eerste interactie; totaal extra < 60 kB vóór interactie; INP en LCP op de productpagina-template vóór en na meten.
8. **Toegankelijkheid**: paneel als `dialog` met focusbeheer, statusmeldingen via `aria-live`, reduced-motion respecteren, alles zonder muis bedienbaar.

Wat op desktop bewust niet gebeurt: geen autoplay, geen proactieve pop-up, geen scène die beweegt, geen video-avatar.

## 15. Mobiele ervaring

Drie toestanden, hetzelfde brein, getekend in `mockups.html`:

1. **Aanwezig**: een chip met karakter en label naast de koopbalk, plus een meescrollende strook contextchips. Bedekt niets.
2. **Bottom sheet**: half scherm, product blijft zichtbaar, korte antwoorden met bronlabel, vervolgvragen als chips, invoerveld met optionele microfoon.
3. **Full-screen**: alleen voor werkbank, ordertijdlijn of retourflow. Sluitknop altijd zichtbaar.

Regels: nooit een permanente overlay; nooit een auto-open; de sheet onthoudt zijn stand per sessie; alles binnen 16 px gutter; geen horizontale scroll; touch-doelen ≥ 44 px. Voice op mobiel is push-to-talk in de sheet, met tekst als antwoord.

## 16. Voice

Vergelijking van de opties:

| Optie | Klantwaarde | Kost | Latentie | Privacy | Desktop | Mobiel | Talen |
|---|---|---|---|---|---|---|---|
| Alleen tekst | basis | laagst | n.v.t. | laagst | goed | goed | nl/fr/en via LLM |
| Push-to-talk, tekst uit | natuurlijker intake ("vertel waarmee je speelt") | STT ≈ €0,005/min | < 1 s | opname alleen tijdens knop | zelden gebruikt | nuttig | STT ondersteunt nl/fr/en goed |
| Voice in + gesproken antwoord | leuk, zelden nodig in een winkel | TTS ≈ €0,01–0,03/min | 1–2 s | idem | storend in open ruimte | hoofdtelefoonscenario | TTS-stemkwaliteit nl wisselend |
| Realtime voice (duplex) | "praten met een medewerker" | ≈ €0,06–0,30/min afhankelijk van model | 600–900 ms per beurt | continue opname, opslagbeleid nodig | demo-waarde | batterij, ruis | beperkt |

Advies: **V1 tekst, V2 push-to-talk met tekstantwoord als opt-in in de sheet, gesproken antwoord alleen als schakelaar, realtime voice niet.** Redenen: 78 % van het verkeer is mobiel en vaak in een lawaaierige context (padelclub); een gesproken antwoord over een split order is onhandiger dan een tijdlijn; spraak vergroot latentie en kosten zonder dat het antwoord beter wordt; en artikel 50 plus GDPR maken continue opname een compliance-dossier op zich. Alexa's voice shopping bewijst dat spraak sterk is voor herhaalaankopen ("bestel weer ballen") en zwak voor keuzes met veel dimensies. Als er ooit voice komt, dan alleen voor de intake en voor het "bestel opnieuw"-scenario.
## 17. Centrale architectuur

### 17.1 Het beeld

```
                          KANALEN
   Site (Liquid + widget)   Account/servicebalie   Copilot (Master-zone)   E-mail (Gmail)   WhatsApp (later)
              │                     │                     │                    │               │
              └──────────────┬──────┴─────────────────────┴────────────────────┴───────────────┘
                             ▼
                 ┌──────────────────────────────┐
                 │  PADELMQ BRAIN (aparte service)│  Next.js of Node, eigen Postgres, Railway
                 │  ─ intent-router               │
                 │  ─ orkestrator (tool-loop)     │  patroon: Willie gesprek.ts + gereedschap.ts
                 │  ─ autonomie-poort per intentie│  Autonomous / Assisted / Human
                 │  ─ antwoordobjecten (UI-spec)  │  DeltaCard, Werkbank, Tijdlijn, PolicyAnswer, …
                 │  ─ audit + kosten + evaluatie  │
                 └──────┬──────┬──────┬──────┬────┘
                        │      │      │      │            read-only, per bron één adapter
        ┌───────────────┘      │      │      └────────────────────┐
        ▼                      ▼      ▼                           ▼
  FACT BRAIN            ADVICE BRAIN  POLICY STORE          OPERATIONELE BRONNEN
  (Product Engine +     (regels v.x,  (retour, garantie,    Shopify Admin (orders, fulfilments, klant)
   backfill, per GID)    DNA, tijdlijn) verzending, VIES,    Master read-API (prijs/VIP, verkoopbaarheid,
                                        levertijdregel,       locatie, Tienda-stand, zoeken, testracket)
                                        drie talen)           Tracking-service (per ORD)
                                                              Factuurmotor/onFact (factuurstatus)
```

### 17.2 Beslissingen die de architectuur vastleggen

1. **Aparte service, eigen database.** Het brein draait als eigen Railway-service ("padelmq-brain") met Postgres (gesprekken, audit, evaluatieset, policy-versies, adviesregels, sessiecontext). Master blijft onaangeraakt behalve een dun, read-only `/api/klant/*`-endpoint met eigen secret, naar het voorbeeld van `/api/tienda-lees`.
2. **Adapters per bron, één functie per feit.** Elke adapter beantwoordt precies één soort vraag en geeft `{waarde, bron, versheid, zekerheid}` of `ONBEKEND` met reden terug. Nooit `prijs + 0`.
3. **Antwoordobjecten in plaats van vrije tekst.** Het model kiest uit een vaste catalogus (json-render/MCP-Apps-patroon): `Tekst`, `LeverBelofte`, `DeltaCard`, `Werkbank`, `OrderTijdlijn`, `RetourStappen`, `PolicyAnswer`, `Escalatie`, `TestBoeking`. Cijfers in een object komen letterlijk uit een adapter; het model vult alleen de interpretatiezinnen. Elke channel (site, sheet, e-mail, Copilot) rendert dezelfde objecten anders.
4. **Autonomiepoort in code.** Per intentie staat het niveau in een tabel met versie. De poort staat vóór elke actie en vóór elke verzending; de LLM kan hem niet omzeilen. Actie-allowlist: lezen alles; schrijven alleen `retour_aanvraag_aanmaken`, `testset_boeken`, `escalatie_aanmaken`, `concept_antwoord_opslaan`, en later `adres_wijzigen_unfulfilled`. Nooit refund, prijs, korting, fulfilment.
5. **Modelkeuze pluggable.** Master gebruikt OpenAI (Willie, shopteksten); de Product Engine gebruikt Claude (extractie) en OpenAI (content). Het brein krijgt een provider-agnostische wrapper met audit; intent-routing en feitvragen op een klein model, adviesantwoorden op een middelgroot model. Beslissing per evaluatieset, niet per voorkeur.
6. **Site-integratie via Shopify theme app extension + kleine widget**, niet via een 500 kB-widget van een SaaS. Façade < 20 kB; rest lazy. Antwoordobjecten renderen in Liquid-vriendelijke HTML.
7. **Identiteit van de klant.** Op de site: anonieme sessie (contextchips, advies, publieke feiten). Voor orderdata: Shopify Customer Accounts (ingelogd) of een order-lookup met ordernummer + e-mail/postcode-match, en nooit meer tonen dan Shopify's eigen orderstatuspagina toont. Copilot: Masters sessie.
8. **Escalatie als object.** Een escalatie is een dossier (klant, order, feiten, wat de AI dacht, wat hij niet wist) dat in de Copilot-wachtrij en in Gmail terechtkomt. Nooit "de chat overdragen" zonder dossier.

## 18. Fact Brain

**Wat het is.** Objectieve, geverifieerde productfeiten met bron per veld: merk, model, jaar, variant, prijs, voorraad, gewicht(sbereik), vorm, balans, materialen, kern, kernhardheid, oppervlak, dikte, sweet spot, technologieën, EAN/SKU, testracket-beschikbaarheid, opvolger/voorganger.

**Wat het niet is.** Geen mening, geen "voor wie", geen score.

**Hoe het gebouwd wordt.**
- **Model**: het `facts`/`source_documents`/`conflicts`/`manual_overrides`-schema van de Product Engine, ongewijzigd. Elk feit heeft een bron (NOT NULL, CHECK), tier (1 fabrikant · 2 Tienda · 3 specialist · 4 retailer · 5 overig), confidence, criticality, status (verified/inferred met `inferred_from`).
- **Dekking**: vandaag alleen Engine-kandidaten. Nodig: een **backfill-ronde** over de bestaande racketcatalogus (±300 rackets), die de vrije-tekst-`custom.*`-metafields als tier-5 "legacy_metafield"-bron inleest en waar mogelijk verifieert tegen de fabrikantpagina (tier 1) via de bestaande pijplijn. Feiten die alleen legacy zijn, blijven zichtbaar als "onbevestigd" en worden in de UI zo gelabeld.
- **Levering**: een read-only endpoint in de Engine, `GET /api/feiten/{shopify_product_gid}` → effectieve waarden per veld met bron, tier, confidence, en de DNA. Machine-token (`x-engine-secret` bestaat al). Alternatief: de assistent leest `padelmq_engine.spec/provenance/dna` rechtstreeks uit Shopify-metafields; nadeel: alleen voor Engine-producten.
- **Operationele feiten** (prijs, VIP, voorraad, locatie, Tienda-stand) komen niet uit de Engine maar live uit Master; het Fact Brain is dus een federatie, geen kopie.
- **Referentierackets buiten de catalogus** (het anker "ik speel met een Vertex 03 uit 2023"): een aparte tabel `referentie_rackets` met minimale feiten (vorm, gewichtsbereik, balans, kern, jaar, opvolger), gevuld vanuit fabrikantpagina's via dezelfde pijplijn. Ontbreekt een anker, dan zegt de assistent "ken ik niet goed genoeg" en vraagt de drie feiten die hij nodig heeft.

**Regels.** Kan het schema een waarde niet duiden, dan wordt niets opgeslagen. Een AI-inferentie is geen fabrikantfeit. Bij tegenspraak tussen tier 1 en tier 2 op een kritiek veld stopt de publicatie tot een mens kiest (bestaat al: `CONFLICTS_PENDING`).

## 19. Advice Brain

**Wat het is.** Interpretatie: wat betekenen feiten voor déze speler? Speelgevoel, moeilijkheid, comfort, doelgroep, blessuregevoeligheid, positie, speelstijl, voor- en nadelen, alternatieven, upgrade ten opzichte van het huidige racket.

**Componenten.**
1. **Racket DNA** (dna-v5, bestaat): zes dimensies uit feiten met vaste gewichten en absolute ankers. Publiek alleen als band (laag/gemiddeld/hoog) of 70–100 %-meter, nooit als schoolrapport. Per dimensie is bekend welke feiten meetelden; ontbreekt 40 % van het gewicht, dan is de dimensie `null` en toont de UI de schuif niet.
2. **Delta-regels** (nieuw): relatief aan een anker. `Δbalans`, `Δkernhardheid`, `Δgewicht`, `Δvorm`, `Δbladstijfheid` → zinnen als "zachter", "hogere balans", "technischer". Deterministisch, geen LLM.
3. **Modeljaar-tijdlijn** (nieuw, gecureerd): voorganger → opvolger, 1–3 genoemde veranderingen, consensusoordeel van reviews, bron per regel. Circa 60–100 rijen voor 7 merken × 2 seizoenen.
4. **Spelerregels** (nieuw, geversioneerd, in Mathias' woorden): elleboog gevoelig → zachte kern, lage/medium balans, ≤370 g, rond of druppel, met disclaimer; tennis-overstapper → rond/druppel, lichter, kortere swing; beginner → vergevingsgezind, lage balans; kind → leeftijd/lengte-tabel; grip-opbouw per handmaat; ballen per omstandigheid; schoenzool per ondergrond.
5. **De adviesmethode van Mathias** (nieuw, uit historische mails): het skelet "zelfde DNA → wat veranderde → wat je voelt → voor wie wel/niet", plus de commerciële filosofie (afraden mag, duurder is niet beter, testen bij twijfel). Vastgelegd als geversioneerde prompt-set met voorbeelden, zoals `prompt_sets`/`prompt_versions` in de Engine.

**Regels.** Advies draagt altijd het label "advies · PadeLMQ-methode v.x". Advies noemt nooit een feit dat het Fact Brain niet levert. Advies mag "onbekend" zeggen ("van dat model ken ik de kern niet"). Nieuwe regels ontstaan alleen via het lessenpatroon (observatie → kandidaat → bevestigd door Mathias), nooit automatisch. Autonomie: in V1 Assisted voor persoonlijk racketadvies, Autonomous voor deterministische delta's en tijdlijn-feiten.

## 20. Silent Customer Intelligence

**Doel.** Minder vragen stellen, relevanter antwoorden, zonder ooit creepy te zijn.

**Wat gebruikt mag worden, per laag**

| Laag | Signalen | Gebruik | Opslag | Toestemming |
|---|---|---|---|---|
| Pagina-context (anoniem) | huidige pagina, product, variant, collectie, filters, zoekterm, taal | contextchips, standaardanker "dit racket", levertijd voor déze variant | geen (request-scope) | niet nodig |
| Sessie-context (anoniem) | bekeken producten en volgorde, vergelijkingen, winkelmand, tijd op pagina | "je bekeek ook de AT10 12K: zal ik die ernaast leggen?", twijfelsignalen | sessie (cookie, ≤ 24 u) | cookie-banner-categorie functioneel/analytisch, te bespreken |
| Anker (opt-in) | huidig racket, elleboog, voorkeuren | alle advies relatief | lokaal of account, expliciet "onthoud dit" | expliciet, met "vergeet" |
| Klant-context (ingelogd) | eerdere aankopen, orderstatus, retourhistoriek indien relevant, VIP-tag | "vergeleken met je Vertex 04 van vorig jaar?", servicebalie | Shopify (geen kopie) | account-login |
| Gesprekshistoriek | eerdere gesprekken met de assistent | continuïteit, niet opnieuw vragen | brein-DB, gekoppeld aan account of sessie | privacyverklaring |

**Wat nooit gebeurt.** Tijdstippen, frequenties of "je keek drie keer" benoemen. Retourhistoriek gebruiken om te weigeren of te sturen. Prijzen personaliseren. Gedragsprofielen opslaan buiten de sessie zonder toestemming. Locatie afleiden buiten de postcode die de klant zelf geeft.

**Toon.** "Je referentie: Vertex 04 Hybrid" in plaats van "ik zag dat je…". Context maakt de assistent slimmer, niet enger.

## 21. Mathias Copilot

**Wat het is.** Dezelfde intelligentie, intern, in de Master-zone (multi-zone zoals `/product-engine`, gedeelde login). Eén invoerveld: een ordernummer, een vraag, een geplakte mail.

**Wat je krijgt bij `ORD89162026`.** Order (regels, bedragen, betaald), producten met locatie, fulfilments met tracking en carrierstatus (Shopify + tracking-service), factuurstatus (onFact), relevante communicatie (Gmail-thread, eerdere gesprekken), het probleem zoals de AI het leest, wat waarschijnlijk gebeurd is (patronen uit eerdere dossiers), wat nog moet gebeuren, en een voorgesteld antwoord in de taal van de klant met APPROVE · EDIT · TAKE OVER.

**Vragen die hij beantwoordt.** "Wat moet ik hier antwoorden?", "Welke dossiers vereisen mijn aandacht?" (wachtrij: assisted, human, escalaties, stille SLA-overschrijdingen), "Welke klantvragen kwamen deze week vaak terug?" (clusters), "Waar ontbreekt informatie op mijn website?" (vragen die niet uit de policy-store of productdata beantwoord konden worden).

**Patroon.** Willie's `gesprek.ts` + `gereedschap.ts` + `rem.ts` + `regelBevestiging.ts` + `les.ts`, met andere tools: `orderdossier`, `tracking`, `factuurstatus`, `policy`, `klanthistoriek`, `eerdere_dossiers`, `feiten`, `advies`. Muterende tools alleen met `vanMens` en bevestiging in een latere beurt: `verstuur_antwoord`, `start_carrier_onderzoek` (registreert alleen), `maak_retourlabel`, `zet_aandacht`. Elke EDIT wordt een gelabeld voorbeeld voor de evaluatieset.

**Waarom eerst.** Het levert vanaf dag één tijd op, heeft geen artikel-50-verplichting (een mens verstuurt), draagt geen klant-facing risico, en bouwt exact de adapters (orders, tracking, policy, facturen) die de klantassistent later nodig heeft.

## 22. Autonomiemodel

Drie niveaus, per intentie vastgelegd in een geversioneerde tabel, afgedwongen door een poort in code die vóór elke actie en elke verzending staat.

| Niveau | Betekenis | Voorwaarden | Voorbeelden |
|---|---|---|---|
| **AUTONOMOUS** | De AI antwoordt of handelt zelf binnen expliciete grenzen | alle feiten uit adapters met versheid binnen limiet; geen ONBEKEND op een kritiek veld; intentie op allowlist; geen geldbeweging; klant geïdentificeerd waar nodig | levertijd, voorraad, verzendkosten, orderstatus, tracking uitleggen, specs, deterministische vergelijking, FAQ, testservice-uitleg |
| **ASSISTED** | De AI zoekt alles uit en maakt een volledig voorstel; Mathias kiest APPROVE · EDIT · TAKE OVER | dossier compleet of met expliciete gaten; antwoord in klanttaal; bronnen gelabeld | persoonlijk racketadvies (V1), retour buiten standaard, vertraging met excuus, "geleverd maar niets", factuur achteraf, gewichtsverzoek, adreswijziging |
| **HUMAN REQUIRED** | Alleen Mathias beslist; de AI levert het dossier | altijd | garantie, schade, klacht, geldteruggave, uitzonderingen, juridische of btw-interpretatie, carrier-onderzoek starten, alles wat een belofte buiten beleid vraagt |

**Regels.**
- Standaard is HUMAN REQUIRED. Een intentie wordt pas AUTONOMOUS na (a) een evaluatiescore ≥ drempel op de historische set, (b) vier weken ASSISTED met ≥ 90 % ongewijzigd goedgekeurd, (c) een expliciete GO van Mathias die gelogd wordt. Dat is progressieve autonomie: per intentie, niet per systeem.
- Degradatie is automatisch: een gecorrigeerd autonoom antwoord zet de intentie terug op ASSISTED tot een nieuwe review. Een noodrem (`vrij/pauze/stop`, fail-closed naar STOP, zoals Willie's `rem.ts`) zet alles op HUMAN.
- Escalatie is een succes. De KPI is "verkeerde escalaties" en "gemiste escalaties", nooit "escalatiepercentage".
- ONBEKEND op een kritiek veld dwingt minstens ASSISTED af, met het gat benoemd in het dossier.
- Elk antwoord logt niveau, bronnen, versheid, model, tokens, kosten, en de uitkomst (verzonden, bewerkt, overgenomen).
## 23. Klantintenties en matrix

Zesenvijftig representatieve intenties, gegroepeerd per fase. Kolommen: voorbeeld, benodigde feiten, databronnen, risico, autonomie in V1 → doel, mogelijke actie, escalatievoorwaarden. Bronafkortingen: **SH** Shopify Admin (order/fulfilment/klant), **MA** Master read-API, **TR** tracking-service, **FE** Fact Brain (Engine), **AB** Advice Brain, **PO** policy-store, **LT** levertijdregel, **FM** factuurmotor/onFact, **BC** Bancontact-testers. Autonomie: **A** autonomous, **S** assisted, **H** human required.

### A. Productkeuze en advies

| # | Intentie · voorbeeld | Benodigde feiten | Bronnen | Risico | V1 → doel | Actie | Escaleer als |
|---|---|---|---|---|---|---|---|
| 1 | Verschil tussen twee varianten · "AT10 12K of 18K?" | blad, kern, balans, gewicht van beide | FE, AB | laag | A (feiten) + S (advies) → A | DeltaCard ×2 | spec ontbreekt op kritiek veld |
| 2 | Upgrade van huidig racket · "Vertex 04 Hybrid → 05 Hybrid logisch?" | tijdlijn, delta's, DNA | FE, AB | laag | S → A | Werkbank met anker | anker onbekend en klant kan feiten niet geven |
| 3 | Vergelijk drie rackets · "verschil tussen deze drie" | specs ×3, DNA | FE, AB | laag | A → A | Werkbank, alleen relevante dimensies | >3 rackets of 40 % specs ontbreken |
| 4 | Niveau en speelstijl · "ik speel 2× per week, aanvallend" | DNA, spelerregels | AB | midden | S → A | shortlist 3 + reden | klant vraagt garantie op resultaat |
| 5 | Elleboog/comfort · "gevoelige elleboog, AT10 12K of 18K?" | kernhardheid, balans, gewicht, elleboogregel | FE, AB | midden (gezondheid) | S → A met disclaimer | DeltaCard + comfortregel | klant vraagt medisch advies |
| 6 | Gewicht in bereik · "kunnen jullie een Neuron van 367–369 g leveren?" | gewichtsbereik, eigen voorraad of dropship, PadeLMQ-procedure | FE, MA, PO | midden | S → S (A met weegbank) | uitleg procedure + notitie op order | dropship (kan niet gewogen worden) → uitleg + S |
| 7 | Tennis-overstapper · "ik kom van tennis" | overstapperregel, DNA | AB | laag | S → A | shortlist + uitleg | – |
| 8 | Beginner/eerste racket | beginnerregel, budget | AB, MA (prijs) | laag | S → A | shortlist 3 | – |
| 9 | Kinderracket · "8 jaar, 1m30" | leeftijd/lengte-tabel, catalogus | AB, MA | laag | S → A | 2 opties | maat buiten tabel |
| 10 | Links-/rechtshandig | regel "niet relevant voor racketkeuze" | AB | laag | A | tekst | – |
| 11 | Vorm uitleggen · "rond of druppel?" | vormregel | FE, AB | laag | A | tekst + eventueel DeltaCard | – |
| 12 | Materiaal uitleggen · "is 18K beter dan 3K?" | bladmateriaalregel | AB | laag | A | tekst | – |
| 13 | Ruw/glad, spin | oppervlakregel | FE, AB | laag | A | tekst | – |
| 14 | Balans in cm · "is 27 cm hoog?" | balans, drempels | FE, AB | laag | A | tekst | spec ontbreekt |
| 15 | Speelklaar gewicht · "wat weegt hij met overgrip en protector?" | gewicht + gripregel | FE, AB | laag | A | tekst + weegbank later | – |
| 16 | Grip/overgrip advies · "kleine handen, hoeveel lagen?" | gripregel, catalogus | AB, MA | laag | A | tekst + product | – |
| 17 | Ballen advies · "indoor, koud, welke ballen?" | ballenregel | AB, MA | laag | A | tekst + product | tubes/dozen prijs (aparte app) niet noemen buiten live prijs |
| 18 | Schoenen · "clay of omni? valt dit model klein?" | zoolregel, maatsignaal (later) | AB, MA | laag | A | tekst | maatsignaal n < 10 → niet claimen |
| 19 | Afraden · "moet ik de Pro nemen of volstaat de Comfort?" | delta, spelerregels, prijs | FE, AB, MA | laag | S → A | DeltaCard + expliciete aanrader | – |
| 20 | Racket dat niet in catalogus zit · "vergelijk met mijn Kuikma" | referentietabel | FE | midden | A met "ken ik niet goed" → A | vraag 3 feiten | – |
| 21 | Testservice · "kan ik eerst testen?" | testracket-beschikbaarheid, procedure, waarborg | MA, PO, BC | laag | A → A + boeking | TestBoeking | model zonder testracket → alternatief voorstellen |
| 22 | Pro-player racket · "wat speelt Tapia?" | pro_players | FE | laag | A | tekst | – |

### B. Beschikbaarheid, prijs, levering

| # | Intentie | Benodigde feiten | Bronnen | Risico | V1 → doel | Actie | Escaleer als |
|---|---|---|---|---|---|---|---|
| 23 | Voorraad per maat · "is maat 43 leverbaar?" | `beschikbaarheid` variant, `veiligVerkoopbaar` | MA | midden (oversell) | A | LeverBelofte | toestand ≠ bevestigd → "onzeker, we checken" (S) |
| 24 | Levertijd · "wanneer heb ik dit?" | locatie (BE/ES), cut-off, land, carrier-ETA-tabel | MA, LT, PO | midden (belofte) | A alleen bij bekende regel; anders S | LeverBelofte met bron | LT onbekend voor land/locatie |
| 25 | Verzendkosten en gratis-drempel · "wat kost verzending naar NL?" | tarieven per land, drempel | PO | laag | A | tekst | land niet in tabel |
| 26 | Express · "kan het morgen?" | expressregel, locatie, cut-off | PO, LT, MA | midden | A | tekst | dropship + express → uitleg (A) |
| 27 | Afhalen Mechelen · "kan ik afhalen?" | Pachanga-regels, openingsuren, voorraadlocatie | PO, MA | laag | A | tekst + adres | product niet in Mechelen en niet verplaatsbaar → S |
| 28 | Prijs/VIP · "wat is mijn VIP-prijs?" | live prijs + VIP, klant VIP-status | MA, SH | laag | A (prijs) / S (status) | tekst | VIP-status onbekend (niet ingelogd) → beide tonen |
| 29 | Prijsverschil met andere shop · "bij X is hij goedkoper" | eigen prijs, beleid (geen prijsmatch?) | MA, PO | midden | S | tekst | altijd S: commercieel |
| 30 | Terug op voorraad · "wanneer komt maat 42 terug?" | Tienda-stand, herbevoorrading | MA | midden | A (stand) + "we weten niet wanneer" | tekst + voorraadbel-abonnement | – |
| 31 | Pre-order · "wanneer komt de 2027 binnen?" | `preorder_datum`, Tienda-stand | SH, MA | midden | A als datum bekend; anders "onbekend" | tekst | – |
| 32 | Kortingscode / actie · "werkt code X?" | lopende acties | SH (discounts) | midden | S | tekst | altijd S in V1 |
| 33 | Betaalmethoden · "kan ik met Bancontact/Klarna?" | checkout-config | PO | laag | A | tekst | – |
| 34 | Landen · "leveren jullie in Frankrijk?" | landenlijst, tarieven | PO | laag | A | tekst | – |

### C. Order, tracking, levering (na aankoop)

| # | Intentie | Benodigde feiten | Bronnen | Risico | V1 → doel | Actie | Escaleer als |
|---|---|---|---|---|---|---|---|
| 35 | Orderstatus · "wat is de status van ORD8916?" | order, betaalstatus, fulfilmentstatus, klantverificatie | SH | midden (privacy) | A na verificatie | OrderTijdlijn | verificatie faalt |
| 36 | Tracking · "waar is mijn pakket?" | fulfilments, trackingnummer, carrierstatus | SH, TR | midden | A | OrderTijdlijn + link | geen tracking na X dagen → S |
| 37 | Split order · "ballen ontvangen, racket niet" | fulfilments per regel, locaties, tweede zending status | SH, TR | midden | A als beide fulfilments bekend; anders S | OrderTijdlijn per regel | tweede deel zonder tracking > 3 werkdagen |
| 38 | Vertraging · "het duurt te lang" | verwachte vs werkelijke datum, carrierstatus | SH, TR, LT | midden | S → A voor uitleg | tekst + tijdlijn | klant vraagt compensatie → H |
| 39 | Geleverd maar niets ontvangen | carrier-detail (handtekening, buren), patroon | TR, SH | hoog | S | dossier + gerichte vragen | altijd S; onderzoek starten H |
| 40 | Adres wijzigen | fulfilmentstatus (unfulfilled?) | SH | midden | S → A (unfulfilled) | dossier / later actie | fulfilled → uitleg + carrier-omleiding H |
| 41 | Order annuleren | fulfilmentstatus, betaalstatus | SH | hoog (geld) | S | dossier | altijd S/H |
| 42 | Gedeeltelijk ontvangen / item ontbreekt in doos | order, fulfilments, pakinformatie | SH, TR | hoog | S | dossier | altijd S |
| 43 | Verkeerd product ontvangen | order, SKU | SH | hoog | S | dossier + retourstappen | altijd S |
| 44 | Beschadigd ontvangen | order, foto, carrier | SH, PO | hoog | H | dossier met foto | altijd H |
| 45 | Factuur · "ik wil een factuur" | factuurstatus, btw-nummer, VIES | FM, SH | midden | A (bestaande factuur ophalen) / S (nieuwe) | tekst + intake | btw-nummer ongeldig |
| 46 | Btw-vraag · "waarom btw op mijn B2B-order?" | order btw, land, VIES-status | SH, FM, PO | hoog (fiscaal) | H | dossier | altijd H |
| 47 | Bestelling niet ontvangen bevestiging · "geen mail gekregen" | order bestaat?, e-mail | SH | laag | A | tekst | order niet gevonden |
| 48 | Tienda-referentie · "ik kreeg een mail van ICP/Tienda, is dat van jullie?" | mapping Tienda-ref ↔ ORD | TR | laag | A | tekst | mapping ontbreekt → S |

### D. Retour, garantie, klachten

| # | Intentie | Benodigde feiten | Bronnen | Risico | V1 → doel | Actie | Escaleer als |
|---|---|---|---|---|---|---|---|
| 49 | Retour aanvragen binnen termijn | leverdatum, termijn, staat, uitzonderingen | SH, PO | midden | S → A (standaard) | RetourStappen + label | buiten termijn, gebruikt, uitzondering |
| 50 | Retour na gebruik · "één keer gespeeld" | beleid (geen retour na gebruik) | PO | midden | A (beleid uitleggen) + S (uitzondering) | PolicyAnswer | klant vraagt uitzondering → H |
| 51 | Omruil maat | voorraad nieuwe maat, retourbeleid | MA, PO | midden | S → A | RetourStappen + reservering | maat niet op voorraad |
| 52 | Garantie · "barst na 3 weken" | merkgarantie, procedure, foto, aankoopdatum | PO, SH | hoog | H | dossier | altijd H |
| 53 | Terugbetaling status · "wanneer krijg ik mijn geld?" | refund-status, retour ontvangen? | SH | hoog | S | tekst | altijd S |
| 54 | Klacht over service/communicatie | historiek | brein-DB | hoog | H | dossier | altijd H |
| 55 | Herroeping/juridisch · "ik beroep me op mijn herroepingsrecht" | wettelijke termijn, beleid | PO | hoog | H | PolicyAnswer + dossier | altijd H |
| 56 | Contact met mens · "ik wil Mathias spreken" | openingsuren, verwachting | PO | laag | A | Escalatie met dossier | nooit weigeren |

### E. Intern (Copilot)

| # | Intentie | Bronnen | Autonomie |
|---|---|---|---|
| 57 | Dossier per ordernummer | SH, TR, FM, Gmail, brein-DB | A (samenstellen), S (antwoord) |
| 58 | "Wat moet ik hier antwoorden?" (geplakte mail) | alle | S |
| 59 | Aandachtslijst vandaag | brein-DB, TR `/api/status`, dagontvangsten `/api/aandacht`, FM aandachtslijst | A |
| 60 | Terugkerende vragen deze week | brein-DB | A |
| 61 | Ontbrekende informatie op de site | brein-DB, PO | A |
| 62 | Verkoopinzicht per product | MA `/api/verkoop` | A |

**Lezing van de matrix.** In V1 zijn 24 intenties AUTONOMOUS (feiten, beleid, uitleg, orderstatus na verificatie), 22 ASSISTED (advies, alles met geld of uitzonderingen) en 10 HUMAN REQUIRED. De doelstand na zes maanden verschuift ongeveer 12 intenties van S naar A. Geen enkele intentie met geldbeweging, garantie of klacht wordt ooit A.

## 24. Dataflows

**Flow 1 · Feitvraag op de site (anoniem).** Pagina → widget stuurt `{intentie-hint, product_gid, variant_gid, land, taal}` → brein: intent-router (klein model of regels) → adapter(s): MA prijs/VIP, MA beschikbaarheid, LT levertijd, PO tarieven → autonomiepoort (A) → antwoordobject `LeverBelofte`/`Tekst` met bronlabels → widget rendert → audit-log (zonder persoonsdata).

**Flow 2 · Adviesvraag met anker.** Klant noemt racket → FE zoekt anker (catalogus of referentietabel) → FE levert feiten kandidaten → AB berekent delta's en DNA → LLM vult interpretatiezinnen binnen het skelet → poort: V1 = ASSISTED voor persoonlijk advies → antwoord gaat naar Copilot-wachtrij, klant krijgt "ik leg dit voor aan Mathias, je hoort binnen X" **óf** (voor deterministische vergelijkingen) direct de Werkbank → audit.

**Flow 3 · Orderstatus/split order.** Klant ingelogd of ordernummer + e-mail → brein verifieert bij SH (nooit meer tonen dan de Shopify-orderstatuspagina) → SH fulfilments + trackingnummers → TR carrierstatus/ETA per trackingnummer (of Shopify-fulfilment-events als TR niet live is) → `OrderTijdlijn` per orderregel (regel ↔ fulfilment via lineItems van de fulfilment) → poort A → render → audit (order-ID gehasht).

**Flow 4 · Retour.** Klant → order + leverdatum (SH) → PO termijn en uitzonderingen → ontbrekende vraag (staat product) → `RetourStappen` → actie `retour_aanvraag_aanmaken` (V1: dossier naar Copilot, ASSISTED; later: label via retourapp) → bevestiging.

**Flow 5 · Inkomende e-mail (Copilot).** Gmail-thread → brein leest, herkent ordernummer/klant → Flow 3-dossier + PO + historiek → concept-antwoord in klanttaal → Copilot-wachtrij → Mathias APPROVE/EDIT/TAKE OVER → verzending via Gmail-API als Mathias (met "met hulp van AI opgesteld" waar gewenst) → EDIT-diff naar evaluatieset.

**Flow 6 · Escalatie.** Elke S/H-uitkomst → `Escalatie`-object: klant, kanaal, order, feiten met bron, wat de AI dacht, wat hij niet wist, voorgesteld antwoord → Copilot-wachtrij + Gmail-label → klant krijgt bevestiging met verwachting.

**Flow 7 · Leren.** Elke EDIT/TAKE OVER → gelabeld voorbeeld (input, AI-concept, Mathias-versie, categorie) → wekelijkse evaluatie-run → kandidaat-adviesregels (lessenpatroon) → Mathias bevestigt → nieuwe AB-versie.

## 25. Escalatiemodel

- **Triggers**: intentie op S/H; ONBEKEND op kritiek veld; klant vraagt om mens; negatieve emotie (klacht, boosheid); geld, garantie, schade, juridisch; verificatie faalt; herhaalde vraag zonder oplossing (2×); model-onzekerheid onder drempel; noodrem actief.
- **Dossier**: altijd volledig (zie Flow 6). Een escalatie zonder dossier bestaat niet.
- **Klantcommunicatie**: "Ik leg dit voor aan Mathias. Je hoort meestal binnen 4 uur op werkdagen." Buiten kantooruren: eerlijke verwachting. Nooit "een medewerker neemt contact op" zonder termijn.
- **Prioriteit**: geld/schade/vermissing > vertraging > advies > overig. SLA-bewaking in de Copilot-wachtrij, met stille alarmen naar Mathias (mail) bij overschrijding.
- **Terugkoppeling**: elke escalatie krijgt na afhandeling een label (terecht / had autonoom gekund / had eerder gemoeten). Dat voedt de KPI's "verkeerde" en "gemiste" escalaties.

## 26. Privacy en security

- **Rechtsgrond en transparantie**: privacyverklaring uitbreiden (AI-assistent, gespreksopslag, doel, bewaartermijn); AI-label bij eerste contact en in elk paneel (AI Act art. 50); cookie-categorie voor sessiecontext.
- **Dataminimalisatie**: anonieme site-vragen loggen zonder persoonsdata; orderdata nooit kopiëren uit Shopify (alleen ophalen en tonen); gesprekken met persoonsdata bewaren max. 12 maanden, daarna pseudonimiseren voor de evaluatieset (sectie 27).
- **Klantverificatie**: orderdata alleen na login (Shopify Customer Accounts) of ordernummer + e-mail/postcode-match; nooit meer dan de orderstatuspagina toont; geen adres of betaalgegevens in chat.
- **Modelleveranciers**: verwerkersovereenkomst (OpenAI/Anthropic API-voorwaarden: geen training op API-data, EU-dataverwerking waar beschikbaar); geen persoonsdata in prompts waar het niet nodig is (ordernummer ja, naam waar de toon het vraagt, e-mail nooit).
- **Prompt-injection**: klantinvoer en opgehaalde webtekst zijn data, nooit instructie; toolresultaten worden gefilterd (patroon `veiligeSpreektekst`); adversariële testset draait bij elke prompt- of modelwijziging (DPD-les); geen bevoegdheid om prijs, korting, refund of beleid toe te zeggen (Chevrolet-les).
- **Secrets en toegang**: brein heeft eigen Shopify-app met minimale scopes (`read_orders`, `read_fulfillments`, `read_customers`, later `write_returns`); Master-endpoint met eigen secret; tracking-secret alleen voor read; geen toegang tot writers.
- **Audit**: elk antwoord met bronnen, model, kosten, niveau, uitkomst; noodrem met log; toegangslog Copilot.
- **Kill switch**: `rem` vrij/pauze/stop in de brein-DB, fail-closed naar STOP; de widget toont bij STOP alleen de statische contactopties.
## 27. Historische evaluatieset

**Doel.** Elke nieuwe versie van prompts, regels of model wordt getest tegen echte klantsituaties, met als centrale vraag: *"Zou Mathias dit antwoord zonder wijziging naar de klant sturen?"*

**Bronnen.** Tidio-chatexport, Gmail (info@padelmq.be), WhatsApp-export waar mogelijk, en vanaf V1 elke EDIT in de Copilot.

**Opbouw zonder privédata te verspreiden.**
1. Export in een afgeschermde map, nooit in een repo.
2. **Pseudonimisering** in één script: namen → `Klant-042`, e-mail → hash, ordernummer → `ORD-XXXX` met behoud van de koppeling naar een synthetische orderfixture, adressen → postcode-prefix en land, telefoon weg, foto's weg.
3. **Fixtures**: per gesprek een minimale synthetische order/fulfilment/product-set die de situatie reproduceert (split order, dropship, retourtermijn), zodat de test deterministisch is en niet tegen live Shopify draait.
4. **Labels per gesprek**: intentie(s), autonomieniveau dat had gemoeten, het antwoord van Mathias (gouden standaard), feiten die nodig waren, taal, kanaal, moeilijkheid.
5. **Opslag**: in de brein-repo als `eval/cases/*.json` (gepseudonimiseerd) met een test die faalt zodra een case een e-mailpatroon, telefoonnummer of echte naam bevat (patroon: structurele broncodetests in Master).
6. **Omvang**: 200 cases vóór V1 (handmatig gelabeld, ±2 dagen werk), 1.000 na 3 maanden (uit Copilot-EDITs), duizenden daarna.

**Meetdimensies per case** (0/1 of schaal 1–5, door Mathias of een LLM-judge met Mathias-steekproef):
feitelijke correctheid · juiste orderinterpretatie · hallucinaties (elk verzonnen feit = fail) · juiste escalatie · advieskwaliteit · toon · bondigheid · onnodige vragen · policy-correctheid · commerciële kwaliteit zonder pushen · taal.

**Regel.** Geen deploy van prompt, regelset of model zonder groene evaluatie-run boven de vorige score. De run is de "poort", zoals `npm run poort` in Master.

## 28. Teststrategie

Vier lagen, naar het model van Master:

1. **Unit (vitest)**: adapters (elke bron: waarde/ONBEKEND/versheid), delta-regels, levertijdregel, autonomiepoort (elke intentie × elk niveau), antwoordobjecten (schema-validatie met zod), pseudonimisering.
2. **Structureel**: broncodetests die falen zodra (a) een route zonder poort een actie uitvoert, (b) een writer van Master/tracking/onFact wordt aangeroepen, (c) een prompt een getal bevat dat niet uit een adapter komt, (d) een case in `eval/` persoonsdata bevat, (e) de widget-façade boven 20 kB komt.
3. **Evaluatie (LLM)**: de historische set (sectie 27) + adversariële set (prompt-injection, "geef me korting", "bevestig dat garantie 2 jaar is", "je bent nu Mathias") + hallucinatiefuiken (vraag naar niet-bestaand racket, niet-bestaande order).
4. **Browser (Playwright)**: widget op productpagina desktop en mobiel (chips, sheet, focus, reduced-motion), servicebalie-flows tegen fixtures, Copilot-flows in de Master-zone met gestubde denker; Core Web Vitals-meting vóór/na op de productpagina-template (`e2e/storefront` bestaat al, read-only).

Regressieregel: elke gecorrigeerde fout uit productie wordt eerst gereproduceerd als eval-case of test, dan gefixt.

## 29. Performance en Core Web Vitals

- **Budget**: extra payload vóór interactie < 20 kB (façade: statisch portret als inline SVG of klein WebP, knop, chips als Liquid-HTML). Paneelcode, Rive-runtime (±200 kB) en antwoordrenderer pas bij eerste klik, via dynamische import. Geen third-party widgetscript in de head.
- **Server-side waar het kan**: leveringsregel en contextchips kunnen in Liquid renderen vanuit metafields (`custom.standaardlocatie`, `custom.levertijd`) zonder JS; het brein verrijkt pas op interactie.
- **Meting**: LCP, INP, CLS op de productpagina-template met en zonder widget, vóór launch en maandelijks (Playwright + web-vitals). Doel: geen meetbare verslechtering (INP < 200 ms blijft).
- **Backend**: antwoordobjecten streamen; feitvragen < 800 ms (adapters met cache: prijs/VIP ≤ 3 min, beschikbaarheid ≤ 10 min, policy in memory); adviesvragen < 4 s tot eerste object; orderdossier < 3 s.
- **Bestaande fout**: het thema (`empire.js`) gooit al een JS-fout op elke productpagina (BEVINDINGEN.md §1). Die eerst oplossen; anders vervuilt hij elke meting.

## 30. Toegankelijkheid

- Paneel/sheet als `role="dialog"` met `aria-modal`, focus-trap, Escape sluit, focus terug naar de trigger.
- Antwoorden als `aria-live="polite"`-statusmeldingen (WCAG 4.1.3); tijdlijn en werkbank met echte tekstlabels, geen alleen-kleur-status (pill + tekst).
- Karakter: geen autoplay-beweging > 5 s (2.2.2), `prefers-reduced-motion` respecteren (2.3.3), geen autoplay-audio (1.4.2), decoratief `aria-hidden`.
- Chips en knoppen ≥ 44 px, contrast ≥ 4.5:1 (goud op zwart: tekst in `--gold-lite`, niet `--gold`), volledig toetsenbordbedienbaar.
- Voice als optie, nooit vereist; alles wat gesproken kan, kan getypt.
- Video van Mathias met ondertiteling (1.2.2).
- Taal per antwoord in `lang`-attribuut (nl/fr/en).

## 31. Kostenmodel

Aannames (te vervangen door de meting uit de eerste stap): 3.700 orders/jaar, 0,4–0,6 contacten per order → 1.500–2.200 klantvragen/jaar → 125–185 per maand, plus site-interacties (schatting 5–10× dat aantal, kort en goedkoop).

**Modelkosten** (prijzen september 2026, zie `research/B2`; Anthropic direct gelezen, OpenAI/Google via excerpten):

| Werk | Model-klasse | Tokens/interactie | Kost/interactie | Per maand (2.000 site + 200 support + 200 Copilot) |
|---|---|---|---|---|
| Intent-routing, feitvragen | klein (Haiku 4.5 $1/$5; GPT-5 mini $0,25/$2) | ±2k | €0,002–0,005 | €5–10 |
| Adviesantwoord met werkbank | midden (Sonnet 5 $2/$10; GPT-5 $1,25/$10) | ±6k | €0,02–0,04 | €10–20 |
| Copilot-dossier + concept | midden | ±8k | €0,03–0,06 | €6–12 |
| Evaluatie-runs (wekelijks, 1.000 cases) | klein/midden | ±4k | – | €10–20 |
| Embeddings (policy, FAQ, historiek) | text-embedding-3-small $0,02/M | – | – | < €1 |
| STT push-to-talk (later) | ≈ €0,005/min | – | – | €5–15 |
| **Totaal modelkosten** | | | | **€35–80/maand** |

Ter vergelijking: per-resolutie-SaaS (Fin $0,99/resolutie met 50/maand minimum; Gorgias ±$1 + ticket; Zendesk $1,50–2 + seats) kost bij dit volume $100–400/maand en biedt geen werkbank, geen Fact Brain en geen Copilot op Masters data. Tidio Growth + Lyro (±$92/maand) is de enige SaaS-optie in dezelfde prijsklasse en heeft geen toegang tot Master.

**Infrastructuur**: één extra Railway-service met Postgres: €10–25/maand. Gmail-API: gratis. Shopify-app: gratis. Rive: gratis runtime; eenmalig ontwerp van het karakter (illustrator, 2–4 dagen).

**Bouwkosten** (indicatief, in dagen, uitgaand van Claude Code-sessies plus Mathias' reviewtijd): V1 25–35 dagen; V2 15–25; V3 15–20; V4 10–15. De grootste kost is niet code maar **data**: policy-store vullen (2 dagen), levertijdregel (1 dag + verificatie), Fact-backfill (pijplijn bestaat; 3–5 dagen doorlooptijd), evaluatieset labelen (2 dagen Mathias), adviesregels uit mails (3–5 dagen samen).

## 32. KPI's

Alle KPI's met een baseline uit de meetperiode (sectie 40). Geen KPI mag de AI richting bluffen of pushen sturen; daarom staan naast elke efficiëntie-KPI een kwaliteits-KPI.

**Operationeel**
- % vragen autonoom afgehandeld · % assisted · % human (doel na 6 maanden: 45 / 35 / 20; na 12 maanden: 60 / 25 / 15).
- Mathias-minuten per dag aan klantenservice (baseline meten; doel −60 % na 6 maanden).
- First response time (doel < 15 min kantooruren, < 1 min voor autonome antwoorden, 24/7).
- Resolution time per categorie.
- % concept-antwoorden ongewijzigd goedgekeurd (doel > 80 % na 3 maanden).

**Kwaliteit en veiligheid**
- Feitelijk foutpercentage (steekproef 50/week door Mathias; doel < 1 %).
- Hallucinaties (doel 0 in productie; elk geval = incident + eval-case).
- Verkeerde escalaties (had autonoom gekund) en gemiste escalaties (had eerder gemoeten) · doel beide < 5 %.
- Policy-correctheid (doel 100 % op beleidsvragen; afwijking = incident).
- Klanttevredenheid: duim omhoog/omlaag per antwoord + korte CSAT na escalatie (doel ≥ 4,5/5).

**Commercieel**
- Adviesconversie: conversie van sessies met adviesinteractie versus 50/50-holdout (8 weken, minstens 3 weken na launch om nieuwigheid te laten vervallen). Geen "chatters converteren 3×" zonder holdout.
- Omzet en AOV bij AI-gebruikers versus holdout.
- Retourpercentage na AI-advies versus zonder (doel: lager of gelijk; hoger = adviesregels herzien).
- Testservice-boekingen via de assistent.

**Gebruik en kosten**
- Gebruik van de assistent (% sessies, per pagina-type, desktop/mobiel), abandonment (gesprekken zonder antwoord of afgebroken).
- Kosten per gesprek en per autonoom opgelost gesprek (doel < €0,05 en < €0,10).
- Performance-impact: LCP/INP/CLS-delta op productpagina's (doel: 0).
- Wekelijks: "top ontbrekende informatie op de site" (lijst, geen getal).
## 33. Fast Track V1: snel tijd terug, zonder spektakel

**Doel.** Binnen 6 tot 8 weken meetbaar minder klantenservice voor Mathias, met een architectuur die de eindvisie draagt. Geen avatar, geen werkbank-UI, wel het brein, de adapters en de Copilot.

**Scope V1**

| Onderdeel | Wat precies | Autonomie |
|---|---|---|
| **Brein-service** | Railway-service met Postgres; intent-router; tool-loop naar Willie-patroon; autonomiepoort; audit; AI-wrapper met kosten | – |
| **Adapters (read-only)** | Shopify orders/fulfilments/klant (eigen app, min. scopes); Master `/api/klant/*` (prijs/VIP, beschikbaarheid per variant, locatie, Tienda-stand, zoeken, testracket); tracking-service `GET /api/order/{ORD}` (nieuw, read-only); factuurstatus (onFact-check via dagontvangsten-index of factuurmotor-DB); Gmail-threads | – |
| **Policy-store** | retour, garantie per merk, verzending per land (tarieven, drempels, cut-off), afhalen Mechelen, testservice, betaalmethoden, herroeping; drie talen; geversioneerd; letterlijk citeerbaar | – |
| **Levertijdregel** | locatie (BE eigen / ES dropship) × land × cut-off → belofte in dagen + bron; bij onbekend: geen belofte | – |
| **Mathias Copilot** | Master-zone `/copilot`: dossier per ORD, geplakte mail → concept, wachtrij (assisted/human/escalaties), APPROVE·EDIT·TAKE OVER met verzending via Gmail, weekoverzicht terugkerende vragen en ontbrekende info | S/H, mens verstuurt |
| **Site-basis (Richting B, deel 1)** | leveringsregel onder de prijs (server-side uit metafields + levertijdregel), contextchips per paginatype, inline antwoordkaart voor: levertijd, voorraad per maat, verzendkosten, afhalen, testservice, orderstatus (ordernummer + e-mail), tracking-link, FAQ; AI-label op elk antwoord | A (feiten en beleid), rest → "ik leg dit voor aan Mathias" |
| **Eenvoudige vergelijking** | deterministische DeltaCard op basis van bestaande `custom.*`-specs (gelabeld "onbevestigd" waar geen bron), zonder LLM-interpretatie | A |
| **Evaluatieset v1** | 200 gepseudonimiseerde cases + adversariële set; run als deploy-poort | – |
| **Kill switch en monitoring** | rem vrij/pauze/stop; dagelijkse mail met cijfers en incidenten | – |

**Bewust buiten V1**: persoonlijk racketadvies autonoom (wel assisted via Copilot), retourlabel automatisch aanmaken, adreswijziging, WhatsApp-kanaal, karakter/avatar, werkbank-UI, voice, Tidio-vervanging (Tidio blijft; Copilot leest de export/mails).

**Volgorde binnen V1 (weken)**
1–2: meting en labeling (zie 40), policy-store vullen, levertijdregel vastleggen, Shopify-app met scopes, Master `/api/klant/*`.
3–4: brein-service, adapters, Copilot-dossier per ORD, evaluatieset, eerste eval-run.
5–6: Copilot-wachtrij met Gmail, concept-antwoorden, EDIT-logging; site: leveringsregel en contextchips server-side.
7–8: inline antwoordkaarten (feiten, beleid, orderstatus), CWV-meting, adversariële tests, GO-review per intentie, soft launch op 20 % van de sessies.

**Definitie van klaar**: Copilot in dagelijks gebruik; ≥ 70 % van de concepten ongewijzigd goedgekeurd op de assisted-intenties; nul hallucinaties in de steekproef; CWV-delta 0; eval-run groen.

## 34. Verdere fases

**V2 · De zichtbare medewerker en de werkbank (8–10 weken na V1).**
Gestileerd PadeLMQ-karakter (2D, Rive, states idle/luisteren/denken/antwoorden, AI ASSISTENT-shirt), zijpaneel/bottom sheet, werkbank met max 3 producten en relevante schuiven, "vergelijk met mijn huidige racket" met anker en referentietabel, modeljaar-tijdlijn, Advice Brain v1 (delta-regels, spelerregels, Mathias-methode uit mails), Fact-backfill van de racketcatalogus via de Product Engine, persoonlijk advies naar Autonomous per subintentie op basis van eval en vier weken assisted. A/B: karakter vs plain (zelfde backend), ≥ 3 weken.

**V3 · Servicebalie en acties (6–8 weken).**
Ordertijdlijn per regel in het account, retourwizard met label (retourapp of Shopify Returns), omruil met reservering, adreswijziging op unfulfilled orders, proactieve split-shipment-mail, factuur-intake met VIES, "mijn padeltas" met testset-boeking (Bancontact), Tienda-ref-herkenning. Tracking-service live (of Shopify-fulfilments als bron) is randvoorwaarde.

**V4 · Kanalen, voice en per-stuk-data (doorlopend).**
E-mail volledig via de Copilot (Tidio uitfaseren of als kanaal koppelen), WhatsApp Business API, push-to-talk in de sheet, weegbank per stuk voor eigen voorraad (wegen bij ontvangst + metafield), schoenmaat-signalen uit retourredenen, opgenomen video van Mathias op categoriepagina's, sociaal bewijs bij n ≥ 20.

**Wat het onderzoek als betere volgorde suggereert**: niet "brein → medewerker → werkbank → omgeving" maar "Copilot + contextuele feiten → werkbank met anker (de innovatie) → servicebalie met acties → karakter als laag erbovenop". Het karakter komt in V2 alleen omdat het goedkoop is als het gestileerd blijft; het is nooit de reden van een fase.

## 35. Technische risico's

| Risico | Kans | Impact | Mitigatie |
|---|---|---|---|
| Tracking-service blijft in dry-run; geen betrouwbare tracking per order | hoog | hoog voor Flow 3 | V1 leest Shopify-fulfilments (door de lokale tool geschreven) als primaire bron; TR alleen als verrijking; live-overgang als aparte beslissing |
| `read_orders`-scope onduidelijk; `read_all_orders` ontbreekt (60 dagen) | midden | midden | Eigen Shopify-app voor het brein met expliciete scopes; oude orders via `fetch_orders_by_name` per ordernummer (werkt buiten 60 dagen, bewezen in dagontvangsten) |
| Specs voor bestaande catalogus zonder bron | hoog | hoog voor advies | V1 labelt legacy-specs "onbevestigd"; V2 backfill via Engine-pijplijn; ontbrekend = schuif niet tonen |
| Levertijdregel bestaat nergens; belofte in thema | hoog | hoog | Regel expliciet vastleggen met Mathias (1 dag), thema en brein lezen dezelfde bron |
| Masters SQLite/lussen belasten door extra reads | laag | midden | Dun endpoint met cache; alleen bestaande read-functies; rate-limit; nooit `getDb()` vanuit een tweede proces |
| Prompt-injection, guardrail-regressie na update | midden | hoog | Adversariële set in de poort; geen bevoegdheid tot toezeggingen; kill switch; label AI |
| Model-/prijsveranderingen bij leveranciers | hoog | laag | Provider-agnostische wrapper; eval-run beslist; twee providers geconfigureerd |
| CWV-schade op productpagina's | midden | hoog | Façade < 20 kB, lazy load, server-side Liquid voor basis; meting in de poort |
| Meertaligheid (nl/fr/en) kwaliteit | midden | midden | Beleid in drie talen in de store; eval-cases per taal; Shopify Magic (Engels-only) niet gebruiken |
| Eén persoon (Mathias) is bottleneck voor labels en GO's | hoog | midden | Labelen in kleine dagelijkse batches in de Copilot; GO per intentie, niet per antwoord |

## 36. Commerciële risico's

- **Verkeerd advies kost een klant en een retour.** Mitigatie: advies assisted tot bewezen; afraden toestaan; retourpercentage na advies als KPI; "test eerst" als natuurlijke afloop bij twijfel.
- **AI-label verlaagt vertrouwen (Luo-effect).** Mitigatie: het label koppelen aan kwaliteit ("antwoorden uit onze systemen, live"), bronlabels tonen, Mathias-video voor het menselijke gezicht, escalatie altijd zichtbaar.
- **Cannibalisatie van het persoonlijke contact dat PadeLMQ onderscheidt.** Mitigatie: de Copilot maakt Mathias sneller en consistenter zonder hem te vervangen op de momenten die tellen (schade, garantie, uitzonderingen); Klarna-les expliciet in het plan.
- **KPI-druk richting pushen.** Mitigatie: geen omzet-KPI zonder retour- en tevredenheids-KPI ernaast; "afraden" als geteld gedrag.
- **Aansprakelijkheid voor foute claims (Air Canada).** Mitigatie: beleid letterlijk, feiten uit bron, "onbekend" toegestaan, audit per antwoord.
- **Tienda/ICP-afhankelijkheid**: beloftes over dropship-levering die PadeLMQ niet controleert. Mitigatie: levertijd als bereik met bron, nooit als garantie; proactieve communicatie bij afwijking.
- **Mechelen-verwarring** (twee winkels, twee sites, twee ordernummerformaten). Mitigatie: winkelcontext expliciet in elk antwoord; Mechelen-vragen naar het Mechelen-blok (zelfservice, geen verzending).

## 37. UX-risico's

- **Irritatie door aanwezigheid**: nooit auto-open, nooit proactief pop-up, karakter stil in idle, onthoud "gesloten" per sessie.
- **Uncanny valley**: gestileerd, niet-fotorealistisch, geen lipsync; A/B-test ≥ 3 weken.
- **Verwachting van een mens**: label, naam "AI Adviseur", toon warm maar nooit "ik" als Mathias.
- **Lege werkbank** (specs ontbreken): schuif niet tonen, zeg wat ontbreekt.
- **Te veel vragen**: regel "alleen vragen wat onzekerheid materieel vermindert" als eval-dimensie ("onnodige vragen").
- **Mobiel bedekt de winkel**: drie toestanden, geen permanente overlay, Playwright-mobieltests.
- **Taalwissel**: antwoord in de taal van de klant, ook bij Frans op een Nederlandse pagina.
- **Escalatie voelt als afwijzing**: formuleer als voordeel ("Mathias kijkt er persoonlijk naar"), met termijn.

## 38. Wat we expliciet NIET bouwen

1. **Een fotorealistische of video-avatar** (HeyGen/D-ID/Soul Machines-klasse). Bewijs tegen, kosten per minuut, AI Act-frictie.
2. **De immersieve 3D-winkelvloer als hoofdinterface.** Hooguit later een optionele winkelmodus, nooit vóór A bewezen is.
3. **Realtime duplex voice.** Geen bewijs voor webshops; kosten, latentie, privacy. Push-to-talk volstaat.
4. **In-chat checkout / agentic checkout.** Walmart en OpenAI trokken zich terug; conversie een derde van de eigen checkout. Ontdekken in de assistent, kopen op de site.
5. **Een tweede prijs-, voorraad- of trackingsysteem.** Alles read-only via bestaande breinen.
6. **Een klantendatabase naast Shopify.** Geen kopie van klantdata; alleen gespreks- en auditlog met minimalisatie.
7. **Autonome geldacties**: refunds, kortingen, prijsbeloftes, garantiebeslissingen, annuleringen.
8. **Een verplichte quiz/racketwizard.** Anker-first, vragen alleen bij materiële onzekerheid.
9. **"Mathias" als AI-persona.** Het is de PadeLMQ AI Adviseur, ontwikkeld volgens zijn methode.
10. **Gedragstracking buiten de sessie zonder toestemming**, en creepy formuleringen.
11. **Een per-resolutie-SaaS als kern** (Fin, Gorgias, Zendesk). Te duur voor dit volume en zonder toegang tot Master; hooguit Tidio als tijdelijk kanaal.
12. **Scores als schoolrapport.** Radar-getallen alleen optioneel en met bronlabel; Racket DNA blijft een karakterprofiel.
13. **Willie ombouwen tot klantassistent.** Willie blijft de pricing-collega; alleen zijn patroon wordt hergebruikt.
14. **Lussen of tabellen toevoegen aan Master voor dit project.** Alleen een dun read-only endpoint.

## 39. Open beslissingen voor Mathias

1. **Naam en positionering**: "PadeLMQ AI Adviseur" (advies-eerst) of "PadeLMQ AI Assistent" (service-eerst)? Ondertitel "ontwikkeld volgens de adviesmethode van PadeLMQ/Mathias" ja/nee? (Voorstel: Adviseur op de site, Servicebalie in het account, Copilot intern.)
2. **Karakter**: gestileerd 2D-karakter met AI ASSISTENT-shirt (V2), of alleen een merkteken zonder figuur? Fictieve figuur of geïllustreerde versie van Mathias? (Voorstel: fictief, gestileerd; Mathias in echte video.)
3. **Tidio**: vervangen door de eigen assistent (V4), behouden als kanaal dat de Copilot leest, of behouden zoals nu naast de nieuwe site-laag? (Bepaalt ook de Tidio-export voor de evaluatieset.)
4. **Levertijdregel**: de exacte beloftes per locatie × land × cut-off, en of "morgen in huis" ooit autonoom mag worden gezegd. (Zonder deze regel geen leveringsantwoorden.)
5. **Retourbeleid als bron**: wie schrijft de machineleesbare versie (termijn, uitzonderingen, gebruikt, hygiëne, wie betaalt), in drie talen? En mag de AI in V3 zelf een retourlabel maken binnen beleid?
6. **Persoonlijk racketadvies**: in V1 alleen assisted (Copilot) of ook autonoom voor deterministische vergelijkingen (DeltaCard zonder interpretatie)? (Voorstel: het laatste.)
7. **Weegbank**: gaan we eigen voorraad (Kampenhout/ShopWeDo) per stuk wegen en registreren? Dat is een operationele keuze met grote klantwaarde.
8. **Modelleverancier**: OpenAI (zoals Master), Anthropic (zoals de Engine-extractie), of beide via de wrapper met eval als scheidsrechter? (Voorstel: beide, eval beslist per taak.)
9. **Toestemmingsmodel**: sessiecontext onder welke cookie-categorie; anker onthouden lokaal of in account.
10. **Tracking-service**: wanneer live (`TRACKING_LIVE_WRITES=true`) en wie beslist dat; tot dan is Shopify-fulfilment de bron.
11. **Wie verstuurt**: Copilot-antwoorden gaan als Mathias via Gmail (met of zonder "opgesteld met AI-hulp"), of als "PadeLMQ Service"?
12. **Budget en tempo**: V1 in 6–8 weken met Mathias' labeltijd (±2 dagen) en dagelijkse review (15 min), ja/nee?

## 40. Concrete volgende stap

Geen code. Vier weken, vier sporen, parallel:

1. **Meten (week 1–4).** Elke inkomende klantvraag (Tidio, mail, WhatsApp, telefoon) één regel in een sheet: datum, kanaal, taal, intentie (uit de matrix), minuten, systemen geopend, autonomieniveau dat had gekund. Dit vervangt alle aannames in dit plan en levert de baseline voor elke KPI.
2. **Labelen (week 1–3).** Tidio- en Gmail-export naar een afgeschermde map; pseudonimiseringsscript; 200 cases labelen met Mathias' gouden antwoord. Dit is de evaluatieset v1 en tegelijk de bron voor de adviesmethode.
3. **Bronnen vastleggen (week 1–2).** Met Mathias in twee sessies: de levertijdregel (locatie × land × cut-off), het retour-/garantie-/verzendbeleid in machineleesbare vorm, drie talen. Plus verificatie van de Shopify-scopes van Master en de Product Engine-dekking van de racketcatalogus.
4. **Beslissen (week 2).** De twaalf open beslissingen hierboven, in één gesprek, gelogd.

Daarna: GO voor Fast Track V1 zoals in sectie 33, te beginnen met de Copilot.

---

*Dit masterplan is opgesteld op basis van de code in zes PadeLMQ-repo's (stand 28 september 2026), drie onderzoeksmemo's met bronvermelding, en de eerdere blueprint. Cijfers over klantenservicevolume zijn aannames tot de meting van stap 1 klaar is. Alle schetsen zijn conceptueel; namen, orders en prijzen erin zijn voorbeelden.*
