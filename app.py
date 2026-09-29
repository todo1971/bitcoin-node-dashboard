#!/usr/bin/env python3
"""Small, read-only Bitcoin Core dashboard with no external dependencies."""

from __future__ import annotations

import json
import os
import re
import base64
import hashlib
import hmac
import platform
import secrets
import shutil
import socket
import sqlite3
import subprocess
import tempfile
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
__version__ = "1.8.1"
STARTED_AT = int(time.time())
STATIC_DIR = APP_DIR / "static"
HOST = os.getenv("DASHBOARD_HOST", "127.0.0.1")
PORT = int(os.getenv("DASHBOARD_PORT", "8787"))
CACHE_SECONDS = max(1, int(os.getenv("DASHBOARD_CACHE_SECONDS", "10")))
BITCOIN_CLI = os.getenv("BITCOIN_CLI", "/home/btc/bin/bitcoin-cli")
BITCOIN_RPC_URL = os.getenv("BITCOIN_RPC_URL", "").strip()
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
VERSION_CHECK_SECONDS = max(
    3600, int(os.getenv("VERSION_CHECK_SECONDS", "21600"))
)
ALERT_EMAIL = os.getenv("ALERT_EMAIL", "").strip()
ALERT_WEBHOOK_URL = os.getenv("ALERT_WEBHOOK_URL", "").strip()
ALERT_GRACE_SECONDS = max(60, int(os.getenv("ALERT_GRACE_SECONDS", "300")))
ALERT_NO_INBOUND_SECONDS = max(
    60, int(os.getenv("ALERT_NO_INBOUND_SECONDS", "900"))
)
ALERT_COOLDOWN_SECONDS = max(
    300, int(os.getenv("ALERT_COOLDOWN_SECONDS", "21600"))
)
SYNC_LAG_BLOCKS = max(1, int(os.getenv("SYNC_LAG_BLOCKS", "3")))
_legacy_disk_min_free = float(os.getenv("DISK_MIN_FREE_PERCENT", "10"))
DISK_MAX_USED_PERCENT = min(
    99.0,
    max(
        50.0,
        float(
            os.getenv(
                "DISK_MAX_USED_PERCENT",
                str(100.0 - _legacy_disk_min_free),
            )
        ),
    ),
)
MEMORY_MAX_USED_PERCENT = min(
    99.0, max(50.0, float(os.getenv("MEMORY_MAX_USED_PERCENT", "90")))
)
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "").strip()
ADMIN_UPDATES_ENABLED = os.getenv("ADMIN_UPDATES_ENABLED", "1").lower() not in (
    "0",
    "false",
    "no",
)
DASHBOARD_GITHUB_REPOSITORY = os.getenv(
    "DASHBOARD_GITHUB_REPOSITORY", "todo1971/bitcoin-node-dashboard"
).strip()
DASHBOARD_GITHUB_TOKEN = os.getenv("DASHBOARD_GITHUB_TOKEN", "").strip()
BITCOIN_UPLOAD_DIR = Path(
    os.getenv(
        "BITCOIN_UPLOAD_DIR", "/var/lib/bitcoin-dashboard/bitcoin-core-upload"
    )
)
BITCOIN_UPLOAD_MAX_BYTES = max(
    1_000_000, int(os.getenv("BITCOIN_UPLOAD_MAX_BYTES", str(200 * 1024 * 1024)))
)
ADMIN_CSRF_TOKEN = secrets.token_urlsafe(32)
ADMIN_MAX_FAILURES = 5
ADMIN_LOCK_SECONDS = 15 * 60
ADMIN_DASHBOARD_COMMAND = (
    "sudo",
    "-n",
    "/usr/bin/systemd-run",
    "--unit=bitcoin-dashboard-update",
    "--collect",
    "--no-block",
    "/usr/local/sbin/update-bitcoin-dashboard",
)
ADMIN_BITCOIN_COMMAND = (
    "sudo",
    "-n",
    "/usr/bin/systemd-run",
    "--unit=bitcoin-core-update",
    "--collect",
    "--no-block",
    "/usr/local/sbin/update-bitcoin-core",
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
_version_cache_lock = threading.Lock()
_version_cache: dict[str, Any] = {"expires": 0.0, "data": None}
_dashboard_version_cache_lock = threading.Lock()
_dashboard_version_cache: dict[str, Any] = {"expires": 0.0, "data": None}
_cpu_lock = threading.Lock()
_cpu_previous: tuple[int, int] | None = None
_admin_auth_lock = threading.Lock()
_admin_failures: list[float] = []
_admin_blocked_until = 0.0
_bitcoin_upload_lock = threading.Lock()


class RpcError(RuntimeError):
    pass


def bitcoin_cli(*args: str, timeout: int = 20) -> Any:
    if BITCOIN_RPC_URL:
        return bitcoin_json_rpc(*args, timeout=timeout)
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


def bitcoin_json_rpc(*args: str, timeout: int = 20) -> Any:
    if not args:
        raise RpcError("RPC method is missing")
    parsed_url = urlparse(BITCOIN_RPC_URL)
    if parsed_url.scheme not in ("http", "https") or not parsed_url.hostname:
        raise RpcError("BITCOIN_RPC_URL is invalid")
    try:
        credentials = Path(BITCOIN_COOKIE).read_text(encoding="utf-8").strip()
    except OSError as exc:
        raise RpcError(f"RPC cookie unavailable: {exc}") from exc
    if ":" not in credentials:
        raise RpcError("RPC cookie is invalid")
    params: list[Any] = []
    for value in args[1:]:
        try:
            params.append(json.loads(value))
        except json.JSONDecodeError:
            params.append(value)
    payload = json.dumps(
        {"jsonrpc": "2.0", "id": "dashboard", "method": args[0], "params": params},
        separators=(",", ":"),
    ).encode()
    authorization = base64.b64encode(credentials.encode()).decode()
    request = urllib.request.Request(
        BITCOIN_RPC_URL,
        data=payload,
        headers={
            "Authorization": f"Basic {authorization}",
            "Content-Type": "application/json",
            "User-Agent": f"BitcoinDashboard/{__version__}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            result = json.load(response)
    except (OSError, ValueError, urllib.error.URLError) as exc:
        raise RpcError(str(exc)) from exc
    if not isinstance(result, dict) or result.get("error"):
        raise RpcError(str(result.get("error") if isinstance(result, dict) else result))
    return result.get("result")


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


def version_tuple(value: str) -> tuple[int, ...]:
    match = re.search(r"(\d+(?:\.\d+)+)", value)
    if not match:
        return ()
    return tuple(int(part) for part in match.group(1).split("."))


def fetch_latest_core_version() -> dict[str, Any]:
    now = time.monotonic()
    with _version_cache_lock:
        if _version_cache["data"] is not None and now < _version_cache["expires"]:
            return _version_cache["data"]
        result: dict[str, Any] = {
            "available": False,
            "latest": None,
            "release_url": "https://bitcoincore.org/en/releases/",
        }
        try:
            request = urllib.request.Request(
                "https://bitcoincore.org/en/download/",
                headers={"User-Agent": "BitcoinDashboard/1.4"},
            )
            with urllib.request.urlopen(request, timeout=8) as response:
                page = response.read(1_000_000).decode("utf-8", "replace")
            match = re.search(
                r"Latest version:\s*</?[^>]*>*\s*(\d+\.\d+(?:\.\d+)?)",
                page,
                re.IGNORECASE,
            ) or re.search(
                r"Latest version:\s*(\d+\.\d+(?:\.\d+)?)",
                page,
                re.IGNORECASE,
            )
            if match:
                latest = match.group(1)
                result.update(
                    available=True,
                    latest=latest,
                    release_url=f"https://bitcoincore.org/en/releases/{latest}/",
                )
        except (OSError, ValueError, urllib.error.URLError):
            pass
        _version_cache.update(data=result, expires=now + VERSION_CHECK_SECONDS)
        return result


def fetch_latest_dashboard_version() -> dict[str, Any]:
    """Check the newest published GitHub release without exposing credentials."""
    now = time.monotonic()
    with _dashboard_version_cache_lock:
        if (
            _dashboard_version_cache["data"] is not None
            and now < _dashboard_version_cache["expires"]
        ):
            return _dashboard_version_cache["data"]
        result: dict[str, Any] = {
            "available": False,
            "current": __version__,
            "latest": None,
            "update_available": False,
            "release_url": f"https://github.com/{DASHBOARD_GITHUB_REPOSITORY}/releases",
        }
        if not re.fullmatch(
            r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", DASHBOARD_GITHUB_REPOSITORY
        ):
            result["error"] = "GitHub-Repository ist ungültig konfiguriert"
        else:
            try:
                headers = {
                    "Accept": "application/vnd.github+json",
                    "User-Agent": f"BitcoinDashboard/{__version__}",
                    "X-GitHub-Api-Version": "2022-11-28",
                }
                if DASHBOARD_GITHUB_TOKEN:
                    headers["Authorization"] = f"Bearer {DASHBOARD_GITHUB_TOKEN}"
                request = urllib.request.Request(
                    "https://api.github.com/repos/"
                    f"{DASHBOARD_GITHUB_REPOSITORY}/releases/latest",
                    headers=headers,
                )
                with urllib.request.urlopen(request, timeout=8) as response:
                    release = json.load(response)
                tag = str(release.get("tag_name") or "")
                latest_tuple = version_tuple(tag)
                current_tuple = version_tuple(__version__)
                if not latest_tuple:
                    raise ValueError("GitHub-Release besitzt keine gültige Version")
                latest = ".".join(str(part) for part in latest_tuple)
                result.update(
                    available=True,
                    latest=latest,
                    update_available=latest_tuple > current_tuple,
                    release_url=str(release.get("html_url") or result["release_url"]),
                )
            except (OSError, ValueError, json.JSONDecodeError, urllib.error.URLError):
                result["error"] = "GitHub-Release konnte nicht geprüft werden"
        _dashboard_version_cache.update(
            data=result, expires=now + VERSION_CHECK_SECONDS
        )
        return result


def cpu_percent() -> float | None:
    global _cpu_previous
    try:
        fields = Path("/proc/stat").read_text(encoding="utf-8").splitlines()[0].split()
        if fields[0] != "cpu":
            return None
        counters = [int(value) for value in fields[1:]]
        idle = counters[3] + (counters[4] if len(counters) > 4 else 0)
        total = sum(counters)
    except (OSError, ValueError, IndexError):
        return None
    with _cpu_lock:
        previous = _cpu_previous
        _cpu_previous = (total, idle)
    if previous is None:
        return None
    total_delta = total - previous[0]
    idle_delta = idle - previous[1]
    if total_delta <= 0:
        return None
    return round(100.0 * (1.0 - idle_delta / total_delta), 2)


def memory_stats() -> dict[str, int | float | None]:
    values: dict[str, int] = {}
    try:
        for line in Path("/proc/meminfo").read_text(encoding="utf-8").splitlines():
            key, raw = line.split(":", 1)
            values[key] = int(raw.strip().split()[0]) * 1024
    except (OSError, ValueError, IndexError):
        return {"total": None, "available": None, "used_percent": None}
    total = values.get("MemTotal")
    available = values.get("MemAvailable")
    used_percent = (
        round(100.0 * (total - available) / total, 2)
        if total and available is not None
        else None
    )
    return {"total": total, "available": available, "used_percent": used_percent}


def system_stats() -> dict[str, Any]:
    try:
        disk = shutil.disk_usage(BITCOIN_DATADIR)
        disk_free_percent = round(100.0 * disk.free / disk.total, 2)
        disk_values: dict[str, int | float | None] = {
            "total": disk.total,
            "used": disk.used,
            "free": disk.free,
            "free_percent": disk_free_percent,
        }
    except OSError:
        disk_values = {
            "total": None,
            "used": None,
            "free": None,
            "free_percent": None,
        }
    try:
        load = [round(value, 2) for value in os.getloadavg()]
    except (AttributeError, OSError):
        load = []
    return {
        "cpu_percent": cpu_percent(),
        "memory": memory_stats(),
        "disk": disk_values,
        "load_average": load,
        "dashboard_uptime": max(0, int(time.time()) - STARTED_AT),
    }


def build_snapshot() -> dict[str, Any]:
    chain = bitcoin_cli("getblockchaininfo")
    network = bitcoin_cli("getnetworkinfo")
    mempool = bitcoin_cli("getmempoolinfo")
    net_totals = bitcoin_cli("getnettotals")
    peers = bitcoin_cli("getpeerinfo")
    bitcoind_uptime = safe_call("uptime")
    latest_version = dict(fetch_latest_core_version())

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

    current_version = str(network.get("subversion") or "")
    current_tuple = version_tuple(current_version)
    latest_tuple = version_tuple(str(latest_version.get("latest") or ""))
    latest_version["current"] = current_version
    latest_version["update_available"] = bool(
        current_tuple and latest_tuple and current_tuple < latest_tuple
    )

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
            "bitcoind_uptime": bitcoind_uptime,
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
        "system": system_stats(),
        "version_check": latest_version,
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
                    block_total_fee_btc REAL,
                    cpu_percent REAL,
                    memory_used_percent REAL,
                    disk_free_percent REAL,
                    disk_free_bytes INTEGER,
                    bitcoind_uptime INTEGER
                )
                """
            )
            existing_columns = {
                row[1]
                for row in connection.execute(
                    "PRAGMA table_info(node_samples)"
                ).fetchall()
            }
            migrations = {
                "cpu_percent": "REAL",
                "memory_used_percent": "REAL",
                "disk_free_percent": "REAL",
                "disk_free_bytes": "INTEGER",
                "bitcoind_uptime": "INTEGER",
            }
            for column, data_type in migrations.items():
                if column not in existing_columns:
                    connection.execute(
                        f"ALTER TABLE node_samples ADD COLUMN {column} {data_type}"
                    )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS alert_states (
                    alert_key TEXT PRIMARY KEY,
                    first_seen INTEGER NOT NULL,
                    active INTEGER NOT NULL DEFAULT 0,
                    last_notified INTEGER,
                    message TEXT NOT NULL
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
    system = data.get("system", {})
    memory = system.get("memory", {})
    disk = system.get("disk", {})
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
        _number(system.get("cpu_percent")),
        _number(memory.get("used_percent")),
        _number(disk.get("free_percent")),
        _number(disk.get("free")),
        _number(network.get("bitcoind_uptime")),
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
                    block_transactions, block_total_fee_btc, cpu_percent,
                    memory_used_percent, disk_free_percent, disk_free_bytes,
                    bitcoind_uptime
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                AVG(fee_12_sat_vb) AS fee_12_sat_vb,
                AVG(cpu_percent) AS cpu_percent,
                AVG(memory_used_percent) AS memory_used_percent,
                AVG(disk_free_percent) AS disk_free_percent,
                100.0 - AVG(disk_free_percent) AS disk_used_percent
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


def deliver_notification(subject: str, message: str) -> None:
    print(f"ALERT: {subject}: {message}", flush=True)
    if ALERT_EMAIL and "\n" not in ALERT_EMAIL and "\r" not in ALERT_EMAIL:
        sendmail = shutil.which("sendmail") or "/usr/sbin/sendmail"
        if Path(sendmail).is_file():
            payload = (
                f"To: {ALERT_EMAIL}\n"
                f"Subject: [Bitcoin Node] {subject}\n"
                "Content-Type: text/plain; charset=utf-8\n"
                "Auto-Submitted: auto-generated\n\n"
                f"Host: {socket.gethostname()}\n{message}\n"
            )
            try:
                subprocess.run(
                    [sendmail, "-t", "-oi"],
                    input=payload,
                    text=True,
                    timeout=15,
                    check=False,
                )
            except (OSError, subprocess.TimeoutExpired):
                print("Alert email delivery failed", flush=True)
    if ALERT_WEBHOOK_URL.startswith("https://"):
        try:
            body = json.dumps(
                {
                    "subject": subject,
                    "message": message,
                    "host": socket.gethostname(),
                    "timestamp": int(time.time()),
                }
            ).encode()
            request = urllib.request.Request(
                ALERT_WEBHOOK_URL,
                data=body,
                headers={
                    "Content-Type": "application/json",
                    "User-Agent": "BitcoinDashboard/1.4",
                },
                method="POST",
            )
            with urllib.request.urlopen(request, timeout=10):
                pass
        except (OSError, ValueError, urllib.error.URLError):
            print("Alert webhook delivery failed", flush=True)


def set_alert_condition(
    alert_key: str,
    firing: bool,
    message: str,
    grace_seconds: int = ALERT_GRACE_SECONDS,
) -> None:
    now = int(time.time())
    notification: tuple[str, str] | None = None
    with closing(database_connection()) as connection:
        with connection:
            row = connection.execute(
                "SELECT * FROM alert_states WHERE alert_key = ?",
                (alert_key,),
            ).fetchone()
            if firing:
                if row is None:
                    connection.execute(
                        """
                        INSERT INTO alert_states
                            (alert_key, first_seen, active, last_notified, message)
                        VALUES (?, ?, 0, NULL, ?)
                        """,
                        (alert_key, now, message),
                    )
                elif not row["active"] and now - row["first_seen"] >= grace_seconds:
                    connection.execute(
                        """
                        UPDATE alert_states
                        SET active = 1, last_notified = ?, message = ?
                        WHERE alert_key = ?
                        """,
                        (now, message, alert_key),
                    )
                    notification = (f"Alarm: {alert_key}", message)
                elif row["active"]:
                    last_notified = row["last_notified"] or 0
                    connection.execute(
                        "UPDATE alert_states SET message = ? WHERE alert_key = ?",
                        (message, alert_key),
                    )
                    if now - last_notified >= ALERT_COOLDOWN_SECONDS:
                        connection.execute(
                            "UPDATE alert_states SET last_notified = ? WHERE alert_key = ?",
                            (now, alert_key),
                        )
                        notification = (f"Alarm weiterhin aktiv: {alert_key}", message)
            elif row is not None:
                if row["active"]:
                    notification = (
                        f"Entwarnung: {alert_key}",
                        f"Der Zustand ist wieder normal. Zuvor: {row['message']}",
                    )
                connection.execute(
                    "DELETE FROM alert_states WHERE alert_key = ?",
                    (alert_key,),
                )
    if notification:
        deliver_notification(*notification)


def evaluate_alerts(data: dict[str, Any]) -> None:
    chain = data.get("chain", {})
    network = data.get("network", {})
    system = data.get("system", {})
    disk = system.get("disk", {})
    memory = system.get("memory", {})
    external = data.get("external_node", {})
    version = data.get("version_check", {})

    set_alert_condition("node_rpc", False, "Bitcoin Core RPC ist erreichbar")
    blocks = int(chain.get("blocks") or 0)
    headers = int(chain.get("headers") or 0)
    lag = max(0, headers - blocks)
    syncing = bool(chain.get("initial_block_download")) or lag > SYNC_LAG_BLOCKS
    set_alert_condition(
        "sync_lag",
        syncing,
        f"Node liegt {lag} Blöcke zurück (Blocks {blocks}, Headers {headers})",
    )

    inbound = int(network.get("connections_in") or 0)
    set_alert_condition(
        "no_inbound_peers",
        inbound == 0,
        "Keine eingehenden Bitcoin-Peers verbunden",
        ALERT_NO_INBOUND_SECONDS,
    )

    disk_free = _number(disk.get("free_percent"))
    disk_used = 100.0 - disk_free if disk_free is not None else None
    set_alert_condition(
        "disk_space",
        disk_used is not None and disk_used >= DISK_MAX_USED_PERCENT,
        f"Datenträgerbelegung liegt bei {disk_used:.1f}%"
        if disk_used is not None
        else "Festplattenstatus unbekannt",
    )

    memory_used = _number(memory.get("used_percent"))
    set_alert_condition(
        "memory_pressure",
        memory_used is not None and memory_used > MEMORY_MAX_USED_PERCENT,
        f"RAM-Auslastung liegt bei {memory_used:.1f}%"
        if memory_used is not None
        else "RAM-Status unbekannt",
    )

    set_alert_condition(
        "external_unreachable",
        external.get("available") is True and external.get("reachable") is False,
        f"Öffentlicher P2P-Port {PUBLIC_NODE_ADDRESS}:{PUBLIC_NODE_PORT} ist extern nicht erreichbar",
        ALERT_NO_INBOUND_SECONDS,
    )
    set_alert_condition(
        "core_update",
        version.get("update_available") is True,
        f"Bitcoin Core {version.get('latest')} ist verfügbar; installiert ist {version.get('current')}",
        60,
    )


def active_alerts() -> list[dict[str, Any]]:
    init_database()
    with closing(database_connection()) as connection:
        rows = connection.execute(
            """
            SELECT alert_key, first_seen, last_notified, message
            FROM alert_states
            WHERE active = 1
            ORDER BY first_seen
            """
        ).fetchall()
    return [dict(row) for row in rows]


def decode_admin_credentials(header: str) -> tuple[str, str] | None:
    if not header.startswith("Basic ") or len(header) > 1024:
        return None
    try:
        decoded = base64.b64decode(header[6:], validate=True).decode("utf-8")
        username, password = decoded.split(":", 1)
    except (ValueError, UnicodeDecodeError):
        return None
    return username, password


def constant_time_equal(left: str, right: str) -> bool:
    return hmac.compare_digest(left.encode("utf-8"), right.encode("utf-8"))


def check_admin_auth(header: str) -> str:
    """Return ok, missing, failed, disabled, or locked."""
    global _admin_blocked_until
    if len(ADMIN_TOKEN) < 32:
        return "disabled"
    now = time.monotonic()
    with _admin_auth_lock:
        if now < _admin_blocked_until:
            return "locked"
    credentials = decode_admin_credentials(header)
    if credentials is None:
        return "missing" if not header else record_admin_failure(now)
    username, password = credentials
    valid = constant_time_equal(username, "admin") and constant_time_equal(
        password, ADMIN_TOKEN
    )
    if valid:
        with _admin_auth_lock:
            _admin_failures.clear()
        return "ok"
    return record_admin_failure(now)


def record_admin_failure(now: float | None = None) -> str:
    global _admin_blocked_until
    current = time.monotonic() if now is None else now
    with _admin_auth_lock:
        cutoff = current - ADMIN_LOCK_SECONDS
        _admin_failures[:] = [value for value in _admin_failures if value >= cutoff]
        _admin_failures.append(current)
        if len(_admin_failures) >= ADMIN_MAX_FAILURES:
            _admin_blocked_until = current + ADMIN_LOCK_SECONDS
            _admin_failures.clear()
            return "locked"
    return "failed"


def admin_origin_allowed(headers: Any) -> bool:
    fetch_site = headers.get("Sec-Fetch-Site", "")
    if fetch_site and fetch_site not in ("same-origin", "none"):
        return False
    origin = headers.get("Origin", "")
    if not origin:
        return True
    parsed = urlparse(origin)
    return parsed.scheme in ("http", "https") and constant_time_equal(
        parsed.netloc, headers.get("Host", "")
    )


def bitcoin_platform_name() -> str | None:
    machine = platform.machine().lower()
    if machine in ("x86_64", "amd64"):
        return "x86_64-linux-gnu"
    if machine in ("aarch64", "arm64"):
        return "aarch64-linux-gnu"
    return None


def parse_bitcoin_archive_name(filename: str) -> tuple[str, str] | None:
    match = re.fullmatch(
        r"bitcoin-(\d+\.\d+(?:\.\d+)?)-(x86_64-linux-gnu|aarch64-linux-gnu)\.tar\.gz",
        filename,
    )
    return (match.group(1), match.group(2)) if match else None


def bitcoin_upload_status() -> dict[str, Any] | None:
    metadata_path = BITCOIN_UPLOAD_DIR / "metadata.json"
    archive_path = BITCOIN_UPLOAD_DIR / "bitcoin-core-upload.tar.gz"
    try:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        if not archive_path.is_file() or not isinstance(metadata, dict):
            return None
        filename = str(metadata.get("filename") or "")
        parsed = parse_bitcoin_archive_name(filename)
        if not parsed or archive_path.stat().st_size != metadata.get("size"):
            return None
        return {
            "filename": filename,
            "version": parsed[0],
            "platform": parsed[1],
            "size": metadata["size"],
            "sha256": metadata.get("sha256"),
            "uploaded_at": metadata.get("uploaded_at"),
        }
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        return None


def save_bitcoin_upload(stream: Any, filename: str, content_length: int) -> dict[str, Any]:
    parsed = parse_bitcoin_archive_name(filename)
    if not parsed:
        raise ValueError(
            "Erwartet wird bitcoin-VERSION-x86_64-linux-gnu.tar.gz "
            "oder bitcoin-VERSION-aarch64-linux-gnu.tar.gz"
        )
    version, archive_platform = parsed
    expected_platform = bitcoin_platform_name()
    if expected_platform is None or archive_platform != expected_platform:
        raise ValueError(
            f"Archivplattform {archive_platform} passt nicht zu "
            f"{expected_platform or platform.machine()}"
        )
    if not 1 <= content_length <= BITCOIN_UPLOAD_MAX_BYTES:
        raise ValueError("Uploadgröße ist ungültig oder überschreitet das Limit")

    BITCOIN_UPLOAD_DIR.mkdir(mode=0o750, parents=True, exist_ok=True)
    archive_path = BITCOIN_UPLOAD_DIR / "bitcoin-core-upload.tar.gz"
    metadata_path = BITCOIN_UPLOAD_DIR / "metadata.json"
    temporary_path: Path | None = None
    with _bitcoin_upload_lock:
        try:
            digest = hashlib.sha256()
            remaining = content_length
            first_bytes = b""
            with tempfile.NamedTemporaryFile(
                dir=BITCOIN_UPLOAD_DIR, prefix="upload-", delete=False
            ) as handle:
                temporary_path = Path(handle.name)
                while remaining:
                    chunk = stream.read(min(1024 * 1024, remaining))
                    if not chunk:
                        raise ValueError("Upload wurde vorzeitig abgebrochen")
                    if len(first_bytes) < 2:
                        first_bytes += chunk[: 2 - len(first_bytes)]
                    handle.write(chunk)
                    digest.update(chunk)
                    remaining -= len(chunk)
                handle.flush()
                os.fsync(handle.fileno())
            if first_bytes != b"\x1f\x8b":
                raise ValueError("Die hochgeladene Datei ist kein gzip-Archiv")
            os.chmod(temporary_path, 0o600)
            os.replace(temporary_path, archive_path)
            temporary_path = None
            metadata = {
                "filename": filename,
                "version": version,
                "platform": archive_platform,
                "size": content_length,
                "sha256": digest.hexdigest(),
                "uploaded_at": int(time.time()),
            }
            metadata_tmp = metadata_path.with_suffix(".tmp")
            metadata_tmp.write_text(
                json.dumps(metadata, separators=(",", ":")), encoding="utf-8"
            )
            os.chmod(metadata_tmp, 0o600)
            os.replace(metadata_tmp, metadata_path)
            return metadata
        finally:
            if temporary_path is not None:
                temporary_path.unlink(missing_ok=True)


def admin_status_data() -> dict[str, Any]:
    network = safe_call("getnetworkinfo")
    bitcoin_version = (
        network.get("subversion")
        if isinstance(network, dict)
        else "Bitcoin Core nicht erreichbar"
    )
    return {
        "dashboard": fetch_latest_dashboard_version(),
        "bitcoin": bitcoin_version,
        "bitcoin_upload": bitcoin_upload_status(),
        "bitcoin_keyring_ready": Path(
            "/usr/local/share/bitcoin-core/trustedkeys.gpg"
        ).is_file(),
        "updates_enabled": ADMIN_UPDATES_ENABLED,
        "admin_enabled": len(ADMIN_TOKEN) >= 32,
    }


def start_admin_update(kind: str) -> tuple[int, str]:
    if not ADMIN_UPDATES_ENABLED:
        return 409, "Updates werden in dieser Installation extern verwaltet"
    command = {
        "dashboard": ADMIN_DASHBOARD_COMMAND,
        "bitcoin": ADMIN_BITCOIN_COMMAND,
    }.get(kind)
    if command is None:
        return 404, "Unbekannte Update-Aktion"
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return 500, str(exc)
    output = (result.stdout + result.stderr).strip()
    if result.returncode != 0:
        return 500, output[-4000:] or "Update-Auftrag konnte nicht gestartet werden"
    return 202, (
        "Update-Auftrag wurde isoliert gestartet. Status prüfen mit: "
        f"journalctl -u {'bitcoin-dashboard-update' if kind == 'dashboard' else 'bitcoin-core-update'} -f"
    )


def sampler_loop() -> None:
    initialized = False
    while True:
        started = time.monotonic()
        try:
            if not initialized:
                init_database()
                initialized = True
        except Exception as exc:
            print(f"Database initialization failed: {exc}", flush=True)
        try:
            data = snapshot()
        except Exception as exc:
            print(f"Node snapshot failed: {exc}", flush=True)
            try:
                set_alert_condition(
                    "node_rpc",
                    True,
                    f"Bitcoin Core RPC ist nicht erreichbar: {str(exc)[:300]}",
                )
            except Exception as alert_exc:
                print(f"Node outage alert failed: {alert_exc}", flush=True)
        else:
            try:
                store_snapshot(data)
                evaluate_alerts(data)
            except Exception as exc:
                print(f"Sample processing failed: {exc}", flush=True)
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
        self.send_header("Cross-Origin-Opener-Policy", "same-origin")
        self.send_header("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'self'; style-src 'self' 'unsafe-inline'; "
            "script-src 'self' 'unsafe-inline'; connect-src 'self'; "
            "img-src 'self'; frame-ancestors 'none'",
        )
        self.end_headers()
        self.wfile.write(body)

    def require_admin_auth(self) -> bool:
        result = check_admin_auth(self.headers.get("Authorization", ""))
        if result == "ok":
            return True
        if result == "disabled":
            self.send_bytes(
                b'{"error":"Administration is not configured"}',
                "application/json; charset=utf-8",
                503,
            )
            return False
        if result == "locked":
            self.send_bytes(
                b'{"error":"Too many failed authentication attempts"}',
                "application/json; charset=utf-8",
                429,
            )
            return False
        self.send_response(HTTPStatus.UNAUTHORIZED)
        self.send_header("WWW-Authenticate", 'Basic realm="Bitcoin maintenance"')
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", "0")
        self.end_headers()
        return False

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path = parsed.path
        if path in ("/admin", "/admin/"):
            if not self.require_admin_auth():
                return
            page = (STATIC_DIR / "admin.html").read_text(encoding="utf-8")
            body = page.replace("__CSRF_TOKEN__", ADMIN_CSRF_TOKEN).encode()
            self.send_bytes(body, "text/html; charset=utf-8")
            return
        if path == "/api/admin/status":
            if not self.require_admin_auth():
                return
            body = json.dumps(admin_status_data(), separators=(",", ":")).encode()
            self.send_bytes(body, "application/json; charset=utf-8")
            return
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
        if path == "/api/alerts":
            try:
                body = json.dumps(
                    {"alerts": active_alerts()}, separators=(",", ":")
                ).encode()
                self.send_bytes(body, "application/json; charset=utf-8")
            except Exception as exc:
                print(f"Alert request failed: {exc}", flush=True)
                body = b'{"error":"Alert data unavailable"}'
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

    def do_POST(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path not in (
            "/api/admin/update/dashboard",
            "/api/admin/update/bitcoin",
            "/api/admin/upload/bitcoin",
        ):
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        if not self.require_admin_auth():
            return
        if not admin_origin_allowed(self.headers):
            self.send_bytes(
                b'{"error":"Cross-origin request rejected"}',
                "application/json; charset=utf-8",
                403,
            )
            return
        content_type = self.headers.get("Content-Type", "").split(";", 1)[0]
        try:
            content_length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            content_length = -1
        if path == "/api/admin/upload/bitcoin":
            if not ADMIN_UPDATES_ENABLED:
                self.send_bytes(
                    b'{"error":"Updates are managed externally"}',
                    "application/json; charset=utf-8",
                    409,
                )
                return
            supplied_csrf = self.headers.get("X-CSRF-Token", "")
            if not constant_time_equal(supplied_csrf, ADMIN_CSRF_TOKEN):
                self.send_bytes(
                    b'{"error":"CSRF validation failed"}',
                    "application/json; charset=utf-8",
                    403,
                )
                return
            if content_type not in ("application/gzip", "application/octet-stream"):
                self.send_bytes(
                    b'{"error":"Only gzip archives are accepted"}',
                    "application/json; charset=utf-8",
                    415,
                )
                return
            filename = self.headers.get("X-File-Name", "")
            try:
                metadata = save_bitcoin_upload(
                    self.rfile, filename, content_length
                )
            except ValueError as exc:
                body = json.dumps(
                    {"error": str(exc)}, separators=(",", ":")
                ).encode()
                self.send_bytes(body, "application/json; charset=utf-8", 400)
                return
            except OSError as exc:
                print(f"Bitcoin Core upload failed: {exc}", flush=True)
                self.send_bytes(
                    b'{"error":"Upload could not be stored"}',
                    "application/json; charset=utf-8",
                    500,
                )
                return
            body = json.dumps(
                {"ok": True, "upload": metadata}, separators=(",", ":")
            ).encode()
            self.send_bytes(body, "application/json; charset=utf-8", 201)
            return
        if content_type != "application/x-www-form-urlencoded" or not (
            1 <= content_length <= 1024
        ):
            self.send_bytes(
                b'{"error":"Invalid request body"}',
                "application/json; charset=utf-8",
                400,
            )
            return
        try:
            values = parse_qs(
                self.rfile.read(content_length).decode("utf-8", "replace"),
                keep_blank_values=True,
                max_num_fields=4,
            )
        except ValueError:
            self.send_bytes(
                b'{"error":"Invalid form data"}',
                "application/json; charset=utf-8",
                400,
            )
            return
        supplied_csrf = values.get("csrf", [""])[0]
        if not constant_time_equal(supplied_csrf, ADMIN_CSRF_TOKEN):
            self.send_bytes(
                b'{"error":"CSRF validation failed"}',
                "application/json; charset=utf-8",
                403,
            )
            return
        kind = "dashboard" if path.endswith("/dashboard") else "bitcoin"
        status, output = start_admin_update(kind)
        body = json.dumps(
            {"ok": status == 202, "output": output}, separators=(",", ":")
        ).encode()
        self.send_bytes(body, "application/json; charset=utf-8", status)

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
