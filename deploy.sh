#!/bin/sh
set -eu

PORT=8001
APP_DIR=/opt/streamcli
SERVICE=streamcli-api
NGINX_SITE=streamcli
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

if ! grep -q '^HOST=' "$APP_DIR/.env"; then
    printf 'HOST=127.0.0.1\n' >> "$APP_DIR/.env"
fi

chown -R streamcli:streamcli "$APP_DIR"

install -m 644 "$SCRIPT_DIR/deploy/$SERVICE.service" "/etc/systemd/system/$SERVICE.service"
systemctl daemon-reload
systemctl enable "$SERVICE"
systemctl restart "$SERVICE"

if command -v nginx >/dev/null 2>&1; then
    sed "s/127\.0\.0\.1:[0-9]\+/127.0.0.1:$PORT/" \
        "$SCRIPT_DIR/deploy/nginx.conf" \
        > "/etc/nginx/sites-available/$NGINX_SITE"

    ln -sf "/etc/nginx/sites-available/$NGINX_SITE" "/etc/nginx/sites-enabled/$NGINX_SITE"

    if nginx -t; then
        systemctl reload nginx
    else
        echo "nginx config test failed; fix it before reloading nginx." >&2
    fi
else
    echo "nginx not found; skipping reverse proxy setup." >&2
fi

echo "Deployed $SERVICE on 127.0.0.1:$PORT"
echo "Status:  systemctl status $SERVICE"
echo "Logs:    journalctl -u $SERVICE -f"
echo "Config:  $APP_DIR/.env"
