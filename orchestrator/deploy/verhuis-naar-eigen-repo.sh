#!/usr/bin/env bash
#
# Haalt de orkestrator uit padelmq-teller en zet hem klaar voor een eigen
# PRIVATE repository, met behoud van de geschiedenis van deze map.
#
# Draait standaard als PROEF: er wordt niets gepusht. Lees de uitvoer, en voeg
# daarna --push toe met de URL van de nieuwe repo.
#
# Gebruik:
#   ./deploy/verhuis-naar-eigen-repo.sh
#   ./deploy/verhuis-naar-eigen-repo.sh --push git@github.com:PadeLMQ/padelmq-orchestrator.git
#
set -euo pipefail

PREFIX="orchestrator"
BRANCH="orchestrator-split"
PUSH_URL=""

if [[ "${1:-}" == "--push" ]]; then
    PUSH_URL="${2:?geef de URL van de nieuwe private repository}"
fi

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

echo "== 1. Controle op geheimen in de map die verhuist =================="
python3 - "$ROOT/$PREFIX" <<'PY'
import sys
from pathlib import Path
root = Path(sys.argv[1])
sys.path.insert(0, str(root))
from orchestrator.secret_scan import format_hits, scan_tree
hits = scan_tree(root)
print(format_hits(hits))
if hits:
    raise SystemExit("GESTOPT: er staan mogelijke geheimen in de map die verhuist.")
PY

echo
echo "== 2. Geschiedenis van $PREFIX/ afsplitsen ========================="
git branch -D "$BRANCH" 2>/dev/null || true
git subtree split --prefix="$PREFIX" -b "$BRANCH"
echo "Branch '$BRANCH' bevat nu alleen de geschiedenis van $PREFIX/."
echo "Commits: $(git rev-list --count "$BRANCH")"

echo
echo "== 3. Controle: staat er geen enkel bestand van buiten $PREFIX in? =="
BUITEN="$(git ls-tree -r --name-only "$BRANCH" | grep -c '^index.html\|^update_teller.py\|^docs/' || true)"
if [[ "$BUITEN" != "0" ]]; then
    echo "GESTOPT: de afgesplitste branch bevat bestanden van buiten $PREFIX/." >&2
    exit 1
fi
echo "In orde: alleen bestanden uit $PREFIX/."

if [[ -z "$PUSH_URL" ]]; then
    echo
    echo "== PROEF afgerond. Er is niets gepusht. ==========================="
    echo
    echo "Volgende stap, nadat je de PRIVATE repository hebt aangemaakt:"
    echo "  ./deploy/verhuis-naar-eigen-repo.sh --push <git-url>"
    echo
    echo "Daarna, in de nieuwe repo:"
    echo "  ln -sf ../../deploy/pre-commit .git/hooks/pre-commit"
    echo "En in padelmq-teller: verwijder $PREFIX/ in een aparte commit."
    exit 0
fi

echo
echo "== 4. Pushen naar $PUSH_URL ======================================="
git push "$PUSH_URL" "$BRANCH:main"
echo "Klaar. De orkestrator staat nu in zijn eigen repository."
echo
echo "Nog te doen, met de hand:"
echo "  - controleer dat de nieuwe repository PRIVATE is;"
echo "  - installeer de pre-commit hook in de nieuwe kloon;"
echo "  - verwijder $PREFIX/ uit padelmq-teller in een aparte commit."
