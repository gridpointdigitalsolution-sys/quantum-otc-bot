#!/usr/bin/env bash
# Deploy the Quantum OTC bot dashboard on a fresh Ubuntu 24.04 VPS.
# Run as root:  bash deploy_vps.sh bot.churchillbracknell.com
# (code must already be in /opt/otc-bot — see transfer step in chat)
set -e
DOMAIN="${1:-}"
APPDIR="/opt/otc-bot"

echo "== installing system deps =="
apt-get update -y
apt-get install -y python3 python3-pip python3-venv nginx git ufw

echo "== python env =="
cd "$APPDIR"
python3 -m venv .venv
. .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

echo "== systemd service (always-on, auto-restart) =="
cat >/etc/systemd/system/otc-bot.service <<EOF
[Unit]
Description=Quantum OTC Bot dashboard
After=network.target
[Service]
WorkingDirectory=$APPDIR
Environment=BOT_HOST=127.0.0.1
Environment=BOT_PORT=8000
ExecStart=$APPDIR/.venv/bin/python -m dashboard.server
Restart=always
RestartSec=5
[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload
systemctl enable --now otc-bot

echo "== nginx reverse proxy =="
cat >/etc/nginx/sites-available/otc-bot <<EOF
server {
  listen 80;
  server_name $DOMAIN;
  location / {
    proxy_pass http://127.0.0.1:8000;
    proxy_http_version 1.1;
    proxy_set_header Upgrade \$http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_set_header Host \$host;
  }
}
EOF
ln -sf /etc/nginx/sites-available/otc-bot /etc/nginx/sites-enabled/otc-bot
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl restart nginx

echo "== firewall =="
ufw allow OpenSSH; ufw allow 'Nginx Full'; ufw --force enable

if [ -n "$DOMAIN" ]; then
  echo "== HTTPS (certbot) — needs DNS A record $DOMAIN -> this server already set =="
  apt-get install -y certbot python3-certbot-nginx
  certbot --nginx -d "$DOMAIN" --non-interactive --agree-tos -m admin@"$DOMAIN" || \
    echo "certbot failed (check DNS A record points here); site still works on http://"
fi

echo "== DONE =="
echo "Dashboard: http(s)://${DOMAIN:-<server-ip>}"
echo "Logs: journalctl -u otc-bot -f"
