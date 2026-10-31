#!/usr/bin/env python3
# Copyright (C) 2026 Hardy (todo1971)
# SPDX-License-Identifier: GPL-3.0-only
"""Small, read-only Bitcoin Core dashboard with optional ZMQ support."""

from __future__ import annotations

import json
import os
import re
import base64
import hashlib
import hmac
import ipaddress
import math
import platform
import secrets
import shlex
import shutil
import socket
import sqlite3
import subprocess
import tempfile
import threading
import time
import urllib.error
import urllib.request
from collections import Counter, deque
from contextlib import closing
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from statistics import median
from typing import Any
from urllib.parse import parse_qs, urlparse


APP_DIR = Path(__file__).resolve().parent
__version__ = "1.18.4"
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
MEMPOOL_ANALYSIS_SECONDS = max(
    60, int(os.getenv("MEMPOOL_ANALYSIS_SECONDS", "300"))
)
UTXO_SAMPLE_SECONDS = max(
    3600, int(os.getenv("UTXO_SAMPLE_SECONDS", "86400"))
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
ZMQ_SEQUENCE_ENDPOINT = os.getenv("ZMQ_SEQUENCE_ENDPOINT", "").strip()
CONFIG_FILE = Path(os.getenv("DASHBOARD_CONFIG_FILE", "/var/lib/bitcoin-dashboard/.env"))
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
ADMIN_CONFIG_RESTART_COMMAND = (
    "sudo", "-n", "/usr/bin/systemd-run",
    "--unit=bitcoin-dashboard-config-restart", "--collect", "--no-block",
    "--on-active=2s", "/usr/bin/systemctl", "restart", "bitcoin-dashboard.service",
)
CONFIG_FIELDS = (
    ("PUBLIC_NODE_ADDRESS", "Öffentliche Node-Adresse", "Node", "address"),
    ("PUBLIC_NODE_PORT", "P2P-Port", "Node", "port"),
    ("ZMQ_SEQUENCE_ENDPOINT", "Lokaler ZMQ-Endpunkt", "Node", "zmq"),
    ("DASHBOARD_CACHE_SECONDS", "Dashboard-Cache (Sekunden)", "Erfassung", "cache"),
    ("SAMPLE_INTERVAL_SECONDS", "Messintervall (Sekunden)", "Erfassung", "sample"),
    ("HISTORY_RETENTION_DAYS", "Aufbewahrung (Tage)", "Erfassung", "retention"),
    ("MEMPOOL_ANALYSIS_SECONDS", "Mempool-Analyse (Sekunden)", "Erfassung", "analysis"),
    ("UTXO_SAMPLE_SECONDS", "UTXO-Messung (Sekunden)", "Erfassung", "utxo"),
    ("EXTERNAL_CACHE_SECONDS", "Externe Prüfung (Sekunden)", "Erfassung", "external"),
    ("VERSION_CHECK_SECONDS", "Versionsprüfung (Sekunden)", "Erfassung", "version"),
    ("ALERT_EMAIL", "Alarm-E-Mail", "Alarme", "email"),
    ("ALERT_WEBHOOK_URL", "HTTPS-Webhook", "Alarme", "webhook"),
    ("ALERT_GRACE_SECONDS", "Alarm-Karenz (Sekunden)", "Alarme", "grace"),
    ("ALERT_NO_INBOUND_SECONDS", "Ohne Inbound (Sekunden)", "Alarme", "inbound"),
    ("ALERT_COOLDOWN_SECONDS", "Wiederholsperre (Sekunden)", "Alarme", "cooldown"),
    ("SYNC_LAG_BLOCKS", "Sync-Rückstand (Blöcke)", "Alarme", "lag"),
    ("DISK_MAX_USED_PERCENT", "Datenträger-Alarm (%)", "Alarme", "percent"),
    ("MEMORY_MAX_USED_PERCENT", "RAM-Alarm (%)", "Alarme", "percent"),
    ("DASHBOARD_GITHUB_REPOSITORY", "GitHub-Repository", "Updates", "repository"),
    ("DASHBOARD_GITHUB_TOKEN", "GitHub-Token (leer lassen = unverändert)", "Updates", "secret"),
)
CONFIG_FIELD_KINDS = {key: kind for key, _, _, kind in CONFIG_FIELDS}
CONFIG_NUMERIC_RANGES = {
    "port": (1, 65535), "cache": (1, 3600), "sample": (30, 3600),
    "retention": (1, 3650), "analysis": (60, 86400),
    "utxo": (3600, 604800), "external": (60, 86400),
    "version": (3600, 604800), "grace": (60, 86400),
    "inbound": (60, 86400), "cooldown": (300, 604800),
    "lag": (1, 1000), "percent": (50, 99),
}
ADMIN_LOG_COMMANDS = {
    kind: (
        "sudo", "-n", "/usr/bin/journalctl", f"--unit={unit}",
        "--lines=80", "--no-pager", "--output=short-iso", "--quiet",
    )
    for kind, unit in (
        ("dashboard", "bitcoin-dashboard-update"),
        ("bitcoin", "bitcoin-core-update"),
    )
}

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
_chain_tips_cache_lock = threading.Lock()
_chain_tips_cache: dict[str, Any] = {"expires": 0.0, "data": None}
_dashboard_version_cache_lock = threading.Lock()
_dashboard_version_cache: dict[str, Any] = {"expires": 0.0, "data": None}
_cpu_lock = threading.Lock()
_cpu_previous: tuple[int, int] | None = None
_admin_auth_lock = threading.Lock()
_config_lock = threading.Lock()
_admin_failures: list[float] = []
_admin_blocked_until = 0.0
_bitcoin_upload_lock = threading.Lock()
_mempool_analysis_lock = threading.Lock()
_mempool_analysis_cache: dict[str, Any] = {"expires": 0.0, "data": None}
_utxo_last_attempt = 0
_block_interval_lock = threading.Lock()
_block_interval_cache: dict[str, Any] = {"height": None, "seconds": None}
_peer_observation_lock = threading.Lock()
_peer_observation: dict[str, Any] = {
    "active": None,
    "uptime": None,
    "observed_at": None,
    "departures": deque(),
}
_realtime_lock = threading.Lock()
_realtime: dict[str, Any] = {
    "state": "disabled" if not ZMQ_SEQUENCE_ENDPOINT else "starting",
    "last_event_at": None,
    "last_transport_sequence": None,
    "gaps_since_start": 0,
    "pending": {},
}
_event_condition = threading.Condition()
_event_serial = 0
_event_kind = "sample"
_sse_slots = threading.BoundedSemaphore(12)
_backfill_lock = threading.Lock()
_ZMQ_COUNTERS = ("block_connected", "block_disconnected", "mempool_added", "mempool_removed", "gaps")


def publish_browser_event(kind: str) -> None:
    global _event_serial, _event_kind
    with _event_condition:
        _event_serial += 1
        _event_kind = kind
        _event_condition.notify_all()


def process_zmq_frames(frames: list[bytes], now: int | None = None) -> tuple[str, bool]:
    """Count Core's sequence events; hashes are deliberately not retained."""
    if len(frames) != 3 or frames[0] != b"sequence" or len(frames[2]) != 4:
        raise ValueError("Invalid ZMQ sequence frames")
    body = frames[1]
    code = body[32:33]
    mapping = {b"C": "block_connected", b"D": "block_disconnected", b"A": "mempool_added", b"R": "mempool_removed"}
    if code not in mapping or len(body) != (41 if code in (b"A", b"R") else 33):
        raise ValueError("Invalid ZMQ sequence body")
    sequence = int.from_bytes(frames[2], "little")
    timestamp = int(time.time() if now is None else now)
    minute = timestamp - timestamp % 60
    with _realtime_lock:
        previous = _realtime["last_transport_sequence"]
        gap = previous is not None and sequence != ((previous + 1) & 0xffffffff)
        counts = _realtime["pending"].setdefault(minute, {key: 0 for key in _ZMQ_COUNTERS})
        counts[mapping[code]] += 1
        if gap:
            counts["gaps"] += 1
            _realtime["gaps_since_start"] += 1
        _realtime["last_transport_sequence"] = sequence
        _realtime["last_event_at"] = timestamp
        _realtime["state"] = "active"
    return mapping[code], gap


def flush_zmq_counts() -> None:
    with _realtime_lock:
        pending = _realtime["pending"]
        _realtime["pending"] = {}
    if not pending:
        return
    try:
        with closing(database_connection()) as connection:
            with connection:
                for minute, counts in pending.items():
                    connection.execute(
                        "INSERT INTO zmq_events VALUES (?, ?, ?, ?, ?, ?) "
                        "ON CONFLICT(minute) DO UPDATE SET "
                        + ", ".join(f"{key}={key}+excluded.{key}" for key in _ZMQ_COUNTERS),
                        (minute, *(counts[key] for key in _ZMQ_COUNTERS)),
                    )
                connection.execute(
                    "DELETE FROM zmq_events WHERE minute < ?",
                    (int(time.time()) - HISTORY_RETENTION_DAYS * 86400,),
                )
    except Exception:
        with _realtime_lock:
            for minute, counts in pending.items():
                current = _realtime["pending"].setdefault(minute, {key: 0 for key in _ZMQ_COUNTERS})
                for key in _ZMQ_COUNTERS:
                    current[key] += counts[key]
        raise


def realtime_data() -> dict[str, Any]:
    minute = int(time.time()) // 60 * 60
    with _realtime_lock:
        state = _realtime["state"]
        last_event_at = _realtime["last_event_at"]
        gaps_since_start = _realtime["gaps_since_start"]
        pending = dict(_realtime["pending"].get(minute, {}))
    stored = {key: 0 for key in _ZMQ_COUNTERS}
    try:
        with closing(database_connection()) as connection:
            row = connection.execute("SELECT * FROM zmq_events WHERE minute = ?", (minute,)).fetchone()
            if row is not None:
                stored = {key: row[key] for key in _ZMQ_COUNTERS}
    except sqlite3.Error:
        pass
    return {
        "state": state,
        "minute": minute,
        "last_event_at": last_event_at,
        "gaps_since_start": gaps_since_start,
        "counts": {key: stored[key] + pending.get(key, 0) for key in _ZMQ_COUNTERS},
    }


def zmq_listener_loop() -> None:
    try:
        import zmq
    except ImportError:
        with _realtime_lock:
            _realtime["state"] = "missing_dependency"
        print("ZMQ disabled: install python3-zmq", flush=True)
        return
    while True:
        context = zmq.Context()
        socket = context.socket(zmq.SUB)
        try:
            socket.setsockopt(zmq.SUBSCRIBE, b"sequence")
            socket.setsockopt(zmq.RCVTIMEO, 1000)
            socket.setsockopt(zmq.LINGER, 0)
            socket.connect(ZMQ_SEQUENCE_ENDPOINT)
            with _realtime_lock:
                _realtime["state"] = "waiting"
                _realtime["last_transport_sequence"] = None
            last_flush = time.monotonic()
            last_publish = 0.0
            while True:
                try:
                    frames = socket.recv_multipart()
                except zmq.Again:
                    frames = None
                if frames is not None:
                    try:
                        kind, gap = process_zmq_frames(frames)
                    except ValueError as exc:
                        print(f"Invalid ZMQ event: {exc}", flush=True)
                    else:
                        try:
                            if gap:
                                record_event("zmq_gap", "ZMQ-Sequenzlücke: Live-Ereignisse können fehlen")
                            if kind == "block_connected":
                                record_event("block_connected", "Neuer Block über ZMQ gemeldet")
                            elif kind == "block_disconnected":
                                record_event("block_disconnected", "Block getrennt; mögliche Reorganisation")
                        except (OSError, sqlite3.Error) as exc:
                            print(f"ZMQ event history unavailable: {exc}", flush=True)
                        now = time.monotonic()
                        if gap or now - last_publish >= (1 if kind.startswith("block_") else 3):
                            with _cache_lock:
                                _cache["expires"] = 0
                            publish_browser_event("resync" if gap else "block" if kind.startswith("block_") else "mempool")
                            last_publish = now
                if time.monotonic() - last_flush >= 5:
                    flush_zmq_counts()
                    last_flush = time.monotonic()
        except Exception as exc:
            with _realtime_lock:
                _realtime["state"] = "error"
                _realtime["last_transport_sequence"] = None
            try:
                record_event("zmq_interrupted", "ZMQ-Verbindung unterbrochen; Live-Daten können fehlen")
            except (OSError, sqlite3.Error):
                pass
            print(f"ZMQ listener error: {exc}", flush=True)
            time.sleep(5)
        finally:
            socket.close(0)
            context.term()


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


def block_interval_seconds(height: int, block_stats: Any) -> int | None:
    """Return the interval to the previous block without failing snapshots."""
    if height < 2 or not isinstance(block_stats, dict):
        return None
    with _block_interval_lock:
        if _block_interval_cache["height"] == height:
            return _block_interval_cache["seconds"]
    current_time = _number(block_stats.get("time"))
    previous = safe_call("getblockstats", str(height - 1), "[\"time\"]")
    previous_time = _number(previous.get("time")) if isinstance(previous, dict) else None
    if current_time is None or previous_time is None:
        return None
    seconds = max(1, int(current_time - previous_time))
    with _block_interval_lock:
        _block_interval_cache.update(height=height, seconds=seconds)
    return seconds


def summarize_mempool(entries: Any) -> dict[str, Any]:
    """Summarize verbose getrawmempool data without retaining transaction IDs."""
    fee_ranges = ((0, 1), (1, 2), (2, 5), (5, 10), (10, 20), (20, 50), (50, None))
    fee_buckets = [
        {"min_sat_vb": low, "max_sat_vb": high, "transactions": 0, "vbytes": 0}
        for low, high in fee_ranges
    ]
    if not isinstance(entries, dict):
        return {
            "available": False,
            "transactions": 0,
            "clusters": 0,
            "package_transactions": 0,
            "cpfp_transactions": 0,
            "rbf_transactions": 0,
            "rbf_replaceable_transactions": 0,
            "standalone_transactions": 0,
            "fee_buckets": fee_buckets,
            "unclassified_transactions": 0,
            "classified_vbytes": 0,
        }
    transaction_ids = set(entries)
    graph: dict[str, set[str]] = {txid: set() for txid in transaction_ids}
    rbf = 0
    cpfp = 0
    unclassified = 0
    classified_vbytes = 0
    package_transactions: set[str] = set()
    for txid, entry in entries.items():
        if not isinstance(entry, dict):
            unclassified += 1
            continue
        rate = mempool_entry_fee_rate(entry)
        vsize = _number(entry.get("vsize"))
        if rate is None or not math.isfinite(rate) or rate < 0 or vsize is None or not math.isfinite(vsize) or vsize <= 0:
            unclassified += 1
        else:
            for bucket in fee_buckets:
                if rate >= bucket["min_sat_vb"] and (bucket["max_sat_vb"] is None or rate < bucket["max_sat_vb"]):
                    bucket["transactions"] += 1
                    bucket["vbytes"] += int(vsize)
                    classified_vbytes += int(vsize)
                    break
        if entry.get("bip125-replaceable") is True:
            rbf += 1
        dependencies = entry.get("depends") or []
        child_rate = mempool_entry_fee_rate(entry)
        parent_rates = [
            mempool_entry_fee_rate(entries[parent])
            for parent in dependencies
            if parent in entries and isinstance(entries[parent], dict)
        ]
        if (
            dependencies
            and child_rate is not None
            and any(rate is not None and child_rate > rate for rate in parent_rates)
        ):
            cpfp += 1
        relatives = list(dependencies) + list(entry.get("spentby") or [])
        for relative in relatives:
            if relative in transaction_ids:
                graph[txid].add(relative)
                graph[relative].add(txid)
                package_transactions.update((txid, relative))

    visited: set[str] = set()
    clusters = 0
    for txid in transaction_ids:
        if txid in visited or not graph[txid]:
            continue
        clusters += 1
        pending = [txid]
        while pending:
            current = pending.pop()
            if current in visited:
                continue
            visited.add(current)
            pending.extend(graph[current] - visited)
    total = len(transaction_ids)
    return {
        "available": True,
        "transactions": total,
        "clusters": clusters,
        "package_transactions": len(package_transactions),
        "cpfp_transactions": cpfp,
        "rbf_transactions": rbf,
        "rbf_replaceable_transactions": rbf,
        "standalone_transactions": total - len(package_transactions),
        "fee_buckets": fee_buckets,
        "unclassified_transactions": unclassified,
        "classified_vbytes": classified_vbytes,
    }


def mempool_entry_fee_rate(entry: dict[str, Any]) -> float | None:
    vsize = _number(entry.get("vsize"))
    fees = entry.get("fees")
    base_fee = _number(fees.get("base")) if isinstance(fees, dict) else None
    if not vsize or base_fee is None:
        return None
    return float(base_fee) * 100_000_000 / float(vsize)


def mempool_analysis() -> dict[str, Any]:
    now = time.monotonic()
    with _mempool_analysis_lock:
        cached = _mempool_analysis_cache.get("data")
        if cached is not None and now < _mempool_analysis_cache["expires"]:
            return cached
        entries = safe_call("getrawmempool", "true")
        result = summarize_mempool(entries)
        result["generated_at"] = int(time.time())
        _mempool_analysis_cache.update(
            data=result, expires=now + MEMPOOL_ANALYSIS_SECONDS
        )
        return result


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
            "found": None,
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
            if not isinstance(payload, dict):
                raise ValueError("Invalid external node response")
            details = payload.get("data")
            if not isinstance(details, list):
                details = []
            found = payload.get("found") if isinstance(payload.get("found"), bool) else None
            status = payload.get("status")
            reachable = status == "UP" if found is True and status in ("UP", "DOWN") else None
            result.update(
                available=True,
                reachable=reachable,
                found=found,
                status=status,
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


def parse_global_ipv6_addresses(interface_data: str) -> list[str]:
    """Read globally scoped interface IPs without treating them as P2P listeners."""
    addresses: list[str] = []
    for line in interface_data.splitlines():
        fields = line.split()
        if len(fields) < 6 or fields[3] != "00":
            continue
        try:
            if len(fields[0]) != 32:
                continue
            address = ipaddress.IPv6Address(int(fields[0], 16))
        except ValueError:
            continue
        if address.is_global and str(address) not in addresses:
            addresses.append(str(address))
    return addresses


def host_global_ipv6_addresses() -> list[str]:
    try:
        return parse_global_ipv6_addresses(
            Path("/proc/net/if_inet6").read_text(encoding="ascii")
        )
    except OSError:
        return []


def _finite_number(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if 0 <= number < float("inf") else None


def observe_peer_departures(
    peers: list[dict[str, Any]], uptime: Any, now: int
) -> dict[str, int] | None:
    """Count observed ended connections, never infer a disconnection cause."""
    current_uptime = _finite_number(uptime)
    if current_uptime is None:
        return None
    active: dict[tuple[int, int], str] = {}
    for peer in peers:
        if peer.get("connection_type") in ("feeler", "addr-fetch", "private-broadcast"):
            continue
        if not isinstance(peer.get("id"), int) or not isinstance(peer.get("conntime"), int):
            continue
        active[(peer["id"], peer["conntime"])] = str(peer.get("network", "unknown"))
    with _peer_observation_lock:
        previous = _peer_observation["active"]
        previous_uptime = _peer_observation["uptime"]
        previous_at = _peer_observation["observed_at"]
        events = _peer_observation["departures"]
        elapsed = now - previous_at if previous_at is not None else 0
        if previous_uptime is not None and (
            elapsed < 0 or current_uptime < previous_uptime
            or current_uptime + 30 < previous_uptime + elapsed
        ):
            events.clear()  # bitcoind restarted: no false mass-disconnect alarm.
            previous = None
        if previous is not None:
            for key, network in previous.items():
                if key not in active:
                    events.append((now, network))
        cutoff = now - 3600
        while events and events[0][0] < cutoff:
            events.popleft()
        _peer_observation["active"] = active
        _peer_observation["uptime"] = current_uptime
        _peer_observation["observed_at"] = now
        return dict(Counter(network for _, network in events))


def peer_quality_summary(
    peers: list[dict[str, Any]], now: int, departures: dict[str, int] | None
) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for network in ("ipv4", "ipv6", "onion"):
        selected = [peer for peer in peers if peer.get("network") == network]
        durations = [
            max(0, now - int(value))
            for peer in selected
            if (value := _finite_number(peer.get("conntime"))) is not None
            and value <= now
        ]
        pings = [
            value * 1000
            for peer in selected
            if (value := _finite_number(peer.get("pingtime"))) is not None
        ]
        versions = Counter(
            peer["version"]
            for peer in selected
            if isinstance(peer.get("version"), int)
        )
        result[network] = {
            "count": len(selected),
            "median_connection_seconds": int(median(durations)) if durations else None,
            "median_ping_ms": round(median(pings), 1) if pings else None,
            "protocol_version": versions.most_common(1)[0][0] if versions else None,
            "transport_v2": sum(peer.get("transport_protocol_type") == "v2" for peer in selected),
            "departures_1h": departures.get(network, 0) if departures is not None else None,
        }
    return result


def build_snapshot() -> dict[str, Any]:
    chain = bitcoin_cli("getblockchaininfo")
    network = bitcoin_cli("getnetworkinfo")
    mempool = bitcoin_cli("getmempoolinfo")
    net_totals = bitcoin_cli("getnettotals")
    peers = bitcoin_cli("getpeerinfo")
    peer_rows = [peer for peer in peers if isinstance(peer, dict)] if isinstance(peers, list) else []
    bitcoind_uptime = safe_call("uptime")
    latest_version = dict(fetch_latest_core_version())

    height = int(chain.get("blocks", 0))
    block_stats = safe_call("getblockstats", str(height)) if height else None
    interval_seconds = block_interval_seconds(height, block_stats)
    if isinstance(block_stats, dict):
        block_stats["interval_seconds"] = interval_seconds
        block_stats["transaction_rate"] = (
            round(float(block_stats.get("txs", 0)) / interval_seconds, 3)
            if interval_seconds
            else None
        )
    peer_networks: dict[str, int] = {}
    peer_directions: dict[str, dict[str, int]] = {
        name: {"inbound": 0, "outbound": 0}
        for name in ("ipv4", "ipv6", "onion")
    }
    inbound = 0
    outbound = 0
    for peer in peer_rows:
        name = str(peer.get("network", "unknown"))
        peer_networks[name] = peer_networks.get(name, 0) + 1
        direction = "inbound" if peer.get("inbound") else "outbound"
        peer_directions.setdefault(name, {"inbound": 0, "outbound": 0})[
            direction
        ] += 1
        if peer.get("inbound"):
            inbound += 1
        else:
            outbound += 1

    local_addresses: dict[str, list[str]] = {
        "ipv4": [], "ipv6": [], "onion": []
    }
    for entry in network.get("localaddresses") or []:
        if not isinstance(entry, dict):
            continue
        address = str(entry.get("address") or "")
        if address.endswith(".onion"):
            family = "onion"
        else:
            try:
                family = "ipv4" if ipaddress.ip_address(address).version == 4 else "ipv6"
            except ValueError:
                continue
        if address not in local_addresses[family]:
            local_addresses[family].append(address)
    configured_public_address = None
    try:
        public_ip = ipaddress.ip_address(PUBLIC_NODE_ADDRESS)
        configured_public_address = {
            "family": "ipv4" if public_ip.version == 4 else "ipv6",
            "address": str(public_ip),
        }
    except ValueError:
        pass

    current_version = str(network.get("subversion") or "")
    current_tuple = version_tuple(current_version)
    latest_tuple = version_tuple(str(latest_version.get("latest") or ""))
    latest_version["current"] = current_version
    latest_version["update_available"] = bool(
        current_tuple and latest_tuple and current_tuple < latest_tuple
    )

    generated_at = int(time.time())
    departures = observe_peer_departures(peer_rows, bitcoind_uptime, generated_at)
    return {
        "generated_at": generated_at,
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
            "network_directions": peer_directions,
            "peer_quality": peer_quality_summary(peer_rows, generated_at, departures),
            "local_addresses": local_addresses,
            "host_ipv6_addresses": host_global_ipv6_addresses(),
            "configured_public_address": configured_public_address,
            "onion_address": local_addresses["onion"][0] if local_addresses["onion"] else None,
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
        "mempool_analysis": mempool_analysis(),
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
                    block_size_bytes INTEGER,
                    block_transaction_rate REAL,
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
                "block_size_bytes": "INTEGER",
                "block_transaction_rate": "REAL",
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
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS utxo_samples (
                    sampled_at INTEGER PRIMARY KEY,
                    height INTEGER NOT NULL,
                    transactions INTEGER,
                    txouts INTEGER NOT NULL,
                    bogosize INTEGER,
                    disk_size INTEGER,
                    total_amount_btc REAL
                )
                """
            )
            connection.execute(
                """CREATE TABLE IF NOT EXISTS zmq_events (
                    minute INTEGER PRIMARY KEY,
                    block_connected INTEGER NOT NULL DEFAULT 0,
                    block_disconnected INTEGER NOT NULL DEFAULT 0,
                    mempool_added INTEGER NOT NULL DEFAULT 0,
                    mempool_removed INTEGER NOT NULL DEFAULT 0,
                    gaps INTEGER NOT NULL DEFAULT 0
                )"""
            )
            connection.execute(
                """CREATE TABLE IF NOT EXISTS dashboard_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    occurred_at INTEGER NOT NULL,
                    kind TEXT NOT NULL,
                    message TEXT NOT NULL
                )"""
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS dashboard_events_time ON dashboard_events(occurred_at)"
            )
            connection.execute(
                """CREATE TABLE IF NOT EXISTS block_observations (
                    height INTEGER PRIMARY KEY,
                    observed_at INTEGER NOT NULL,
                    block_time INTEGER,
                    transactions INTEGER,
                    total_size INTEGER,
                    total_fee_btc REAL,
                    transaction_rate REAL,
                    source TEXT NOT NULL
                )"""
            )
            connection.execute(
                """CREATE TABLE IF NOT EXISTS dashboard_meta (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )"""
            )


def record_event(kind: str, message: str, at: int | None = None) -> None:
    """Persist a bounded, address-free operational event for the public view."""
    if kind not in {
        "dashboard_started", "dashboard_updated", "node_restarted", "peer_drop",
        "alert_on", "alert_off", "block_connected", "block_disconnected",
        "zmq_gap", "zmq_interrupted", "block_backfill", "block_gap",
    }:
        raise ValueError("Unknown event kind")
    timestamp = int(time.time() if at is None else at)
    with closing(database_connection()) as connection:
        with connection:
            connection.execute(
                "INSERT INTO dashboard_events (occurred_at, kind, message) VALUES (?, ?, ?)",
                (timestamp, kind, message[:240]),
            )
            connection.execute(
                "DELETE FROM dashboard_events WHERE occurred_at < ?",
                (timestamp - HISTORY_RETENTION_DAYS * 86400,),
            )


def record_dashboard_start() -> None:
    init_database()
    with closing(database_connection()) as connection:
        with connection:
            row = connection.execute(
                "SELECT value FROM dashboard_meta WHERE key = 'version'"
            ).fetchone()
            previous = row[0] if row else None
            connection.execute(
                "INSERT OR REPLACE INTO dashboard_meta (key, value) VALUES ('version', ?)",
                (__version__,),
            )
    if previous and previous != __version__:
        record_event("dashboard_updated", f"Dashboard von {previous} auf {__version__} aktualisiert")
    record_event("dashboard_started", f"Dashboard {__version__} gestartet")


def timeline_data(range_name: str) -> dict[str, Any]:
    duration, _ = HISTORY_RANGES.get(range_name, HISTORY_RANGES["24h"])
    now = int(time.time())
    cutoff = now - duration
    init_database()
    with closing(database_connection()) as connection:
        important_rows = connection.execute(
            """SELECT occurred_at, kind, message FROM dashboard_events
               WHERE occurred_at >= ? AND kind != 'block_connected'
               ORDER BY occurred_at DESC, id DESC LIMIT 60""",
            (cutoff,),
        ).fetchall()
        block_rows = connection.execute(
            """SELECT occurred_at, kind, message FROM dashboard_events
               WHERE occurred_at >= ? AND kind = 'block_connected'
               ORDER BY occurred_at DESC, id DESC LIMIT 20""",
            (cutoff,),
        ).fetchall()
        quality = connection.execute(
            """SELECT kind, COUNT(*) AS count FROM dashboard_events
               WHERE occurred_at >= ? AND kind IN
               ('zmq_gap', 'zmq_interrupted', 'dashboard_started', 'block_gap')
               GROUP BY kind""",
            (cutoff,),
        ).fetchall()
        backfilled = connection.execute(
            """SELECT COUNT(*) FROM block_observations
               WHERE block_time >= ? AND source = 'rpc_backfill'""",
            (cutoff,),
        ).fetchone()[0]
    return {
        "range": range_name if range_name in HISTORY_RANGES else "24h",
        "generated_at": now,
        "events": sorted((dict(row) for row in [*important_rows, *block_rows]),
                         key=lambda row: row["occurred_at"], reverse=True),
        "quality": {**{key: 0 for key in ("zmq_gap", "zmq_interrupted", "dashboard_started", "block_gap")},
                    **{row["kind"]: row["count"] for row in quality},
                    "blocks_backfilled": backfilled},
    }


def summarize_chain_tips(raw: Any, observed_at: int) -> dict[str, Any]:
    """Keep the complete counts, but bound the public list of fork candidates."""
    if not isinstance(raw, list):
        return {"available": False, "observed_at": observed_at, "active": None,
                "other_count": 0, "status_counts": {}, "other_tips": []}
    tips = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        height, branchlen, status, block_hash = (
            item.get("height"), item.get("branchlen"), item.get("status"), item.get("hash")
        )
        if (not isinstance(height, int) or isinstance(height, bool) or height < 0
                or not isinstance(branchlen, int) or isinstance(branchlen, bool) or branchlen < 0
                or not isinstance(status, str) or not re.fullmatch(r"[a-z-]{1,32}", status)
                or not isinstance(block_hash, str) or not re.fullmatch(r"[0-9a-fA-F]{64}", block_hash)):
            continue
        tips.append({"height": height, "branchlen": branchlen,
                     "status": status, "hash": block_hash.lower()})
    active = next((tip for tip in tips if tip["status"] == "active"), None)
    if active is None:
        return {"available": False, "observed_at": observed_at, "active": None,
                "other_count": 0, "status_counts": {}, "other_tips": []}
    others = [tip for tip in tips if tip["status"] != "active"]
    others.sort(key=lambda tip: tip["height"], reverse=True)
    return {"available": True, "observed_at": observed_at, "active": active,
            "other_count": len(others), "status_counts": dict(Counter(tip["status"] for tip in others)),
            "other_tips": others[:12]}


def chain_tips_data(range_name: str) -> dict[str, Any]:
    now = int(time.time())
    with _chain_tips_cache_lock:
        if _chain_tips_cache["data"] is None or time.monotonic() >= _chain_tips_cache["expires"]:
            _chain_tips_cache.update(
                data=summarize_chain_tips(safe_call("getchaintips"), now),
                expires=time.monotonic() + 60,
            )
        tips = dict(_chain_tips_cache["data"])
    duration, _ = HISTORY_RANGES.get(range_name, HISTORY_RANGES["24h"])
    init_database()
    with closing(database_connection()) as connection:
        row = connection.execute(
            """SELECT COUNT(*) AS count, MAX(occurred_at) AS latest
               FROM dashboard_events WHERE kind = 'block_disconnected' AND occurred_at >= ?""",
            (now - duration,),
        ).fetchone()
    tips["range"] = range_name if range_name in HISTORY_RANGES else "24h"
    tips["disconnected_blocks"] = row["count"]
    tips["last_disconnected_at"] = row["latest"]
    return tips


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
        _number(block.get("total_size")),
        _number(block.get("transaction_rate")),
        _number(system.get("cpu_percent")),
        _number(memory.get("used_percent")),
        _number(disk.get("free_percent")),
        _number(disk.get("free")),
        _number(network.get("bitcoind_uptime")),
    )

    cutoff = sampled_at - HISTORY_RETENTION_DAYS * 24 * 60 * 60
    previous = None
    with closing(database_connection()) as connection:
        with connection:
            previous = connection.execute(
                "SELECT sampled_at, connections, bitcoind_uptime FROM node_samples "
                "ORDER BY sampled_at DESC LIMIT 1"
            ).fetchone()
            connection.execute(
                """
                INSERT OR REPLACE INTO node_samples (
                    sampled_at, blocks, verification_progress, size_on_disk,
                    connections, connections_in, connections_out,
                    mempool_transactions, mempool_bytes, mempool_memory_usage,
                    mempool_min_fee_sat_vb, fee_2_sat_vb, fee_6_sat_vb,
                    fee_12_sat_vb, bytes_received, bytes_sent,
                    block_transactions, block_total_fee_btc, block_size_bytes,
                    block_transaction_rate, cpu_percent,
                    memory_used_percent, disk_free_percent, disk_free_bytes,
                    bitcoind_uptime
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                values,
            )
            connection.execute(
                "DELETE FROM node_samples WHERE sampled_at < ?",
                (cutoff,),
            )
    if previous is not None and sampled_at > previous["sampled_at"]:
        old_uptime, new_uptime = previous["bitcoind_uptime"], network.get("bitcoind_uptime")
        if isinstance(old_uptime, int) and isinstance(new_uptime, int) and new_uptime < old_uptime:
            record_event("node_restarted", "Bitcoin Core wurde neu gestartet", sampled_at)
        old_peers, new_peers = previous["connections"], network.get("connections")
        if isinstance(old_peers, int) and isinstance(new_peers, int):
            drop = old_peers - new_peers
            if old_peers >= 5 and drop >= max(3, (old_peers * 3 + 9) // 10):
                record_event("peer_drop", f"Peers deutlich gesunken: {old_peers} auf {new_peers}", sampled_at)


def backfill_missing_blocks(data: dict[str, Any], max_blocks: int = 12) -> None:
    """Recover recent block statistics from Core without a costly full rescan."""
    if not _backfill_lock.acquire(blocking=False):
        return
    try:
        current_height = int(data.get("chain", {}).get("blocks") or 0)
        if current_height <= 0:
            return
        with closing(database_connection()) as connection:
            row = connection.execute(
                "SELECT MIN(height), MAX(height) FROM block_observations"
            ).fetchone()
            first_observed_height, previous_height = row
            first_height = (current_height if previous_height is None else
                            max(first_observed_height, current_height - max_blocks + 1))
            known = {row[0] for row in connection.execute(
                "SELECT height FROM block_observations WHERE height BETWEEN ? AND ?",
                (first_height, current_height),
            )}
            heights = [height for height in range(first_height, current_height + 1)
                       if height not in known]
            skipped = (max(0, first_height - previous_height - 1)
                       if previous_height is not None and previous_height < current_height else 0)
            if not heights and not skipped:
                return
            recovered = 0
            failed = 0
            observations = []
            for height in heights:
                previous_time_row = connection.execute(
                    "SELECT block_time FROM block_observations WHERE height = ?",
                    (height - 1,),
                ).fetchone()
                previous_time = previous_time_row[0] if previous_time_row else None
                if observations and observations[-1][0] == height - 1:
                    previous_time = observations[-1][2]
                stats = data.get("latest_block") if height == current_height else None
                if not isinstance(stats, dict):
                    stats = safe_call("getblockstats", str(height))
                if not isinstance(stats, dict) or not isinstance(stats.get("time"), int):
                    failed += 1
                    continue
                block_time = stats["time"]
                interval = block_time - previous_time if previous_time is not None else None
                rate = (round(float(stats["txs"]) / interval, 3)
                        if isinstance(stats.get("txs"), int) and interval and interval > 0 else None)
                fee = stats.get("totalfee")
                observations.append((height, int(time.time()), block_time,
                                     _number(stats.get("txs")), _number(stats.get("total_size")),
                                     float(fee) / 100_000_000 if isinstance(fee, (int, float)) else None,
                                     rate, "snapshot" if height == current_height else "rpc_backfill"))
                if height != current_height:
                    recovered += 1
            with connection:
                connection.executemany(
                    """INSERT OR REPLACE INTO block_observations
                       (height, observed_at, block_time, transactions, total_size,
                        total_fee_btc, transaction_rate, source)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    observations,
                )
                connection.execute(
                    "DELETE FROM block_observations WHERE block_time < ?",
                    (int(time.time()) - HISTORY_RETENTION_DAYS * 86400,),
                )
        if recovered:
            record_event("block_backfill", f"{recovered} fehlende Blockstatistiken per RPC nachgetragen")
        if skipped or failed:
            record_event("block_gap", f"{skipped + failed} Blockstatistiken nicht nachgetragen (Grenze oder RPC nicht verfügbar)")
    finally:
        _backfill_lock.release()


def run_block_backfill(data: dict[str, Any]) -> None:
    try:
        backfill_missing_blocks(data)
    except Exception as exc:
        print(f"Block backfill failed: {exc}", flush=True)
        try:
            record_event("block_gap", "Blockstatistiken konnten nicht nachgetragen werden")
        except (OSError, sqlite3.Error):
            pass


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
                AVG(block_transactions) AS block_transactions,
                AVG(block_total_fee_btc) AS block_total_fee_btc,
                AVG(block_size_bytes) AS block_size_bytes,
                AVG(block_transaction_rate) AS block_transaction_rate,
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


def store_daily_utxo_sample(now: int | None = None) -> bool:
    """Store one inexpensive UTXO-set summary per configured interval."""
    global _utxo_last_attempt
    sampled_at = int(time.time()) if now is None else int(now)
    init_database()
    with closing(database_connection()) as connection:
        latest = connection.execute(
            "SELECT MAX(sampled_at) FROM utxo_samples"
        ).fetchone()[0]
    if latest is not None and sampled_at - int(latest) < UTXO_SAMPLE_SECONDS:
        return False
    if sampled_at - _utxo_last_attempt < UTXO_SAMPLE_SECONDS:
        return False
    _utxo_last_attempt = sampled_at
    try:
        result = bitcoin_cli("gettxoutsetinfo", "none", timeout=600)
    except RpcError:
        return False
    if not isinstance(result, dict) or not isinstance(result.get("txouts"), int):
        return False
    with closing(database_connection()) as connection:
        with connection:
            connection.execute(
                """
                INSERT OR REPLACE INTO utxo_samples (
                    sampled_at, height, transactions, txouts, bogosize,
                    disk_size, total_amount_btc
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    sampled_at,
                    int(result.get("height") or 0),
                    _number(result.get("transactions")),
                    int(result["txouts"]),
                    _number(result.get("bogosize")),
                    _number(result.get("disk_size")),
                    _number(result.get("total_amount")),
                ),
            )
            cutoff = sampled_at - HISTORY_RETENTION_DAYS * 24 * 60 * 60
            connection.execute(
                "DELETE FROM utxo_samples WHERE sampled_at < ?", (cutoff,)
            )
    return True


def analytics_data(range_name: str) -> dict[str, Any]:
    history = history_data(range_name)
    duration, bucket_seconds = HISTORY_RANGES.get(range_name, HISTORY_RANGES["24h"])
    cutoff = int(time.time()) - duration
    with closing(database_connection()) as connection:
        rows = connection.execute(
            """
            SELECT sampled_at AS timestamp, height, transactions, txouts,
                   bogosize, disk_size, total_amount_btc
            FROM utxo_samples
            WHERE sampled_at >= ?
            ORDER BY sampled_at
            """,
            (cutoff,),
        ).fetchall()
        if len(rows) < 2:
            recent_rows = connection.execute(
                """
                SELECT sampled_at AS timestamp, height, transactions, txouts,
                       bogosize, disk_size, total_amount_btc
                FROM utxo_samples
                ORDER BY sampled_at DESC LIMIT 2
                """
            ).fetchall()
            if len(recent_rows) > len(rows):
                rows = list(reversed(recent_rows))
        block_rows = connection.execute(
            """SELECT CAST(block_time / ? AS INTEGER) * ? AS timestamp,
                      AVG(total_size) AS block_size_bytes,
                      AVG(transaction_rate) AS block_transaction_rate,
                      AVG(transactions) AS block_transactions,
                      AVG(total_fee_btc) AS block_total_fee_btc
               FROM block_observations WHERE block_time >= ?
               GROUP BY timestamp ORDER BY timestamp""",
            (bucket_seconds, bucket_seconds, cutoff),
        ).fetchall()
    block_points = {point["timestamp"]: point for point in history["points"]}
    for row in block_rows:
        point = block_points.setdefault(row["timestamp"], {"timestamp": row["timestamp"]})
        # A sparse RPC sample must not erase a known value from node snapshots.
        point.update({key: value for key, value in dict(row).items() if value is not None})
    return {
        "range": history["range"],
        "generated_at": int(time.time()),
        "block_points": [block_points[key] for key in sorted(block_points)],
        "utxo_points": [dict(row) for row in rows],
        "mempool": mempool_analysis(),
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
    transition: str | None = None
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
                    transition = "alert_on"
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
                    transition = "alert_off"
                connection.execute(
                    "DELETE FROM alert_states WHERE alert_key = ?",
                    (alert_key,),
                )
    if transition:
        record_event(transition, f"{'Alarm' if transition == 'alert_on' else 'Entwarnung'}: {alert_key}", now)
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
        external.get("found") is True and external.get("reachable") is False,
        f"Externer Crawler meldet {PUBLIC_NODE_ADDRESS}:{PUBLIC_NODE_PORT} als nicht erreichbar",
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


def read_config_file() -> tuple[bytes, dict[str, str]]:
    if CONFIG_FILE.is_symlink() or not CONFIG_FILE.is_file():
        raise OSError("Dashboard .env is missing or is a symbolic link")
    raw = CONFIG_FILE.read_bytes()
    if len(raw) > 65536:
        raise ValueError("Dashboard .env is too large")
    values: dict[str, str] = {}
    for line in raw.decode("utf-8").splitlines():
        match = re.match(r"^([A-Z][A-Z0-9_]*)=(.*)$", line)
        if match:
            value = match.group(2).strip()
            try:
                parts = shlex.split(value, comments=False, posix=True)
                values[match.group(1)] = parts[0] if len(parts) == 1 else value
            except ValueError:
                values[match.group(1)] = value
    return raw, values


def config_defaults() -> dict[str, str]:
    return {
        "PUBLIC_NODE_ADDRESS": PUBLIC_NODE_ADDRESS,
        "PUBLIC_NODE_PORT": str(PUBLIC_NODE_PORT),
        "ZMQ_SEQUENCE_ENDPOINT": ZMQ_SEQUENCE_ENDPOINT,
        "DASHBOARD_CACHE_SECONDS": str(CACHE_SECONDS),
        "SAMPLE_INTERVAL_SECONDS": str(SAMPLE_INTERVAL_SECONDS),
        "HISTORY_RETENTION_DAYS": str(HISTORY_RETENTION_DAYS),
        "MEMPOOL_ANALYSIS_SECONDS": str(MEMPOOL_ANALYSIS_SECONDS),
        "UTXO_SAMPLE_SECONDS": str(UTXO_SAMPLE_SECONDS),
        "EXTERNAL_CACHE_SECONDS": str(EXTERNAL_CACHE_SECONDS),
        "VERSION_CHECK_SECONDS": str(VERSION_CHECK_SECONDS),
        "ALERT_EMAIL": ALERT_EMAIL,
        "ALERT_WEBHOOK_URL": ALERT_WEBHOOK_URL,
        "ALERT_GRACE_SECONDS": str(ALERT_GRACE_SECONDS),
        "ALERT_NO_INBOUND_SECONDS": str(ALERT_NO_INBOUND_SECONDS),
        "ALERT_COOLDOWN_SECONDS": str(ALERT_COOLDOWN_SECONDS),
        "SYNC_LAG_BLOCKS": str(SYNC_LAG_BLOCKS),
        "DISK_MAX_USED_PERCENT": str(DISK_MAX_USED_PERCENT),
        "MEMORY_MAX_USED_PERCENT": str(MEMORY_MAX_USED_PERCENT),
        "DASHBOARD_GITHUB_REPOSITORY": DASHBOARD_GITHUB_REPOSITORY,
        "DASHBOARD_GITHUB_TOKEN": DASHBOARD_GITHUB_TOKEN,
    }


def admin_config_data() -> dict[str, Any]:
    if not ADMIN_UPDATES_ENABLED:
        raise OSError("Configuration is managed externally in container mode")
    _, saved = read_config_file()
    defaults = config_defaults()
    fields = []
    for key, label, section, kind in CONFIG_FIELDS:
        value = saved.get(key, defaults[key])
        fields.append({
            "key": key, "label": label, "section": section, "kind": kind,
            "value": "" if kind == "secret" else value,
            "configured": bool(value) if kind == "secret" else None,
            "range": CONFIG_NUMERIC_RANGES.get(kind),
        })
    return {"fields": fields, "restart_required": True}


def validate_config_value(key: str, value: Any) -> str:
    kind = CONFIG_FIELD_KINDS[key]
    if not isinstance(value, str) or len(value) > 2048 or any(
        character.isspace() or character in "\\\"'\x00" for character in value
    ):
        raise ValueError(f"Invalid value for {key}")
    if kind in CONFIG_NUMERIC_RANGES:
        if not re.fullmatch(r"[0-9]+(?:\.[0-9]+)?" if kind == "percent" else r"[0-9]+", value):
            raise ValueError(f"Invalid number for {key}")
        minimum, maximum = CONFIG_NUMERIC_RANGES[kind]
        number = float(value) if kind == "percent" else int(value)
        if not minimum <= number <= maximum:
            raise ValueError(f"{key} must be between {minimum} and {maximum}")
        return value if kind == "percent" else str(number)
    if kind == "address":
        try:
            ipaddress.ip_address(value)
        except ValueError:
            if len(value) > 253 or not re.fullmatch(r"(?i)[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?", value):
                raise ValueError("Invalid public node address") from None
    elif kind == "zmq" and value:
        if not re.fullmatch(r"tcp://127\.0\.0\.1:[1-9][0-9]{0,4}", value) or int(value.rsplit(":", 1)[1]) > 65535:
            raise ValueError("ZMQ endpoint must be on 127.0.0.1")
    elif kind == "email" and value:
        if not re.fullmatch(r"[^@]+@[^@.]+(?:\.[^@.]+)+", value):
            raise ValueError("Invalid alert email")
    elif kind == "webhook" and value:
        parsed = urlparse(value)
        if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
            raise ValueError("Webhook must be an HTTPS URL without credentials")
    elif kind == "repository":
        if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", value):
            raise ValueError("Invalid GitHub repository")
    return value


def write_config_file(content: bytes) -> None:
    descriptor, temporary = tempfile.mkstemp(prefix=".env.", dir=CONFIG_FILE.parent)
    try:
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, CONFIG_FILE)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def save_admin_config(submitted: Any) -> tuple[int, str]:
    if not ADMIN_UPDATES_ENABLED:
        return 409, "Configuration is managed externally in container mode"
    if not isinstance(submitted, dict) or set(submitted) != set(CONFIG_FIELD_KINDS):
        return 400, "Incomplete or unknown configuration fields"
    with _config_lock:
        original: bytes | None = None
        written = False
        try:
            original, saved = read_config_file()
            defaults = config_defaults()
            values: dict[str, str] = {}
            for key in CONFIG_FIELD_KINDS:
                proposed = submitted[key]
                if CONFIG_FIELD_KINDS[key] == "secret" and proposed == "":
                    proposed = saved.get(key, defaults[key])
                values[key] = validate_config_value(key, proposed)
            kept = [
                line for line in original.decode("utf-8").splitlines()
                if not (re.match(r"^([A-Z][A-Z0-9_]*)=", line) and line.split("=", 1)[0] in CONFIG_FIELD_KINDS)
            ]
            content = ("\n".join(kept + [f"{key}={values[key]}" for key in CONFIG_FIELD_KINDS]) + "\n").encode()
            if len(content) > 65536:
                raise ValueError("Configuration is too large")
            write_config_file(content)
            written = True
            result = subprocess.run(ADMIN_CONFIG_RESTART_COMMAND, capture_output=True, text=True, timeout=10, check=False)
            if result.returncode != 0:
                write_config_file(original)
                written = False
                return 503, "Configuration restart could not be scheduled; changes were reverted"
            return 202, "Configuration saved; dashboard restarts in a few seconds"
        except ValueError as exc:
            return 400, str(exc)
        except (OSError, subprocess.TimeoutExpired) as exc:
            if written and original is not None:
                try:
                    write_config_file(original)
                except OSError as rollback_exc:
                    print(f"Admin config rollback failed: {rollback_exc}", flush=True)
            print(f"Admin config save failed: {exc}", flush=True)
            return 503, "Configuration could not be saved"


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
        "Update-Auftrag wurde isoliert gestartet. Das Protokoll erscheint unten."
    )


def update_result_from_journal(kind: str, log: str) -> tuple[str, str]:
    """Determine the most recent unit result without guessing from updater output."""
    unit = "bitcoin-dashboard-update" if kind == "dashboard" else "bitcoin-core-update"
    state = "unknown"
    lines = log.splitlines()
    latest_start = 0
    for index, line in enumerate(lines):
        if f"systemd[1]: Started {unit}.service" in line or f"systemd[1]: Starting {unit}.service" in line:
            state = "running"
            latest_start = index
        elif f"systemd[1]: {unit}.service: Failed with result" in line or f"systemd[1]: {unit}.service: Main process exited" in line:
            state = "failure"
        elif f"systemd[1]: {unit}.service: Deactivated successfully" in line or f"systemd[1]: Finished {unit}.service" in line:
            state = "success"
    return state, "\n".join(lines[latest_start:]) if lines else "Noch keine Update-Einträge vorhanden."


def admin_update_log(kind: str) -> tuple[int, str, str]:
    if not ADMIN_UPDATES_ENABLED:
        return 409, "Update-Protokolle werden in dieser Installation extern verwaltet", "unknown"
    command = ADMIN_LOG_COMMANDS.get(kind)
    if command is None:
        return 404, "Unbekanntes Update-Protokoll", "unknown"
    try:
        result = subprocess.run(
            command, capture_output=True, text=True, timeout=8, check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return 503, "Update-Protokoll ist derzeit nicht erreichbar", "unknown"
    if result.returncode != 0:
        return 503, "Update-Protokoll konnte nicht gelesen werden; Bootstrap erneut ausführen", "unknown"
    state, log = update_result_from_journal(kind, result.stdout[-32_768:])
    return 200, log, state


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
                if not _backfill_lock.locked():
                    threading.Thread(
                        target=run_block_backfill, args=(data,),
                        name="block-backfill", daemon=True,
                    ).start()
                publish_browser_event("sample")
            except Exception as exc:
                print(f"Sample processing failed: {exc}", flush=True)
        elapsed = time.monotonic() - started
        time.sleep(max(1, SAMPLE_INTERVAL_SECONDS - elapsed))


def analytics_sampler_loop() -> None:
    """Keep slow analytical RPCs away from health and alert sampling."""
    while True:
        try:
            store_daily_utxo_sample()
        except Exception as exc:
            print(f"UTXO sample failed: {exc}", flush=True)
        time.sleep(min(3600, max(60, UTXO_SAMPLE_SECONDS)))


class Handler(BaseHTTPRequestHandler):
    server_version = f"BitcoinDashboard/{__version__}"

    def send_event_stream(self) -> None:
        if not _sse_slots.acquire(blocking=False):
            self.send_bytes(b'{"error":"Too many live connections"}', "application/json", 503)
            return
        try:
            with _event_condition:
                seen = _event_serial
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream; charset=utf-8")
            self.send_header("Cache-Control", "no-cache, no-transform")
            self.send_header("Connection", "close")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(b": connected\n\n")
            self.wfile.flush()
            deadline = time.monotonic() + 300
            while time.monotonic() < deadline:
                with _event_condition:
                    _event_condition.wait_for(lambda: _event_serial != seen, timeout=15)
                    serial, kind = _event_serial, _event_kind
                if serial != seen:
                    self.wfile.write(f"id: {serial}\nevent: {kind}\ndata: {{}}\n\n".encode())
                    seen = serial
                else:
                    self.wfile.write(b": heartbeat\n\n")
                self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError, OSError):
            pass
        finally:
            self.close_connection = True
            _sse_slots.release()

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
        public_assets = {
            "/static/i18n.js": ("i18n.js", "text/javascript; charset=utf-8"),
            "/static/locales/de.json": ("locales/de.json", "application/json; charset=utf-8"),
            "/static/locales/en.json": ("locales/en.json", "application/json; charset=utf-8"),
        }
        if path in public_assets:
            filename, content_type = public_assets[path]
            self.send_bytes((STATIC_DIR / filename).read_bytes(), content_type)
            return
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
        if path == "/api/admin/config":
            if not self.require_admin_auth():
                return
            try:
                body = json.dumps(admin_config_data(), separators=(",", ":")).encode()
                self.send_bytes(body, "application/json; charset=utf-8")
            except (OSError, ValueError) as exc:
                print(f"Admin config unavailable: {exc}", flush=True)
                self.send_bytes(b'{"error":"Configuration editor is not installed; run admin bootstrap"}', "application/json; charset=utf-8", 503)
            return
        if path in ("/api/admin/logs/dashboard", "/api/admin/logs/bitcoin"):
            if not self.require_admin_auth():
                return
            kind = path.rsplit("/", 1)[-1]
            status, log, state = admin_update_log(kind)
            body = json.dumps({"log": log, "state": state}, separators=(",", ":")).encode()
            self.send_bytes(body, "application/json; charset=utf-8", status)
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
        if path == "/api/realtime":
            body = json.dumps(realtime_data(), separators=(",", ":")).encode()
            self.send_bytes(body, "application/json; charset=utf-8")
            return
        if path == "/api/events":
            self.send_event_stream()
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
        if path == "/api/timeline":
            range_name = parse_qs(parsed.query).get("range", ["24h"])[0]
            try:
                body = json.dumps(timeline_data(range_name), separators=(",", ":")).encode()
                self.send_bytes(body, "application/json; charset=utf-8")
            except Exception as exc:
                print(f"Timeline request failed: {exc}", flush=True)
                self.send_bytes(b'{"error":"Timeline unavailable"}', "application/json; charset=utf-8", 503)
            return
        if path == "/api/chain-tips":
            range_name = parse_qs(parsed.query).get("range", ["24h"])[0]
            try:
                body = json.dumps(chain_tips_data(range_name), separators=(",", ":")).encode()
                self.send_bytes(body, "application/json; charset=utf-8")
            except Exception as exc:
                print(f"Chain tips request failed: {exc}", flush=True)
                self.send_bytes(b'{"error":"Chain tips unavailable"}', "application/json; charset=utf-8", 503)
            return
        if path == "/api/analytics":
            range_name = parse_qs(parsed.query).get("range", ["24h"])[0]
            try:
                body = json.dumps(
                    analytics_data(range_name), separators=(",", ":")
                ).encode()
                self.send_bytes(body, "application/json; charset=utf-8")
            except Exception as exc:
                print(f"Analytics request failed: {exc}", flush=True)
                body = b'{"error":"Analytics data unavailable"}'
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
            "/api/admin/config",
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
        if path == "/api/admin/config":
            if not constant_time_equal(self.headers.get("X-CSRF-Token", ""), ADMIN_CSRF_TOKEN):
                self.send_bytes(b'{"error":"CSRF validation failed"}', "application/json; charset=utf-8", 403)
                return
            if content_type != "application/json" or not 1 <= content_length <= 8192:
                self.send_bytes(b'{"error":"Invalid configuration request"}', "application/json; charset=utf-8", 400)
                return
            try:
                submitted = json.loads(self.rfile.read(content_length).decode("utf-8"))
            except (ValueError, UnicodeDecodeError):
                self.send_bytes(b'{"error":"Invalid JSON"}', "application/json; charset=utf-8", 400)
                return
            status, message = save_admin_config(submitted)
            body = json.dumps({"ok": status == 202, "message": message}, separators=(",", ":")).encode()
            self.send_bytes(body, "application/json; charset=utf-8", status)
            return
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
    try:
        record_dashboard_start()
    except (OSError, sqlite3.Error) as exc:
        print(f"Dashboard start event unavailable: {exc}", flush=True)
    if ZMQ_SEQUENCE_ENDPOINT:
        if not re.fullmatch(r"tcp://127\.0\.0\.1:[1-9][0-9]{0,4}", ZMQ_SEQUENCE_ENDPOINT) or int(ZMQ_SEQUENCE_ENDPOINT.rsplit(":", 1)[1]) > 65535:
            raise SystemExit("ZMQ_SEQUENCE_ENDPOINT must be a local tcp://127.0.0.1:PORT endpoint")
        threading.Thread(target=zmq_listener_loop, name="zmq-sequence", daemon=True).start()
    history_thread = threading.Thread(
        target=sampler_loop,
        name="history-sampler",
        daemon=True,
    )
    history_thread.start()
    analytics_thread = threading.Thread(
        target=analytics_sampler_loop,
        name="analytics-sampler",
        daemon=True,
    )
    analytics_thread.start()
    print(f"Bitcoin dashboard listening on http://{HOST}:{PORT}", flush=True)
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()
