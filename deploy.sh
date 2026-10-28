#!/bin/sh
set -eu

PORT=8001
HOST=0.0.0.0
APP_DIR=/opt/streamcli
SERVICE=streamcli-api
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)

if [ "$(id -u)" -ne 0 ]; then
    echo "Run this script as root: sudo sh deploy.sh" >&2
    exit 1
fi

if ! command -v python3 >/dev/null 2>&1; then
    echo "python3 is required but was not found." >&2
    exit 1
fi

if ! id streamcli >/dev/null 2>&1; then
    useradd --system --home "$APP_DIR" --shell /usr/sbin/nologin streamcli
fi

mkdir -p "$APP_DIR"
cp "$SCRIPT_DIR/api.py" "$APP_DIR/api.py"
cp "$SCRIPT_DIR/.env.example" "$APP_DIR/.env.example"

if [ ! -f "$APP_DIR/.env" ]; then
    cp "$APP_DIR/.env.example" "$APP_DIR/.env"
fi

if grep -q '^PORT=' "$APP_DIR/.env"; then
    sed -i "s/^PORT=.*/PORT=$PORT/" "$APP_DIR/.env"
else
    printf '\nPORT=%s\n' "$PORT" >> "$APP_DIR/.env"
fi

if grep -q '^HOST=' "$APP_DIR/.env"; then
    sed -i "s/^HOST=.*/HOST=$HOST/" "$APP_DIR/.env"
else
    printf '\nHOST=%s\n' "$HOST" >> "$APP_DIR/.env"
fi

chown -R streamcli:streamcli "$APP_DIR"

install -m 644 "$SCRIPT_DIR/deploy/$SERVICE.service" "/etc/systemd/system/$SERVICE.service"
systemctl daemon-reload
systemctl enable "$SERVICE"
systemctl restart "$SERVICE"

echo "Deployed $SERVICE on $HOST:$PORT (public)"
echo "Status:  systemctl status $SERVICE"
echo "Logs:    journalctl -u $SERVICE -f"
echo "Config:  $APP_DIR/.env"
