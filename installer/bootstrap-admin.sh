#!/bin/sh
set -eu

test "$(id -u)" -eq 0 || { echo "Run as root" >&2; exit 1; }
id deploybot >/dev/null 2>&1 || { echo "User deploybot does not exist" >&2; exit 1; }

script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
project_dir=$(dirname "$script_dir")

install -d -o root -g root -m 0755 /opt/bitcoin-dashboard-admin
install -o root -g root -m 0755 "$project_dir/admin/admin_app.py" /opt/bitcoin-dashboard-admin/admin_app.py
install -o root -g root -m 0755 "$script_dir/update-bitcoin-dashboard" /usr/local/sbin/update-bitcoin-dashboard
install -o root -g root -m 0755 "$script_dir/update-bitcoin-core" /usr/local/sbin/update-bitcoin-core
install -o root -g root -m 0644 "$project_dir/admin/bitcoin-dashboard-admin.service" /etc/systemd/system/bitcoin-dashboard-admin.service

if test ! -f /etc/bitcoin-dashboard-updater.conf; then
    printf '%s\n' \
        'UPDATE_ROOT=/home/todo' \
        'DASHBOARD_USER=btc' \
        'DASHBOARD_TARGET=/home/btc/bitcoin-dashboard' \
        'DASHBOARD_SERVICE=bitcoin-dashboard' \
        'DASHBOARD_HEALTH_URL=http://127.0.0.1:8787/healthz' \
        'BITCOIN_SERVICE=bitcoind' \
        'BITCOIN_BIN_DIR=/home/btc/bin' \
        > /etc/bitcoin-dashboard-updater.conf
    chown root:root /etc/bitcoin-dashboard-updater.conf
    chmod 0640 /etc/bitcoin-dashboard-updater.conf
fi

token=$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')
umask 077
printf 'ADMIN_PORT=8790\nADMIN_TOKEN=%s\nBITCOIN_CLI=/home/btc/bin/bitcoin-cli\nUPDATE_ROOT=/home/todo\n' "$token" > /etc/default/bitcoin-dashboard-admin
chown root:root /etc/default/bitcoin-dashboard-admin
chmod 0600 /etc/default/bitcoin-dashboard-admin

sudoers_tmp=$(mktemp)
trap 'rm -f -- "$sudoers_tmp"' EXIT INT TERM
cat >"$sudoers_tmp" <<'EOF'
deploybot ALL=(root) NOPASSWD: /usr/local/sbin/update-bitcoin-dashboard
deploybot ALL=(root) NOPASSWD: /usr/local/sbin/update-bitcoin-core
EOF
chmod 0440 "$sudoers_tmp"
visudo -cf "$sudoers_tmp"
install -o root -g root -m 0440 "$sudoers_tmp" /etc/sudoers.d/bitcoin-dashboard-updates

systemctl daemon-reload
systemctl enable --now bitcoin-dashboard-admin

echo "Admin UI installed on 127.0.0.1:8790"
echo "SSH tunnel: ssh -L 8790:127.0.0.1:8790 trading-server"
echo "Username: admin"
echo "Password: $token"
echo "Store this password securely; it is only printed once."
