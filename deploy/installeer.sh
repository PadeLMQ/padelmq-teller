#!/usr/bin/env bash
# Installeert de orkestrator als systemd-dienst. Idempotent: opnieuw draaien
# werkt de installatie bij zonder iets weg te gooien.
#
# Gebruik:  sudo ./installeer.sh
set -euo pipefail

REPO_URL="${REPO_URL:-https://github.com/PadeLMQ/padelmq-teller.git}"
BRANCH="${BRANCH:-main}"
BASIS=/opt/orchestrator
DATA=/var/lib/orchestrator
CONF=/etc/orchestrator

echo "==> gebruiker"
id -u orchestrator >/dev/null 2>&1 || useradd --system --home "$BASIS" --shell /usr/sbin/nologin orchestrator

echo "==> mappen"
mkdir -p "$BASIS/repo" "$BASIS/werk" "$DATA/data" "$CONF"
chown -R orchestrator:orchestrator "$BASIS" "$DATA"

echo "==> code"
if [ -d "$BASIS/repo/.git" ]; then
  sudo -u orchestrator git -C "$BASIS/repo" fetch --quiet origin "$BRANCH"
  # Vorige versie onthouden, zodat terugrollen één commando is.
  sudo -u orchestrator git -C "$BASIS/repo" rev-parse HEAD > "$BASIS/vorige-versie"
  sudo -u orchestrator git -C "$BASIS/repo" checkout --quiet "origin/$BRANCH"
else
  sudo -u orchestrator git clone --quiet --branch "$BRANCH" "$REPO_URL" "$BASIS/repo"
fi

echo "==> afhankelijkheden"
python3 -m pip install --quiet --upgrade "openai>=1.0"
command -v claude >/dev/null 2>&1 || echo "   LET OP: 'claude' staat niet in PATH; de uitvoerder kan niet draaien"
command -v git    >/dev/null 2>&1 || { echo "   git ontbreekt"; exit 1; }

echo "==> configuratie"
if [ ! -f "$CONF/env" ]; then
  cp "$BASIS/repo/deploy/env.voorbeeld" "$CONF/env"
  echo "   $CONF/env aangemaakt — vul de geheimen in voordat je start"
fi
chown root:orchestrator "$CONF/env"
chmod 640 "$CONF/env"

echo "==> tests, voordat er iets gaat draaien"
sudo -u orchestrator bash -c "cd '$BASIS/repo/orchestrator' && python3 -m unittest discover -s tests -q" \
  || { echo "   tests falen; installatie afgebroken"; exit 1; }

echo "==> systemd"
cp "$BASIS/repo/deploy/orchestrator.service" /etc/systemd/system/
cp "$BASIS/repo/deploy/orchestrator-status.service" /etc/systemd/system/
cp "$BASIS/repo/deploy/orchestrator-status.timer" /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now orchestrator-status.timer

echo
echo "Klaar. Nu:"
echo "  1. vul $CONF/env in (geheimen)"
echo "  2. sudo -u orchestrator bash -c 'set -a; . $CONF/env; set +a; cd $BASIS/repo/orchestrator && python3 -m orchestrator.cli doctor'"
echo "  3. systemctl enable --now orchestrator"
echo "  4. systemctl status orchestrator  en  journalctl -u orchestrator -f"
