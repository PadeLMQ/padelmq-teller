#!/usr/bin/env bash
# Zet de vorige versie terug. De data blijven staan: alleen de code gaat terug.
set -euo pipefail
BASIS=/opt/orchestrator
[ -f "$BASIS/vorige-versie" ] || { echo "geen vorige versie bekend"; exit 1; }
VORIGE=$(cat "$BASIS/vorige-versie")
echo "terug naar $VORIGE"
systemctl stop orchestrator
sudo -u orchestrator git -C "$BASIS/repo" checkout --quiet "$VORIGE"
sudo -u orchestrator bash -c "cd '$BASIS/repo/orchestrator' && python3 -m unittest discover -s tests -q" \
  || echo "let op: de tests van de vorige versie falen ook"
systemctl start orchestrator
systemctl status orchestrator --no-pager | head -5
