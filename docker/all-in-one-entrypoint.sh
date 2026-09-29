#!/bin/bash
set -Eeuo pipefail

bitcoin_pid=""
dashboard_pid=""
stopping=0

shutdown_children() {
    if [ "$stopping" -eq 1 ]; then
        return
    fi
    stopping=1

    if [ -n "$dashboard_pid" ] && kill -0 "$dashboard_pid" 2>/dev/null; then
        kill -TERM "$dashboard_pid" 2>/dev/null || true
    fi
    if [ -n "$bitcoin_pid" ] && kill -0 "$bitcoin_pid" 2>/dev/null; then
        bitcoin-cli -datadir="$BITCOIN_DATADIR" stop >/dev/null 2>&1 || \
            kill -TERM "$bitcoin_pid" 2>/dev/null || true
    fi
}

trap shutdown_children TERM INT

bitcoind \
    -conf=/etc/bitcoin/bitcoin.conf \
    -datadir="$BITCOIN_DATADIR" &
bitcoin_pid=$!

python3 /app/app.py &
dashboard_pid=$!

set +e
wait -n "$bitcoin_pid" "$dashboard_pid"
status=$?
set -e

shutdown_children
wait "$dashboard_pid" 2>/dev/null || true
wait "$bitcoin_pid" 2>/dev/null || true
exit "$status"
