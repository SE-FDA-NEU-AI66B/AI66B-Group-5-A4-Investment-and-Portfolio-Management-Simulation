#!/usr/bin/env bash
# Install or update VirtuTrade on a Debian 12 Google Cloud e2-micro VM.
# Re-running it updates the code and keeps the database and settings.
# Usage: bash setup.sh            (host name <external-ip>.sslip.io)
#        SITE_ADDRESS=my.domain bash setup.sh
set -euo pipefail

REPO="${REPO:-https://github.com/SE-FDA-NEU-AI66B/AI66B-Group-5-A4-Investment-and-Portfolio-Management-Simulation.git}"
BRANCH="${BRANCH:-main}"
APP=/opt/virtutrade
ENV_FILE=/etc/virtutrade/virtutrade.env
DATA=/var/lib/virtutrade

if [ -z "${SITE_ADDRESS:-}" ]; then
  ip=$(curl -fsS -H 'Metadata-Flavor: Google' \
    http://metadata.google.internal/computeMetadata/v1/instance/network-interfaces/0/access-configs/0/external-ip)
  SITE_ADDRESS="${ip//./-}.sslip.io"
fi

sudo apt-get update -q
sudo apt-get install -y -q python3-venv git caddy

# The e2-micro has 1 GB of RAM: swap keeps pip and gunicorn from being killed.
if [ ! -f /swapfile ]; then
  sudo fallocate -l 1G /swapfile
  sudo chmod 600 /swapfile
  sudo mkswap /swapfile >/dev/null
  sudo swapon /swapfile
  echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab >/dev/null
fi

id virtutrade >/dev/null 2>&1 || sudo useradd --system --home "$DATA" --shell /usr/sbin/nologin virtutrade
sudo install -d -o virtutrade -g virtutrade -m 750 "$DATA"
sudo install -d -o root -g virtutrade -m 750 /etc/virtutrade

if [ -d "$APP/.git" ]; then
  sudo git -C "$APP" fetch --quiet origin "$BRANCH"
  sudo git -C "$APP" checkout --quiet "$BRANCH"
  sudo git -C "$APP" merge --ff-only --quiet "origin/$BRANCH"
else
  sudo git clone --quiet --branch "$BRANCH" "$REPO" "$APP"
fi
sudo python3 -m venv "$APP/.venv"
sudo "$APP/.venv/bin/pip" install --quiet --upgrade pip
sudo "$APP/.venv/bin/pip" install --quiet -e "$APP"

if [ ! -f "$ENV_FILE" ]; then
  sudo install -o root -g virtutrade -m 640 "$APP/deploy/gcp/virtutrade.env.example" "$ENV_FILE"
  secret=$(python3 -c 'import secrets; print(secrets.token_hex(32))')
  sudo sed -i "s/^SECRET_KEY=$/SECRET_KEY=$secret/" "$ENV_FILE"
fi

# Run a CLI command as the service user with the service settings.
as_app() {
  sudo -u virtutrade bash -c "set -a; . '$ENV_FILE'; set +a; cd '$APP'; exec .venv/bin/python -m virtutrade $1"
}
mode=$(sudo sed -n 's/^QUOTE_MODE=//p' "$ENV_FILE")
database=$(sudo sed -n 's/^DATABASE_PATH=//p' "$ENV_FILE")
if [ "$mode" = simulation ] && ! sudo test -f "$database"; then
  as_app init-demo
else
  as_app init-db  # Idempotent: adds new tables, keeps accounts and trades.
fi

sudo install -m 644 "$APP/deploy/gcp/virtutrade-web.service" "$APP/deploy/gcp/virtutrade-feed.service" \
  /etc/systemd/system/
sed "s/SITE_ADDRESS/$SITE_ADDRESS/" "$APP/deploy/gcp/Caddyfile" | sudo tee /etc/caddy/Caddyfile >/dev/null
sudo systemctl daemon-reload
sudo systemctl enable --quiet virtutrade-web virtutrade-feed caddy
sudo systemctl restart virtutrade-web virtutrade-feed caddy

echo "VirtuTrade is starting at https://$SITE_ADDRESS"
echo "Settings: sudo nano $ENV_FILE   Logs: journalctl -u virtutrade-web -u virtutrade-feed -f"
