#!/bin/sh
set -eu

test "$(id -u)" -eq 0 || { echo "Run as root" >&2; exit 1; }

script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
project_dir=$(dirname "$script_dir")

install -o root -g root -m 0755 "$script_dir/update-bitcoin-dashboard" /usr/local/sbin/update-bitcoin-dashboard
install -o root -g root -m 0755 "$script_dir/update-bitcoin-core" /usr/local/sbin/update-bitcoin-core
install -d -o root -g root -m 0755 /usr/local/libexec
install -o root -g root -m 0755 "$script_dir/fetch-dashboard-release" /usr/local/libexec/fetch-bitcoin-dashboard-release

if test ! -f /etc/bitcoin-dashboard-updater.conf; then
    printf '%s\n' \
        'UPDATE_ROOT=/var/cache/bitcoin-dashboard-updates' \
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
update_root=/var/cache/bitcoin-dashboard-updates
test ! -L /etc/bitcoin-dashboard-updater.conf || { echo "Unsafe updater config link" >&2; exit 1; }
test ! -L "$update_root" || { echo "Unsafe update cache link" >&2; exit 1; }
install -d -o root -g root -m 0700 "$update_root"
if grep -q '^UPDATE_ROOT=' /etc/bitcoin-dashboard-updater.conf; then
    sed -i "s#^UPDATE_ROOT=.*#UPDATE_ROOT=$update_root#" /etc/bitcoin-dashboard-updater.conf
else
    printf 'UPDATE_ROOT=%s\n' "$update_root" >> /etc/bitcoin-dashboard-updater.conf
fi
chown root:root /etc/bitcoin-dashboard-updater.conf
chmod 0640 /etc/bitcoin-dashboard-updater.conf
grep -q '^BITCOIN_UPLOAD_DIR=' /etc/bitcoin-dashboard-updater.conf || \
    printf '%s\n' 'BITCOIN_UPLOAD_DIR=/var/lib/bitcoin-dashboard/bitcoin-core-upload' >> /etc/bitcoin-dashboard-updater.conf
grep -q '^BITCOIN_MIN_VALID_SIGNATURES=' /etc/bitcoin-dashboard-updater.conf || \
    printf '%s\n' 'BITCOIN_MIN_VALID_SIGNATURES=2' >> /etc/bitcoin-dashboard-updater.conf
dashboard_user=$(sed -n 's/^DASHBOARD_USER=//p' /etc/bitcoin-dashboard-updater.conf | tail -n 1)
case "$dashboard_user" in *[!A-Za-z0-9_-]*|'') echo "Invalid dashboard user" >&2; exit 1 ;; esac
id "$dashboard_user" >/dev/null 2>&1 || { echo "User $dashboard_user does not exist" >&2; exit 1; }
dashboard_target=$(sed -n 's/^DASHBOARD_TARGET=//p' /etc/bitcoin-dashboard-updater.conf | tail -n 1)
unit_path=/etc/systemd/system/bitcoin-dashboard.service
if test "$dashboard_user" = btc && test "$dashboard_target" = /home/btc/bitcoin-dashboard; then
    install -o root -g root -m 0644 "$project_dir/bitcoin-dashboard.service" "$unit_path"
elif test -f "$unit_path"; then
    unit_tmp=$(mktemp)
    sed '/^\(NoNewPrivileges\|PrivateDevices\|ProtectClock\|ProtectKernelLogs\|ProtectKernelModules\|ProtectKernelTunables\|RestrictNamespaces\|LockPersonality\|SystemCallArchitectures\)=/d' "$unit_path" >"$unit_tmp"
    install -o root -g root -m 0644 "$unit_tmp" "$unit_path"
    rm -f -- "$unit_tmp"
else
    echo "Missing $unit_path" >&2
    exit 1
fi

env_file=/etc/default/bitcoin-dashboard
test -f "$env_file" || install -o root -g root -m 0640 "$project_dir/bitcoin-dashboard.env.example" "$env_file"
token=$(sed -n 's/^ADMIN_TOKEN=//p' "$env_file" | tail -n 1)
if test "${#token}" -lt 32; then
    token=$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')
fi
env_tmp=$(mktemp)
grep -v '^ADMIN_TOKEN=' "$env_file" >"$env_tmp" || true
printf 'ADMIN_TOKEN=%s\n' "$token" >>"$env_tmp"
grep -q '^DASHBOARD_GITHUB_REPOSITORY=' "$env_tmp" || \
    printf '%s\n' 'DASHBOARD_GITHUB_REPOSITORY=todo1971/bitcoin-node-dashboard' >>"$env_tmp"
grep -q '^DASHBOARD_GITHUB_TOKEN=' "$env_tmp" || \
    printf '%s\n' 'DASHBOARD_GITHUB_TOKEN=' >>"$env_tmp"
grep -q '^BITCOIN_UPLOAD_DIR=' "$env_tmp" || \
    printf '%s\n' 'BITCOIN_UPLOAD_DIR=/var/lib/bitcoin-dashboard/bitcoin-core-upload' >>"$env_tmp"
grep -q '^BITCOIN_UPLOAD_MAX_BYTES=' "$env_tmp" || \
    printf '%s\n' 'BITCOIN_UPLOAD_MAX_BYTES=209715200' >>"$env_tmp"
install -o root -g root -m 0640 "$env_tmp" "$env_file"
rm -f -- "$env_tmp"

sudoers_tmp=$(mktemp)
trap 'rm -f -- "$sudoers_tmp"' EXIT INT TERM
printf '%s\n' \
    "$dashboard_user ALL=(root) NOPASSWD: /usr/bin/systemd-run --unit=bitcoin-dashboard-update --collect --no-block /usr/local/sbin/update-bitcoin-dashboard" \
    "$dashboard_user ALL=(root) NOPASSWD: /usr/bin/systemd-run --unit=bitcoin-core-update --collect --no-block /usr/local/sbin/update-bitcoin-core" \
    "$dashboard_user ALL=(root) NOPASSWD: /usr/bin/journalctl --unit=bitcoin-dashboard-update --lines=80 --no-pager --output=short-iso --quiet" \
    "$dashboard_user ALL=(root) NOPASSWD: /usr/bin/journalctl --unit=bitcoin-core-update --lines=80 --no-pager --output=short-iso --quiet" \
    >"$sudoers_tmp"
chmod 0440 "$sudoers_tmp"
visudo -cf "$sudoers_tmp"
install -o root -g root -m 0440 "$sudoers_tmp" /etc/sudoers.d/bitcoin-dashboard-updates

systemctl disable --now bitcoin-dashboard-admin 2>/dev/null || true
rm -f /etc/systemd/system/bitcoin-dashboard-admin.service
rm -f /etc/default/bitcoin-dashboard-admin
rm -rf -- /opt/bitcoin-dashboard-admin

systemctl daemon-reload
systemctl restart bitcoin-dashboard

echo "Integrated admin UI installed at /admin"
echo "Username: admin"
echo "Password: $token"
echo "Store this password securely. Use the public URL only over HTTPS."
