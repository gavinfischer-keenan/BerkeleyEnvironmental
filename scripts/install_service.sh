#!/usr/bin/env bash
set -euo pipefail

INSTALL_DIR="/opt/envstation"
SERVICE_USER="envstation"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "=== Berkeley Environmental Station — Install ==="

if ! id "$SERVICE_USER" &>/dev/null; then
    sudo useradd --system --no-create-home --shell /usr/sbin/nologin "$SERVICE_USER"
    echo "Created user: $SERVICE_USER"
fi

sudo mkdir -p "$INSTALL_DIR"
sudo rsync -a --exclude '.git' --exclude '__pycache__' --exclude 'venv' "$PROJECT_DIR/" "$INSTALL_DIR/"

if [ ! -d "$INSTALL_DIR/venv" ]; then
    sudo python3 -m venv "$INSTALL_DIR/venv"
fi
sudo "$INSTALL_DIR/venv/bin/pip" install --upgrade pip
sudo "$INSTALL_DIR/venv/bin/pip" install -e "$INSTALL_DIR"

sudo mkdir -p "$INSTALL_DIR/data"
sudo chown -R "$SERVICE_USER:$SERVICE_USER" "$INSTALL_DIR/data"

if [ ! -f "$INSTALL_DIR/.env" ]; then
    sudo cp "$INSTALL_DIR/.env.example" "$INSTALL_DIR/.env"
    echo "Copied .env.example → .env (edit with your settings)"
fi

sudo cp "$INSTALL_DIR/systemd/envstation.service" /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable envstation
sudo systemctl start envstation

echo ""
echo "=== Installation complete ==="
sudo systemctl status envstation --no-pager
