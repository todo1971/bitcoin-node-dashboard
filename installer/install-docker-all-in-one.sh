#!/bin/sh
# Copyright (C) 2026 Hardy (todo1971) <hb@308-arms.de>
# SPDX-License-Identifier: GPL-3.0-only
set -eu

usage() {
    cat <<'EOF'
Usage: install-docker-all-in-one.sh --public-address ADDRESS [options]

Options:
  --install-dir PATH  Installation directory below /opt
                      (default: /opt/bitcoin-node-dashboard)
  --prepare-only      Copy and validate files without starting containers
  --help              Show this help

ADMIN_TOKEN may be supplied through the environment. If it is omitted, a
cryptographically random token is generated.
EOF
}

test "$(id -u)" -eq 0 || { echo "Run as root" >&2; exit 1; }

public_address=${PUBLIC_NODE_ADDRESS:-}
install_dir=/opt/bitcoin-node-dashboard
start_stack=1

while test "$#" -gt 0; do
    case "$1" in
        --public-address)
            test "$#" -ge 2 || { echo "Missing address" >&2; exit 2; }
            public_address=$2
            shift 2
            ;;
        --install-dir)
            test "$#" -ge 2 || { echo "Missing installation directory" >&2; exit 2; }
            install_dir=$2
            shift 2
            ;;
        --prepare-only)
            start_stack=0
            shift
            ;;
        --help)
            usage
            exit 0
            ;;
        *)
            echo "Unknown option: $1" >&2
            usage >&2
            exit 2
            ;;
    esac
done

case "$public_address" in
    ''|*[!A-Za-z0-9.:-]*) echo "Invalid public address" >&2; exit 2 ;;
esac
command -v readlink >/dev/null 2>&1 || { echo "readlink is unavailable" >&2; exit 1; }
install_dir=$(readlink -m -- "$install_dir")
case "$install_dir" in
    /opt/*) ;;
    *) echo "Installation directory must be below /opt" >&2; exit 2 ;;
esac

command -v docker >/dev/null 2>&1 || { echo "Docker is not installed" >&2; exit 1; }
docker compose version >/dev/null 2>&1 || { echo "Docker Compose is unavailable" >&2; exit 1; }

script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
project_dir=$(dirname "$script_dir")
for required in app.py Dockerfile.all-in-one compose.all-in-one.yaml docker.env.example; do
    test -e "$project_dir/$required" || { echo "Missing $required" >&2; exit 1; }
done
test -d "$project_dir/static" || { echo "Missing static directory" >&2; exit 1; }
test -d "$project_dir/docker" || { echo "Missing docker directory" >&2; exit 1; }
if find "$project_dir/static" "$project_dir/docker" -type l -print -quit | grep -q .; then
    echo "Symbolic links are not allowed in the installation source" >&2
    exit 1
fi

for destination in \
    "$install_dir" "$install_dir/static" "$install_dir/docker" \
    "$install_dir/app.py" "$install_dir/Dockerfile.all-in-one" \
    "$install_dir/compose.all-in-one.yaml" "$install_dir/docker.env.example" \
    "$install_dir/.env"; do
    test ! -L "$destination" || { echo "Refusing symbolic link: $destination" >&2; exit 1; }
done

install -d -o root -g root -m 0755 "$install_dir" "$install_dir/static" "$install_dir/docker"
for file in app.py LICENSE NOTICE Dockerfile.all-in-one compose.all-in-one.yaml docker.env.example; do
    install -o root -g root -m 0644 "$project_dir/$file" "$install_dir/$file"
done
cp -a "$project_dir/static/." "$install_dir/static/"
cp -a "$project_dir/docker/." "$install_dir/docker/"
chown -R root:root "$install_dir/static" "$install_dir/docker"

env_file="$install_dir/.env"
if test ! -f "$env_file"; then
    admin_token=${ADMIN_TOKEN:-}
    if test -z "$admin_token"; then
        admin_token=$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')
    fi
    case "$admin_token" in
        *[!A-Za-z0-9_-]*) echo "ADMIN_TOKEN contains unsupported characters" >&2; exit 2 ;;
    esac
    test "${#admin_token}" -ge 32 || { echo "ADMIN_TOKEN must contain at least 32 characters" >&2; exit 2; }
    umask 077
    {
        printf 'PUBLIC_NODE_ADDRESS=%s\n' "$public_address"
        printf 'ADMIN_TOKEN=%s\n' "$admin_token"
        printf '%s\n' \
            'BITCOIN_UID=1010' \
            'BITCOIN_GID=1010' \
            'DASHBOARD_PORT=8787' \
            'BITCOIN_CORE_VERSION=31.1' \
            'BITCOIN_P2P_BIND=0.0.0.0' \
            'DISK_MAX_USED_PERCENT=90' \
            'MEMORY_MAX_USED_PERCENT=90' \
            'ALERT_EMAIL=' \
            'ALERT_WEBHOOK_URL='
    } >"$env_file"
    chmod 0600 "$env_file"
else
    echo "Keeping existing $env_file"
fi

compose() {
    docker compose --project-directory "$install_dir" \
        --env-file "$env_file" -f "$install_dir/compose.all-in-one.yaml" "$@"
}

compose config --quiet

if test "$start_stack" -eq 0; then
    echo "All-in-one stack prepared and validated in $install_dir"
    exit 0
fi

existing_container=$(compose ps -q node 2>/dev/null || true)
if test -z "$existing_container" && command -v ss >/dev/null 2>&1; then
    if ss -lntH | awk '{print $4}' | grep -Eq '(^|\]|:)(8333|8787)$'; then
        echo "Port 8333 or 8787 is already in use; existing services were not changed" >&2
        exit 1
    fi
fi

compose up -d --build
compose ps
echo "Dashboard: http://127.0.0.1:8787"
echo "Configuration: $env_file"
echo "Data volume: bitcoin-node-all-in-one_node-data"
