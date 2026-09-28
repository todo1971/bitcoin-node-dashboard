#!/usr/bin/env python3
"""Small, read-only Bitcoin Core dashboard with no external dependencies."""

from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import threading
import time
import urllib.error
import urllib.request
from contextlib import closing
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse


APP_DIR = Path(__file__).resolve().parent
__version__ = "1.3.0"
STATIC_DIR = APP_DIR / "static"
HOST = os.getenv("DASHBOARD_HOST", "127.0.0.1")
PORT = int(os.getenv("DASHBOARD_PORT", "8787"))
CACHE_SECONDS = max(1, int(os.getenv("DASHBOARD_CACHE_SECONDS", "10")))
BITCOIN_CLI = os.getenv("BITCOIN_CLI", "/home/btc/bin/bitcoin-cli")
BITCOIN_DATADIR = os.getenv("BITCOIN_DATADIR", "/home/btc/bitcoin-data")
BITCOIN_COOKIE = os.getenv(
    "BITCOIN_COOKIE", "/home/btc/bitcoin-core/.bitcoin/.cookie"
)
PUBLIC_NODE_ADDRESS = os.getenv("PUBLIC_NODE_ADDRESS", "217.160.16.224")
PUBLIC_NODE_PORT = int(os.getenv("PUBLIC_NODE_PORT", "8333"))
EXTERNAL_CACHE_SECONDS = max(
    60, int(os.getenv("EXTERNAL_CACHE_SECONDS", "300"))
)
DATABASE_PATH = os.getenv(
    "DATABASE_PATH", "/var/lib/bitcoin-dashboard/history.sqlite3"
)
SAMPLE_INTERVAL_SECONDS = max(
    30, int(os.getenv("SAMPLE_INTERVAL_SECONDS", "60"))
)
HISTORY_RETENTION_DAYS = max(
    1, int(os.getenv("HISTORY_RETENTION_DAYS", "365"))
)

HISTORY_RANGES: dict[str, tuple[int, int]] = {
    "1h": (60 * 60, 60),
    "6h": (6 * 60 * 60, 2 * 60),
    "12h": (12 * 60 * 60, 5 * 60),
    "24h": (24 * 60 * 60, 5 * 60),
    "7d": (7 * 24 * 60 * 60, 30 * 60),
    "30d": (30 * 24 * 60 * 60, 2 * 60 * 60),
    "1y": (365 * 24 * 60 * 60, 24 * 60 * 60),
}

_cache_lock = threading.Lock()
_cache: dict[str, Any] = {"expires": 0.0, "data": None}
_external_cache_lock = threading.Lock()
_external_cache: dict[str, Any] = {"expires": 0.0, "data": None}


class RpcError(RuntimeError):
    pass


def bitcoin_cli(*args: str, timeout: int = 20) -> Any:
    command = [
        BITCOIN_CLI,
        f"-datadir={BITCOIN_DATADIR}",
        f"-rpccookiefile={BITCOIN_COOKIE}",
        *args,
    ]
    try:
        result = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise RpcError(str(exc)) from exc
    if result.returncode != 0:
        message = result.stderr.strip() or result.stdout.strip() or "RPC failed"
        raise RpcError(message)
    output = result.stdout.strip()
    if not output:
        return None
    try:
        return json.loads(output)
    except json.JSONDecodeError:
        return output


def safe_call(*args: str) -> Any:
    try:
        return bitcoin_cli(*args)
    except RpcError:
        return None


def fee_rate(target: int) -> float | None:
    response = safe_call("estimatesmartfee", str(target))
    if not isinstance(response, dict):
        return None
    value = response.get("feerate")
    if not isinstance(value, (int, float)):
        return None
    # Bitcoin Core returns BTC/kvB. Convert to sat/vB.
    return round(float(value) * 100_000, 2)


