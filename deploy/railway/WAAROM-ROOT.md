# Waarom `railway.json` in de repo-root staat

Railway leest zijn configuratie uit de **root** van de repository. Een
`railway.json` in een submap wordt genegeerd; hij ziet hem niet.

Dat ging hier mis. `padelmq-teller` is ook de website-repo: er staat een
`index.html` en een `CNAME`. Zonder configuratie in de root deed Railway wat het
in dat geval doet — de repo zelf onderzoeken, een statische site herkennen, en
die met Caddy uitrollen. De deploy slaagde, de service kwam Online, en de
orkestrator werd nooit gestart. In de logs stond daarom alleen
`Starting Container` en verder niets: er wás niets anders om te loggen.

De root-`railway.json` wijst nu expliciet naar `deploy/railway/Dockerfile`. De
kopie in deze map blijft staan als documentatie van wat die service doet, maar
de root is wat telt.

GitHub Pages trekt zich van `railway.json` niets aan, dus de website blijft
gewoon werken.

## En waarom er nu opstartlogging is

De fout was gevonden, maar de reden dat hij zo lang onzichtbaar bleef niet. Een
service die "Active" heet en zwijgt, is niet te onderscheiden van een service
die werkt en niets te doen heeft. Daarom draait `start.sh` nu eerst
`orchestrator startup`. Dat commando zegt per onderdeel `OK` of `FOUT`:

    [OK  ] datamap      /data/orchestrator beschrijfbaar; blijft behouden (vorige start ...)
    [OK  ] github-auth  geauthenticeerd als PadeLMQ, repo's: ...
    [OK  ] openai       OK via credential-proxy (... modellen zichtbaar, gratis eindpunt)
    [OK  ] claude-cli   /usr/bin/claude: 2.1.261 (Claude Code)
    [OK  ] doctor       alle controles geslaagd
    [OK  ] opstart      alle noodzakelijke controles geslaagd
    [OK  ] serve        gestart voor ...; ronde elke 120s bij stilte

Elke controle bewijst het hele pad in plaats van te kijken of een variabele
bestaat: `github-auth` vraagt wie we zijn, `openai` haalt de modellenlijst op
(gratis, geen tokens), `claude-cli` roept de CLI werkelijk aan. Sleutels komen
er nooit in voor; foutmeldingen van leveranciers gaan door de redactie heen.

De datamap-controle laat bij elke start een merkteken achter en meldt of dat
van een vorige start er al stond. Zo wordt een volume dat niets bewaart bij de
tweede start zichtbaar, in plaats van pas wanneer je een taak kwijt bent.

Faalt een noodzakelijke controle, dan stopt `start.sh` met exitcode 1. Railway
herstart dan (maximaal tien keer), en in de log staat een regel met `FOUT` en de
reden. Dat is met opzet luidruchtiger dan doorstarten en later stilvallen.

Daarna print `serve` elke ronde een `[HART]`-regel, ook als er niets gebeurde:

    [HART] ronde 12 2026-09-05T23:07:32+00:00 stil; hersteld=0 ... ; volgende over 120s

Juist die stille regels maken het verschil tussen "niets te doen" en "dood".

## En waarom "Completed" ook fout was

Na de eerste fix bouwde en startte de container wel, maar meldde Railway de
service als **Completed** in plaats van Online. De oorzaak lag een laag dieper
en was dezelfde soort fout.

Projectconfiguratie staat op het volume, onder `/data/orchestrator/projects`.
Een vers volume is leeg, en er was geen weg om er projecten op te krijgen
behalve met de hand `orchestrator project add` draaien — waarvoor je een shell
nodig hebt die er niet is. Dus: nul projecten, `serve` had niets te doen, en
sloot af met code 0. Exitcode 0 leest als succes. Groen, en niets draait.

Twee dingen zijn daarop veranderd.

**Nul projecten is nu luidruchtig fout.** Het opstartrapport heeft een regel
`projecten` erbij, en `serve` stopt met exitcode 1 in plaats van 0. Een lus
zonder projecten is een verkeerd geconfigureerde dienst, geen rustige dienst.

**Projecten kunnen uit de omgeving komen.** `start.sh` draait
`orchestrator project ensure`, dat `ORCH_PROJECTS` leest: JSON met een lijst
projecten. Bijvoorbeeld:

    [{"slug":"orchestrator-zelf",
      "github_repo":"PadeLMQ/padelmq-teller",
      "default_branch":"main",
      "checks":{"tests":"python3 -m unittest discover -s orchestrator/tests -t orchestrator"}}]

Staat `repo` er niet in, dan komt de kloon onder `ORCH_REPOS` op het volume te
staan. Een project dat al op het volume staat wordt **nooit** overschreven: het
volume is de waarheid zodra het bestaat, anders zou een oude variabele later
stilletjes wijzigingen terugdraaien. Wat er niet in staat wordt niet geraden —
een project zonder `slug` is een fout met een leesbare melding.

Omdat hiermee een nieuwe weg ontstaat waarlangs verificatiecommando's
binnenkomen, is de veiligheidspoort in `verify.py` uitgebreid. Die weigerde al
bedrijfsacties (sync, import, deploy, Shopify-schrijfacties); nu ook
destructieve shell: verwijderen, `sudo`, `git push`, geschiedenis herschrijven,
en ingrijpen op schijf of machine. Een verificatiecommando hoort te draaien en
een exitcode terug te geven, meer niet.
