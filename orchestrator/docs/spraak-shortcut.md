# De vraag hardop, het antwoord ingesproken

Handleiding voor de Apple Shortcut die BLOCK-vragen voorleest en je gesproken
antwoord terugstuurt. Werkt handsfree met AirPods via "Hey Siri".

## Wat je nodig hebt

1. Het spraakeindpunt draait en is bereikbaar over **https**:

   ```bash
   openssl rand -hex 24          # het token; zet dit in .env als ORCH_VOICE_TOKEN
   orchestrator voice-serve      # luistert standaard op 127.0.0.1:8765
   ```

   Zet er op de VPS een reverse proxy met TLS voor. Stuur dit token **nooit**
   over http: wie het heeft, kan beslissingen namens jou vastleggen.

2. De twee handelingen die de Shortcut gebruikt:

   | | |
   |---|---|
   | `GET /voice/next` | geeft `{sessie, project, taak, spreek, opties}` of `{"vraag": null}` |
   | `POST /voice/answer` | verwacht `{sessie, transcript, zekerheid?}`, geeft `{spreek, klaar, vastgelegd}` |

   Beide met de kop `X-Orch-Token: <jouw token>`.

## De Shortcut

Maak in de app Opdrachten een nieuwe opdracht, bijvoorbeeld **"Wat staat er open"**.

1. **Inhoud van URL ophalen**
   URL `https://<jouw-domein>/voice/next` · Methode `GET`
   Koptekst `X-Orch-Token` = je token
2. **Woordenlijstwaarde ophalen** — sleutel `spreek`
3. **Tekst uitspreken** — die waarde
4. **Als** `vraag` gelijk is aan niets → *Stop opdracht* (er staat niets open)
5. **Tekst dicteren** — dit is je antwoord
6. **Inhoud van URL ophalen**
   URL `https://<jouw-domein>/voice/answer` · Methode `POST` · Aanvraagtype JSON
   Koptekst `X-Orch-Token` = je token
   Body: `sessie` = de `sessie` uit stap 1, `transcript` = de gedicteerde tekst
7. **Woordenlijstwaarde ophalen** — sleutel `spreek` → **Tekst uitspreken**
8. **Als** `klaar` onwaar is → herhaal vanaf stap 5

Stap 8 is de verduidelijkings- en bevestigingslus. Meer dan één verduidelijking
komt er niet: daarna zegt het systeem zelf dat de blokkade blijft staan.

## Wat je moet weten voor je erop vertrouwt

**Dicteren geeft geen zekerheidsscore.** De Shortcut-actie *Tekst dicteren*
levert alleen tekst, geen betrouwbaarheidscijfer. De controle op "slecht
verstaan" valt daardoor weg, en de poort leunt zwaarder op de bevestigingsstap:
je hoort altijd terug wat er vastgelegd gaat worden voordat het gebeurt.

Wil je die controle wél, stuur dan `zekerheid` mee vanuit een transport dat hem
kent — een spraakbericht dat serverzijdig getranscribeerd wordt, bijvoorbeeld.

**Er wordt nooit iets aangevuld.** Verstaat het systeem je antwoord niet
eenduidig, dan vraagt het één keer door en houdt daarna de blokkade. Zeg je
"weet ik niet" of "later", dan stopt het meteen zonder door te vragen.

**Alleen blokkades worden voorgelezen.** Geparkeerde vragen blijven in het
dagrapport; die hoef je niet in je oor.

**Geheimen worden niet uitgesproken.** De vraagtekst gaat door dezelfde redactie
als alles wat de machine verlaat.

## Alternatief: een spraakbericht

Wie liever niet met Shortcuts werkt, kan hetzelfde eindpunt vanuit een bot
aanroepen: spraakbericht → transcriptie (mét zekerheid) → `POST /voice/answer`.
Minder handsfree, maar de volledige poort blijft werken. Het eindpunt maakt geen
onderscheid tussen kanalen; het audit spoor legt vast welk kanaal het was.
