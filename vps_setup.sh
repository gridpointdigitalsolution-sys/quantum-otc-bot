#!/usr/bin/env bash
# One-shot VPS setup for the Quantum OTC bot dashboard (Ubuntu 24.04).
# Run on the VPS:  curl -sSL <raw-url>/vps_setup.sh | bash
set -e
echo "== installing deps =="
apt-get update -y
apt-get install -y python3 python3-pip python3-venv git
echo "== pulling bot =="
rm -rf /opt/otc-bot
git clone https://github.com/gridpointdigitalsolution-sys/quantum-otc-bot.git /opt/otc-bot
cd /opt/otc-bot
python3 -m venv .venv
. .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
echo "== service =="
cat >/etc/systemd/system/otc-bot.service <<'UNIT'
[Unit]
Description=Quantum OTC Bot
After=network.target
[Service]
WorkingDirectory=/opt/otc-bot
Environment=BOT_HOST=0.0.0.0
Environment=BOT_PORT=8000
ExecStart=/opt/otc-bot/.venv/bin/python -m dashboard.server
Restart=always
RestartSec=5
[Install]
WantedBy=multi-user.target
UNIT
systemctl daemon-reload
systemctl enable --now otc-bot
echo "== firewall =="
ufw allow 8000/tcp || true
ufw allow OpenSSH || true
ufw --force enable || true
sleep 6
echo "== status =="
systemctl status otc-bot --no-pager | head -8
echo ""
echo "DONE -> open http://187.77.176.95:8000"