def fetch_external_node_status() -> dict[str, Any]:
    """Read public crawler data. Failure must never break the local dashboard."""
    now = time.monotonic()
    with _external_cache_lock:
        if _external_cache["data"] is not None and now < _external_cache["expires"]:
            return _external_cache["data"]

        lookup_url = (
            "https://btcnodes.io/api/v1/nodes/"
            f"{PUBLIC_NODE_ADDRESS}-{PUBLIC_NODE_PORT}/"
        )
        page_url = (
            "https://btcnodes.io/nodes/?q="
            f"{PUBLIC_NODE_ADDRESS}"
        )
        result: dict[str, Any] = {
            "available": False,
            "reachable": None,
            "address": PUBLIC_NODE_ADDRESS,
            "port": PUBLIC_NODE_PORT,
            "page_url": page_url,
            "legacy_bitnodes_url": (
                "https://bitnodes.io/nodes/?q=" f"{PUBLIC_NODE_ADDRESS}"
            ),
        }
        try:
            request = urllib.request.Request(
                lookup_url,
                headers={"Accept": "application/json", "User-Agent": "BitcoinDashboard/1.1"},
            )
            with urllib.request.urlopen(request, timeout=5) as response:
                payload = json.load(response)
            details = payload.get("data") or []
            result.update(
                available=True,
                reachable=payload.get("status") == "UP",
                status=payload.get("status"),
                user_agent=details[1] if len(details) > 1 else None,
                last_seen=details[2] if len(details) > 2 else None,
                height=details[4] if len(details) > 4 else None,
                country=details[7] if len(details) > 7 else None,
                asn=details[11] if len(details) > 11 else None,
                provider=details[12] if len(details) > 12 else None,
            )
        except (OSError, ValueError, urllib.error.URLError):
            pass

        _external_cache.update(
            data=result,
            expires=now + EXTERNAL_CACHE_SECONDS,
        )
        return result


def build_snapshot() -> dict[str, Any]:
    chain = bitcoin_cli("getblockchaininfo")
    network = bitcoin_cli("getnetworkinfo")
    mempool = bitcoin_cli("getmempoolinfo")
    net_totals = bitcoin_cli("getnettotals")
    peers = bitcoin_cli("getpeerinfo")

    height = int(chain.get("blocks", 0))
    block_stats = safe_call("getblockstats", str(height)) if height else None
    peer_networks: dict[str, int] = {}
    inbound = 0
    outbound = 0
    for peer in peers if isinstance(peers, list) else []:
        name = str(peer.get("network", "unknown"))
        peer_networks[name] = peer_networks.get(name, 0) + 1
        if peer.get("inbound"):
            inbound += 1
        else:
            outbound += 1

    return {
        "generated_at": int(time.time()),
        "chain": {
            "chain": chain.get("chain"),
            "blocks": height,
            "headers": chain.get("headers"),
            "verification_progress": chain.get("verificationprogress"),
            "initial_block_download": chain.get("initialblockdownload"),
            "pruned": chain.get("pruned"),
            "size_on_disk": chain.get("size_on_disk"),
            "best_block_hash": chain.get("bestblockhash"),
            "warnings": chain.get("warnings", ""),
        },
        "network": {
            "version": network.get("subversion"),
            "connections": network.get("connections"),
            "connections_in": network.get("connections_in", inbound),
            "connections_out": network.get("connections_out", outbound),
            "networks": peer_networks,
            "bytes_received": net_totals.get("totalbytesrecv"),
            "bytes_sent": net_totals.get("totalbytessent"),
        },
        "mempool": {
            "transactions": mempool.get("size"),
            "bytes": mempool.get("bytes"),
            "memory_usage": mempool.get("usage"),
            "max_memory": mempool.get("maxmempool"),
            "min_fee_btc_kvb": mempool.get("mempoolminfee"),
            "total_fee_btc": mempool.get("total_fee"),
        },
        "fees_sat_vb": {
            "2": fee_rate(2),
            "6": fee_rate(6),
            "12": fee_rate(12),
        },
        "latest_block": block_stats,
        "external_node": fetch_external_node_status(),
    }


