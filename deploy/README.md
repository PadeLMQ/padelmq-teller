# De orkestrator 24/7 draaien

## Waarom systemd op de bestaande VPS

Niet omdat het het modernste is, maar omdat het het minste toevoegt.

De orkestrator is een Python-proces dat een SQLite-bestand, een kennisbasis en
git-worktrees op schijf bijhoudt, en dat de `claude`-CLI als subproces start.
Dat zijn precies de dingen waar containerplatforms als Railway lastig over doen:
een schrijfbare schijf die een herstart overleeft vraagt daar een apart volume,
en een CLI die zelf processen start en git-repositories beheert past slecht in
een read-only image.

Op een VPS die er al staat is dit één unitbestand. Geen extra rekening, geen
tweede plek waar geheimen wonen, geen nieuw begrip om te onderhouden. `systemd`
doet het herstarten, het opkomen na een reboot en het loggen, en dat doet het
beter dan wat wij zouden bouwen.

Railway of Fly zijn zinnig als er ooit een webdienst bijkomt die van buiten
bereikbaar moet zijn. Dat is hier niet zo: de orkestrator praat naar buiten,
niemand praat naar binnen.

## Wat er komt te staan

```
/opt/orchestrator/repo        de code (git checkout)
/opt/orchestrator/werk        git-worktrees per taak
/var/lib/orchestrator/data    SQLite, kennisbasis, audittrail, kosten
/etc/orchestrator/env         geheimen, 640 root:orchestrator
```

De data staan **buiten** de repository. Dat is geen netheid maar een harde
regel: de kennisbasis bevat businessregels en die horen nooit in git.

## Installeren

```bash
git clone https://github.com/PadeLMQ/padelmq-teller.git
sudo ./padelmq-teller/deploy/installeer.sh
```

Het script maakt de gebruiker, de mappen en de units, en **draait de testsuite
voordat er iets gaat draaien**. Falen de tests, dan stopt de installatie.

Daarna:

1. vul `/etc/orchestrator/env` in
2. `orchestrator doctor` — die controleert of authenticatie werkelijk werkt,
   niet of er een variabele bestaat
3. `systemctl enable --now orchestrator`

## Bewijzen dat het draait

```bash
orchestrator status          # exit 0 = levensteken vers genoeg
systemctl status orchestrator
journalctl -u orchestrator -f
```

`status` leest het levensteken dat de lus na **elke** ronde schrijft, ook een
stille. Dat is met opzet: zonder een teken bij stilte is een rustige dienst niet
te onderscheiden van een dode.

De timer `orchestrator-status.timer` controleert dat elk kwartier. Blijft het
levensteken uit, dan komt de unit in `systemctl --failed` te staan — zichtbaar
zonder dat er iets extra's voor draait.

## Terugrollen

```bash
sudo /opt/orchestrator/repo/deploy/terugrollen.sh
```

Zet de code terug naar de versie van vóór de laatste installatie. De data
blijven staan: taken, kennis, audittrail en kosten gaan niet mee terug.

## Wat er NIET verandert door 24/7 te draaien

Alle grenzen blijven staan, want ze zitten in de code en niet in de manier van
starten: geen automatische merge naar `main`, geen deploy, geen live
Shopify-, prijs- of voorraadactie, budgetremmen vóór elke betaalde aanroep,
BLOCK bij ontbrekende businessregels, en strikte scheiding tussen projecten.

Een lus die vaker draait mag niet méér mogen.

## Back-up

Alles wat ertoe doet staat in `/var/lib/orchestrator`. Een dagelijkse kopie
daarvan is de volledige back-up:

```bash
sqlite3 /var/lib/orchestrator/data/orchestrator.sqlite3 ".backup /pad/naar/backup.sqlite3"
tar czf /pad/naar/kennis.tar.gz -C /var/lib/orchestrator/data projects
```

Let op: die kopie bevat businessregels en hoort dus dezelfde bescherming te
krijgen als het origineel.
