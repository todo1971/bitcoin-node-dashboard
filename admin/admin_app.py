#!/usr/bin/env python3
"""Local-only maintenance UI for the Bitcoin Node Dashboard."""

from __future__ import annotations

import base64
import hmac
import json
import os
import subprocess
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


HOST = "127.0.0.1"
PORT = int(os.getenv("ADMIN_PORT", "8790"))
TOKEN = os.getenv("ADMIN_TOKEN", "")
DASHBOARD_UPDATER = "/usr/local/sbin/update-bitcoin-dashboard"
BITCOIN_UPDATER = "/usr/local/sbin/update-bitcoin-core"
BITCOIN_CLI = os.getenv("BITCOIN_CLI", "/home/btc/bin/bitcoin-cli")
UPDATE_ROOT = Path(os.getenv("UPDATE_ROOT", "/home/todo"))

PAGE = """<!doctype html>
<html lang="de"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Bitcoin Dashboard Administration</title><style>
:root{color-scheme:dark;--bg:#0b0d10;--card:#151a20;--line:#29313a;--text:#eef2f6;--muted:#9ba8b6;--orange:#f7931a;--green:#37d67a;--red:#ff6b6b}*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);font:15px/1.5 system-ui,sans-serif}main{width:min(850px,calc(100% - 32px));margin:0 auto;padding:42px 0}h1{font-size:34px;margin:0 0 8px}p{color:var(--muted)}.warning{padding:12px;border:1px solid #604516;background:#241b0c;border-radius:10px}.grid{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-top:20px}.card{border:1px solid var(--line);border-radius:14px;background:var(--card);padding:20px}button{border:1px solid var(--orange);border-radius:9px;padding:10px 14px;background:#20170c;color:var(--orange);cursor:pointer}button:disabled{opacity:.5;cursor:wait}pre{min-height:150px;overflow:auto;padding:14px;border-radius:10px;background:#07090b;color:#c9d1d9;white-space:pre-wrap}.ok{color:var(--green)}.bad{color:var(--red)}@media(max-width:650px){.grid{grid-template-columns:1fr}}
</style></head><body><main><h1>Bitcoin Administration</h1><p>Lokale Wartungsoberfläche – nur über einen SSH-Tunnel verwenden.</p><div class="warning">Updates werden nur aus den festgelegten Paketverzeichnissen ausgeführt. Bitcoin Core benötigt Prüfsumme und eine vertrauenswürdige GPG-Signatur.</div><section class="grid"><article class="card"><h2>Dashboard</h2><p id="dashboardStatus">Status wird geladen …</p><button data-action="dashboard">Dashboard aktualisieren</button></article><article class="card"><h2>Bitcoin Core</h2><p id="bitcoinStatus">Status wird geladen …</p><button data-action="bitcoin">Bitcoin Core aktualisieren</button></article></section><h2>Ausgabe</h2><pre id="output">Bereit.</pre></main><script>
const output=document.getElementById('output');
async function status(){try{const r=await fetch('/api/status'),d=await r.json();document.getElementById('dashboardStatus').textContent=d.dashboard;document.getElementById('bitcoinStatus').textContent=d.bitcoin}catch(e){output.textContent='Statusfehler: '+e.message}}
document.querySelectorAll('button').forEach(b=>b.addEventListener('click',async()=>{if(!confirm('Dieses Update jetzt ausführen?'))return;b.disabled=true;output.textContent='Update läuft …';try{const r=await fetch('/api/update/'+b.dataset.action,{method:'POST',headers:{'X-Admin-Action':'update'}}),d=await r.json();output.textContent=d.output||d.error;output.className=r.ok?'ok':'bad';await status()}catch(e){output.textContent=e.message;output.className='bad'}finally{b.disabled=false}}));status();
</script></body></html>"""


def command(*args: str, timeout: int = 180) -> tuple[int, str]:
    try:
        result = subprocess.run(
            list(args),
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        output = (result.stdout + result.stderr).strip()
        return result.returncode, output[-20_000:]
    except (OSError, subprocess.TimeoutExpired) as exc:
        return 1, str(exc)


def status_data() -> dict[str, str]:
    dashboard_code, dashboard_output = command(
        "systemctl", "is-active", "bitcoin-dashboard"
    )
    bitcoin_code, bitcoin_output = command(
        BITCOIN_CLI, "-version"
    )
    dashboard = "aktiv" if dashboard_code == 0 else dashboard_output or "inaktiv"
    if (UPDATE_ROOT / "bitcoin-node-dashboard-update.tar.gz").is_file():
        dashboard += " · Update-Paket bereit"
    bitcoin = (
        bitcoin_output.splitlines()[0]
        if bitcoin_code == 0 and bitcoin_output
        else "nicht erkannt"
    )
    version_file = UPDATE_ROOT / "bitcoin-core-update" / "version"
    if version_file.is_file():
        prepared = version_file.read_text(encoding="utf-8").strip()[:32]
        bitcoin += f" · Update {prepared} vorbereitet"
    return {"dashboard": dashboard, "bitcoin": bitcoin}


class Handler(BaseHTTPRequestHandler):
    server_version = "BitcoinDashboardAdmin/1.0"

    def authenticated(self) -> bool:
        if not TOKEN:
            return False
        header = self.headers.get("Authorization", "")
        if not header.startswith("Basic "):
            return False
        try:
            decoded = base64.b64decode(header[6:], validate=True).decode()
            _, supplied = decoded.split(":", 1)
        except (ValueError, UnicodeDecodeError):
            return False
        return hmac.compare_digest(supplied, TOKEN)

    def send_bytes(
        self, body: bytes, content_type: str, status: int = 200
    ) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'self'; style-src 'unsafe-inline'; "
            "script-src 'unsafe-inline'; connect-src 'self'; "
            "frame-ancestors 'none'",
        )
        self.end_headers()
        self.wfile.write(body)

    def require_auth(self) -> bool:
        if self.authenticated():
            return True
        self.send_response(HTTPStatus.UNAUTHORIZED)
        self.send_header("WWW-Authenticate", 'Basic realm="Bitcoin maintenance"')
        self.send_header("Content-Length", "0")
        self.end_headers()
        return False

    def do_GET(self) -> None:  # noqa: N802
        if not self.require_auth():
            return
        path = urlparse(self.path).path
        if path == "/":
            self.send_bytes(PAGE.encode(), "text/html; charset=utf-8")
            return
        if path == "/api/status":
            body = json.dumps(status_data()).encode()
            self.send_bytes(body, "application/json; charset=utf-8")
            return
        self.send_error(HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:  # noqa: N802
        if not self.require_auth():
            return
        if self.headers.get("X-Admin-Action") != "update":
            self.send_bytes(b'{"error":"Action header required"}', "application/json", 403)
            return
        path = urlparse(self.path).path
        updater = {
            "/api/update/dashboard": DASHBOARD_UPDATER,
            "/api/update/bitcoin": BITCOIN_UPDATER,
        }.get(path)
        if updater is None:
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        code, output = command("sudo", "-n", updater, timeout=900)
        body = json.dumps({"ok": code == 0, "output": output}).encode()
        self.send_bytes(
            body,
            "application/json; charset=utf-8",
            200 if code == 0 else 500,
        )

    def log_message(self, fmt: str, *args: Any) -> None:
        print(f"{self.address_string()} - {fmt % args}", flush=True)


if __name__ == "__main__":
    if not TOKEN:
        raise SystemExit("ADMIN_TOKEN is not configured")
    print(f"Maintenance UI listening on http://{HOST}:{PORT}", flush=True)
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()