def snapshot() -> dict[str, Any]:
    now = time.monotonic()
    with _cache_lock:
        if _cache["data"] is not None and now < _cache["expires"]:
            return _cache["data"]
        data = build_snapshot()
        _cache.update(data=data, expires=now + CACHE_SECONDS)
        return data


def database_connection() -> sqlite3.Connection:
    database = Path(DATABASE_PATH)
    database.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(database, timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA busy_timeout = 10000")
    return connection


def init_database() -> None:
    with closing(database_connection()) as connection:
        with connection:
            connection.execute("PRAGMA journal_mode = WAL")
            connection.execute("PRAGMA synchronous = NORMAL")
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS node_samples (
                    sampled_at INTEGER PRIMARY KEY,
                    blocks INTEGER NOT NULL,
                    verification_progress REAL,
                    size_on_disk INTEGER,
                    connections INTEGER,
                    connections_in INTEGER,
                    connections_out INTEGER,
                    mempool_transactions INTEGER,
                    mempool_bytes INTEGER,
                    mempool_memory_usage INTEGER,
                    mempool_min_fee_sat_vb REAL,
                    fee_2_sat_vb REAL,
                    fee_6_sat_vb REAL,
                    fee_12_sat_vb REAL,
                    bytes_received INTEGER,
                    bytes_sent INTEGER,
                    block_transactions INTEGER,
                    block_total_fee_btc REAL
                )
                """
            )


def _number(value: Any) -> int | float | None:
    return value if isinstance(value, (int, float)) else None


def store_snapshot(data: dict[str, Any]) -> None:
    chain = data.get("chain", {})
    network = data.get("network", {})
    mempool = data.get("mempool", {})
    fees = data.get("fees_sat_vb", {})
    block = data.get("latest_block") or {}
    minimum_fee = _number(mempool.get("min_fee_btc_kvb"))
    sampled_at = int(data.get("generated_at") or time.time())

    values = (
        sampled_at,
        int(chain.get("blocks") or 0),
        _number(chain.get("verification_progress")),
        _number(chain.get("size_on_disk")),
        _number(network.get("connections")),
        _number(network.get("connections_in")),
        _number(network.get("connections_out")),
        _number(mempool.get("transactions")),
        _number(mempool.get("bytes")),
        _number(mempool.get("memory_usage")),
        round(float(minimum_fee) * 100_000, 3)
        if minimum_fee is not None
        else None,
        _number(fees.get("2")),
        _number(fees.get("6")),
        _number(fees.get("12")),
        _number(network.get("bytes_received")),
        _number(network.get("bytes_sent")),
        _number(block.get("txs")),
        (float(block["totalfee"]) / 100_000_000)
        if isinstance(block.get("totalfee"), (int, float))
        else None,
    )

    cutoff = sampled_at - HISTORY_RETENTION_DAYS * 24 * 60 * 60
    with closing(database_connection()) as connection:
        with connection:
            connection.execute(
                """
                INSERT OR REPLACE INTO node_samples (
                    sampled_at, blocks, verification_progress, size_on_disk,
                    connections, connections_in, connections_out,
                    mempool_transactions, mempool_bytes, mempool_memory_usage,
                    mempool_min_fee_sat_vb, fee_2_sat_vb, fee_6_sat_vb,
                    fee_12_sat_vb, bytes_received, bytes_sent,
                    block_transactions, block_total_fee_btc
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                values,
            )
            connection.execute(
                "DELETE FROM node_samples WHERE sampled_at < ?",
                (cutoff,),
            )


def history_data(range_name: str) -> dict[str, Any]:
    duration, bucket_seconds = HISTORY_RANGES.get(
        range_name, HISTORY_RANGES["24h"]
    )
    now = int(time.time())
    cutoff = now - duration
    init_database()
    with closing(database_connection()) as connection:
        rows = connection.execute(
            """
            SELECT
                CAST(sampled_at / ? AS INTEGER) * ? AS timestamp,
                MAX(blocks) AS blocks,
                AVG(connections) AS connections,
                AVG(connections_in) AS connections_in,
                AVG(connections_out) AS connections_out,
                AVG(mempool_transactions) AS mempool_transactions,
                AVG(mempool_bytes) AS mempool_bytes,
                AVG(mempool_min_fee_sat_vb) AS mempool_min_fee_sat_vb,
                AVG(fee_2_sat_vb) AS fee_2_sat_vb,
                AVG(fee_6_sat_vb) AS fee_6_sat_vb,
                AVG(fee_12_sat_vb) AS fee_12_sat_vb
            FROM node_samples
            WHERE sampled_at >= ?
            GROUP BY timestamp
            ORDER BY timestamp
            """,
            (bucket_seconds, bucket_seconds, cutoff),
        ).fetchall()

    return {
        "range": range_name if range_name in HISTORY_RANGES else "24h",
        "bucket_seconds": bucket_seconds,
        "generated_at": now,
        "points": [dict(row) for row in rows],
    }


def sampler_loop() -> None:
    initialized = False
    while True:
        started = time.monotonic()
        try:
            if not initialized:
                init_database()
                initialized = True
            store_snapshot(snapshot())
        except Exception as exc:
            print(f"History sample failed: {exc}", flush=True)
        elapsed = time.monotonic() - started
        time.sleep(max(1, SAMPLE_INTERVAL_SECONDS - elapsed))


class Handler(BaseHTTPRequestHandler):
    server_version = f"BitcoinDashboard/{__version__}"

    def send_bytes(self, body: bytes, content_type: str, status: int = 200) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'self'; style-src 'self' 'unsafe-inline'; "
            "script-src 'self' 'unsafe-inline'; connect-src 'self'; "
            "img-src 'self'; frame-ancestors 'none'",
        )
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path = parsed.path
        if path == "/api/dashboard":
            try:
                body = json.dumps(snapshot(), separators=(",", ":")).encode()
                self.send_bytes(body, "application/json; charset=utf-8")
            except Exception as exc:  # Return a controlled error, never a traceback.
                print(f"Dashboard request failed: {exc}", flush=True)
                body = b'{"error":"Node data unavailable"}'
                self.send_bytes(body, "application/json; charset=utf-8", 503)
            return
        if path == "/api/history":
            range_name = parse_qs(parsed.query).get("range", ["24h"])[0]
            try:
                body = json.dumps(
                    history_data(range_name), separators=(",", ":")
                ).encode()
                self.send_bytes(body, "application/json; charset=utf-8")
            except Exception as exc:
                print(f"History request failed: {exc}", flush=True)
                body = b'{"error":"History data unavailable"}'
                self.send_bytes(body, "application/json; charset=utf-8", 503)
            return
        if path == "/healthz":
            try:
                bitcoin_cli("getblockcount", timeout=5)
                self.send_bytes(b'{"status":"ok"}', "application/json", 200)
            except RpcError:
                self.send_bytes(b'{"status":"unavailable"}', "application/json", 503)
            return
        if path in ("/", "/index.html"):
            self.send_bytes(
                (STATIC_DIR / "index.html").read_bytes(),
                "text/html; charset=utf-8",
            )
            return
        self.send_error(HTTPStatus.NOT_FOUND)

    def log_message(self, fmt: str, *args: Any) -> None:
        print(f"{self.address_string()} - {fmt % args}", flush=True)


if __name__ == "__main__":
    history_thread = threading.Thread(
        target=sampler_loop,
        name="history-sampler",
        daemon=True,
    )
    history_thread.start()
    print(f"Bitcoin dashboard listening on http://{HOST}:{PORT}", flush=True)
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()
