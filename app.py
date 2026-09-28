#!/usr/bin/env python3
"""Small, read-only Bitcoin Core dashboard with no external dependencies."""

from __future__ import annotations

import json
import os
import subprocess
import threading
import time
import urllib.error
import urllib.request
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


APP_DIR = Path(__file__).resolve().parent
__version__ = "1.1.0"
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
        path = urlparse(self.path).path
        if path == "/api/dashboard":
            try:
                body = json.dumps(snapshot(), separators=(",", ":")).encode()
                self.send_bytes(body, "application/json; charset=utf-8")
            except Exception as exc:  # Return a controlled error, never a traceback.
                body = json.dumps({"error": str(exc)}).encode()
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
    print(f"Bitcoin dashboard listening on http://{HOST}:{PORT}", flush=True)
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()
