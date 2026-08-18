# PadeLMQ omzetteller live zetten op GitHub Pages — uitvoeringsinstructies

Doel: de **volledige** PadeLMQ-teller ("Road to €1.000.000", één zelfstandig `index.html`
met alle features: voortgangsbalk, aftelklok, Tienda-balken, wist-je-datjes, de
"Employee of the Month"-galerij van Willie, enz.) publiek en zelf-verversend zetten.
De vaste link deel je met Willie; hij ververst elk uur, zonder dat er een desktop
moet openstaan.

## Belangrijk 1 — gebruik DIT `index.html`
`index.html` in dit pakket is de volledige, afgewerkte teller. Gebruik het exact zoals
het is. Vervang het NIET door een simpelere voorbeeldpagina, anders verdwijnen alle
features (galerij, Tienda-balken, animaties, pop-up, …).

## Belangrijk 2 — GEEN nieuwe Shopify-tokens
Dit pakket hergebruikt dezelfde verbinding als de **dagontvangst-robot**: Client ID +
Client Secret worden via de **client_credentials** grant ingewisseld voor een tijdelijk
Admin API access token. Maak dus GEEN nieuwe `shpat_`-tokens aan. Gebruik de **Client ID
en Client Secret van de bestaande Dev Dashboard-apps** (exact dezelfde waarden die de
dagontvangst-robot als secrets gebruikt).

## Bestanden in dit pakket
- `index.html` — de volledige teller (zelfstandig; alle CSS/JS/afbeeldingen ingebakken).
- `update_teller.py` — haalt elk uur de omzet + het aantal orders op (client_credentials)
  en werkt in `index.html` UITSLUITEND deze CONFIG-velden bij (in het `<script>` bovenaan):
  `COMPONENTS.webshop`, `COMPONENTS.fysiek`, `PADELMQ_ORDERS` en `UPDATED`.
- `.github/workflows/update-teller.yml` — de uurtaak (GitHub Actions).

## Uitvoeren
1. Maak een nieuw **PUBLIEK** repo (bv. `padelmq-teller`). (Pages op een privé-repo
   vereist een betaald plan; een publiek repo is gratis. Secrets zijn ook in een publiek
   repo versleuteld en komen nooit in de code.)
2. Zet erin: `index.html` (root), `update_teller.py` (root), en
   `.github/workflows/update-teller.yml`.
3. Voeg 6 repo-secrets toe (Settings → Secrets and variables → Actions → New repository
   secret). Gebruik dezelfde waarden als de dagontvangst-robot:
   - `SHOP_WEBSHOP_DOMAIN`         = `c481d6-a0.myshopify.com`
   - `SHOP_WEBSHOP_CLIENT_ID`      = (Client ID van de webshop-app)
   - `SHOP_WEBSHOP_CLIENT_SECRET`  = (Client Secret van de webshop-app)
   - `SHOP_FYSIEK_DOMAIN`          = `nf41iq-yj.myshopify.com`
   - `SHOP_FYSIEK_CLIENT_ID`       = (Client ID van de fysieke-winkel-app)
   - `SHOP_FYSIEK_CLIENT_SECRET`   = (Client Secret van de fysieke-winkel-app)
   (De Client ID / Secret staan in het Dev Dashboard van elke app, óf zijn dezelfde als
   de `SHOP1_*` / `SHOP2_*`-secrets van de dagontvangst-robot.)
4. Zet GitHub Pages aan: Settings → Pages → Source: **Deploy from a branch** →
   Branch `main` / `(root)` → Save. Pages serveert dan `index.html` op een vaste URL
   (`https://<gebruiker>.github.io/padelmq-teller/`). Die link deelt Mathias met Willie.
5. Draai de workflow één keer handmatig: Actions → "Update teller" → Run workflow.
   Toon daarna de output van de run en de Pages-URL.

## Vaste (niet-Shopify) bronnen
In `index.html`, bovenaan in het `CONFIG`-object, staan `COMPONENTS.b2b` (B2B via
Lucy/onFact) en `COMPONENTS.bancontact` (Bancontact-testers) als handmatige waarden.
Het uurscript raakt ze NIET aan; werk ze met de hand bij (of laat Claude ze bijwerken)
wanneer er nieuwe cijfers zijn. Ook de Tienda-schatting (`TIENDA`) is client-side en
blijft ongemoeid.

## Regel voor het script (belangrijk)
`update_teller.py` mag in `index.html` UITSLUITEND de vier CONFIG-waarden aanpassen
(`webshop`, `fysiek`, `PADELMQ_ORDERS`, `UPDATED`). Alle andere inhoud — opmaak, teksten,
`b2b`, `bancontact`, `TIENDA`, het doelbedrag, de galerij — blijft ongewijzigd.

## Wat de teller toont als "omzet"
De som van `currentTotalPrice` (incl. btw, na refunds/annuleringen) van de betaalde
orders die dit jaar zijn aangemaakt, per winkel. Dit is een overzichts-/moraalcijfer,
niet de btw-boekhouding (dat blijft de dagontvangst-robot).

## Kanttekening
GitHub Pages is een publieke link zonder toegangscontrole. Deze teller toont het echte
omzetbedrag, dus deel de URL enkel met Willie (lange, niet te raden link, maar technisch
publiek).
