#!/usr/bin/env bash
# Start de orkestrator, maar pas nadat is vastgesteld dat hij kán werken.
# Een dienst die opkomt en dan stilletjes niets doet is erger dan een dienst
# die weigert te starten: het eerste merk je pas als je iets verwacht.
set -euo pipefail

echo "== orkestrator start =="
mkdir -p "${ORCH_DATA_DIR:-/data/orchestrator}" "${ORCH_REPOS:-/data/repos}"

# Git kan zonder identiteit niet committen.
git config --global user.name  "${ORCH_GIT_NAME:-orchestrator}"
git config --global user.email "${ORCH_GIT_EMAIL:-bot@padelmq.be}"
git config --global --add safe.directory '*'

# Pushen gebeurt over HTTPS met de token. Die staat in een bestand met rechten
# 600 en nooit in een remote-URL: een URL belandt in logs en in .git/config.
if [ -n "${ORCH_GITHUB_TOKEN:-}" ]; then
  printf 'https://x-access-token:%s@github.com\n' "$ORCH_GITHUB_TOKEN" > /root/.git-credentials
  chmod 600 /root/.git-credentials
  git config --global credential.helper store
  echo "   git-authenticatie ingesteld (token niet getoond)"
else
  echo "   LET OP: ORCH_GITHUB_TOKEN ontbreekt; pushen en PR's openen gaat niet werken"
fi

# doctor toetst of authenticatie werkelijk werkt, niet of er een variabele
# bestaat. Faalt hij, dan stoppen we hier: Railway herstart en probeert opnieuw,
# en de fout staat in de log in plaats van dat er stil niets gebeurt.
# De klonen van de projecten staan op het volume, maar na een herstart kan er
# een ontbreken of achterlopen. Dit haalt ze terug zonder bestaande worktrees
# weg te gooien.
echo "== repositories =="
python3 -m orchestrator.cli project bootstrap || echo "   let op: niet elke repository is beschikbaar"

# Eén rapport met OK/FOUT per onderdeel: datamap, github-auth, openai,
# claude-cli en doctor. Faalt er iets, dan stopt het hier met een regel die
# zegt wát er mis is. Railway herstart dan; wat je niet krijgt is een dienst
# die "Active" heet en zwijgt.
echo "== controle vooraf =="
python3 -m orchestrator.cli startup

echo "== draaien =="
exec python3 -m orchestrator.cli serve --interval "${ORCH_INTERVAL:-120}"
