#!/usr/bin/env python3
# Copyright (C) 2026 Hardy (todo1971) <hb@308-arms.de>
# SPDX-License-Identifier: GPL-3.0-only
"""One-time, localhost-only web installer for systemd Linux servers."""

from __future__ import annotations

import base64
import hmac
import html
import ipaddress
import os
import re
import secrets
import shutil
import subprocess
import sys
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs

try:
    import grp
    import pwd
except ImportError:  # Allows validation tests on non-POSIX development hosts.
    grp = None
    pwd = None


HOST = "127.0.0.1"
PORT = 8791
TOKEN = secrets.token_urlsafe(24)
PROJECT_DIR = Path(__file__).resolve().parent.parent
NAME_PATTERN = re.compile(r"^[a-z_][a-z0-9_-]{0,31}$")
HOST_PATTERN = re.compile(r"^[A-Za-z0-9.-]{1,253}$")

PAGE = """<!doctype html><html lang="de"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Bitcoin Dashboard installieren</title><style>
:root{color-scheme:dark;--bg:#0b0d10;--card:#151a20;--line:#29313a;--text:#eef2f6;--muted:#9ba8b6;--orange:#f7931a}*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);font:15px/1.5 system-ui,sans-serif}main{width:min(780px,calc(100% - 32px));margin:0 auto;padding:40px 0}h1{font-size:34px}form{display:grid;grid-template-columns:1fr 1fr;gap:14px;padding:22px;border:1px solid var(--line);border-radius:14px;background:var(--card)}label{display:flex;flex-direction:column;gap:5px;color:var(--muted)}label.full{grid-column:1/-1}input{width:100%;padding:10px;border:1px solid var(--line);border-radius:8px;background:#0e1216;color:var(--text)}button{grid-column:1/-1;padding:12px;border:1px solid var(--orange);border-radius:9px;background:#20170c;color:var(--orange);cursor:pointer}pre{white-space:pre-wrap;background:#07090b;padding:15px;border-radius:10px;min-height:80px}@media(max-width:650px){form{grid-template-columns:1fr}label.full,button{grid-column:1}}</style></head><body><main><h1>Bitcoin Node Dashboard</h1><p>Einmalige Installation auf diesem Server. Die Seite ist ausschließlich über den lokalen SSH-Tunnel erreichbar.</p><form id="form"><label>Service-Benutzer<input name="service_user" value="btc" required></label><label>Dashboard-Port<input name="dashboard_port" value="8787" inputmode="numeric" required></label><label class="full">bitcoin-cli<input name="bitcoin_cli" value="/home/btc/bin/bitcoin-cli" required></label><label class="full">Bitcoin-Datadir<input name="bitcoin_datadir" value="/home/btc/bitcoin-data" required></label><label class="full">RPC-Cookie<input name="bitcoin_cookie" value="/home/btc/bitcoin-core/.bitcoin/.cookie" required></label><label>Öffentliche Node-Adresse<input name="public_address" placeholder="203.0.113.10 oder node.example.org" required></label><label>P2P-Port<input name="public_port" value="8333" inputmode="numeric" required></label><label>Messintervall (Sekunden)<input name="sample_interval" value="60" inputmode="numeric" required></label><label>Aufbewahrung (Tage)<input name="retention_days" value="365" inputmode="numeric" required></label><button type="submit">Dashboard installieren</button></form><h2>Ergebnis</h2><pre id="result">Bereit.</pre></main><script>document.getElementById('form').addEventListener('submit',async e=>{e.preventDefault();const result=document.getElementById('result');result.textContent='Installation läuft …';const body=new URLSearchParams(new FormData(e.target));try{const r=await fetch('/install',{method:'POST',headers:{'Content-Type':'application/x-www-form-urlencoded','X-Installer-Action':'install'},body}),text=await r.text();result.textContent=text;if(r.ok)e.target.querySelector('button').disabled=true}catch(error){result.textContent=error.message}});</script></body></html>"""


def parse_integer(value: str, minimum: int, maximum: int, name: str) -> int:
    try:
        number = int(value)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer") from exc
    if not minimum <= number <= maximum:
        raise ValueError(f"{name} must be between {minimum} and {maximum}")
    return number


def validate_public_address(value: str) -> str:
    try:
        return str(ipaddress.ip_address(value))
    except ValueError:
        if not HOST_PATTERN.fullmatch(value) or ".." in value:
            raise ValueError("Invalid public node address")
        return value.lower()


def validate_existing_path(value: str, kind: str) -> Path:
    path = Path(value)
    if not path.is_absolute() or ".." in path.parts:
        raise ValueError(f"Unsafe {kind} path")
    if kind == "bitcoin-cli":
        if not path.is_file() or not os.access(path, os.X_OK):
            raise ValueError("bitcoin-cli does not exist or is not executable")
    elif not path.exists():
        raise ValueError(f"{kind} path does not exist")
    return path


def copy_project(target: Path, uid: int, gid: int) -> None:
    target.mkdir(parents=True, exist_ok=True, mode=0o750)
    for filename in (
        "app.py",
        "LICENSE",
        "NOTICE",
        "README.md",
        "README.en.md",
        "CHANGELOG.md",
        "CHANGELOG.en.md",
        "bitcoin-dashboard.env.example",
        "plesk-apache.conf",
    ):
        source = PROJECT_DIR / filename
        if source.exists():
            shutil.copy2(source, target / filename)
    for dirname in ("static", "docs", "tests"):
        destination = target / dirname
        if destination.exists():
            shutil.rmtree(destination)
        shutil.copytree(PROJECT_DIR / dirname, destination)
    for root, directories, files in os.walk(target):
        os.chown(root, uid, gid)
        os.chmod(root, 0o750)
        for name in files:
            file_path = Path(root) / name
            os.chown(file_path, uid, gid)
            os.chmod(file_path, 0o640)


def install_dashboard(values: dict[str, str]) -> str:
    if pwd is None or grp is None or not hasattr(os, "geteuid"):
        raise RuntimeError("Installation requires a POSIX system")
    user_name = values.get("service_user", "")
    if not NAME_PATTERN.fullmatch(user_name):
        raise ValueError("Invalid service user")
    try:
        account = pwd.getpwnam(user_name)
    except KeyError as exc:
        raise ValueError(f"User {user_name} does not exist") from exc
    group_name = grp.getgrgid(account.pw_gid).gr_name

    dashboard_port = parse_integer(
        values.get("dashboard_port", ""), 1024, 65535, "Dashboard port"
    )
    public_port = parse_integer(
        values.get("public_port", ""), 1024, 65535, "P2P port"
    )
    sample_interval = parse_integer(
        values.get("sample_interval", ""), 30, 3600, "Sample interval"
    )
    retention_days = parse_integer(
        values.get("retention_days", ""), 1, 3650, "Retention days"
    )
    public_address = validate_public_address(values.get("public_address", ""))
    bitcoin_cli = validate_existing_path(values.get("bitcoin_cli", ""), "bitcoin-cli")
    bitcoin_datadir = validate_existing_path(
        values.get("bitcoin_datadir", ""), "Bitcoin datadir"
    )
    bitcoin_cookie = validate_existing_path(
        values.get("bitcoin_cookie", ""), "RPC cookie"
    )

    home = Path(account.pw_dir).resolve()
    if not home.is_absolute() or home == Path("/"):
        raise ValueError("Unsafe service user home directory")
    target = home / "bitcoin-dashboard"
    if (target / "app.py").exists():
        raise RuntimeError(
            "Dashboard is already installed; use the dedicated updater"
        )
    copy_project(target, account.pw_uid, account.pw_gid)

    environment = f"""DASHBOARD_HOST=127.0.0.1
DASHBOARD_PORT={dashboard_port}
DASHBOARD_CACHE_SECONDS=10
BITCOIN_CLI={bitcoin_cli}
BITCOIN_DATADIR={bitcoin_datadir}
BITCOIN_COOKIE={bitcoin_cookie}
PUBLIC_NODE_ADDRESS={public_address}
PUBLIC_NODE_PORT={public_port}
EXTERNAL_CACHE_SECONDS=300
DATABASE_PATH=/var/lib/bitcoin-dashboard/history.sqlite3
SAMPLE_INTERVAL_SECONDS={sample_interval}
HISTORY_RETENTION_DAYS={retention_days}
VERSION_CHECK_SECONDS=21600
ALERT_EMAIL=
ALERT_WEBHOOK_URL=
ALERT_GRACE_SECONDS=300
ALERT_NO_INBOUND_SECONDS=900
ALERT_COOLDOWN_SECONDS=21600
SYNC_LAG_BLOCKS=3
DISK_MAX_USED_PERCENT=90
MEMORY_MAX_USED_PERCENT=90
"""
    state_dir = Path("/var/lib/bitcoin-dashboard")
    if state_dir.is_symlink() or (state_dir / ".env").exists():
        raise RuntimeError("Dashboard state directory already contains a configuration")
    state_dir.mkdir(parents=True, exist_ok=True)
    os.chown(state_dir, account.pw_uid, account.pw_gid)
    os.chmod(state_dir, 0o750)
    env_path = state_dir / ".env"
    env_path.write_text(environment, encoding="utf-8")
    os.chown(env_path, account.pw_uid, account.pw_gid)
    os.chmod(env_path, 0o600)
    (target / ".env").symlink_to(env_path)

    unit = f"""[Unit]
Description=Read-only Bitcoin Core dashboard
After=network-online.target bitcoind.service
Wants=network-online.target

[Service]
Type=simple
User={user_name}
Group={group_name}
WorkingDirectory={target}
EnvironmentFile=/var/lib/bitcoin-dashboard/.env
ExecStart=/usr/bin/python3 {target}/app.py
Restart=on-failure
RestartSec=5
StateDirectory=bitcoin-dashboard
StateDirectoryMode=0750
PrivateTmp=true
ProtectSystem=strict
ProtectHome=read-only
ReadOnlyPaths={target} {bitcoin_datadir} {bitcoin_cookie.parent}
ProtectControlGroups=true

[Install]
WantedBy=multi-user.target
"""
    unit_path = Path("/etc/systemd/system/bitcoin-dashboard.service")
    unit_path.write_text(unit, encoding="utf-8")
    os.chown(unit_path, 0, 0)
    os.chmod(unit_path, 0o644)

    updater_config = Path("/etc/bitcoin-dashboard-updater.conf")
    updater_config.write_text(
        "\n".join(
            (
                "UPDATE_ROOT=/var/cache/bitcoin-dashboard-updates",
                f"DASHBOARD_USER={user_name}",
                f"DASHBOARD_TARGET={target}",
                "DASHBOARD_SERVICE=bitcoin-dashboard",
                f"DASHBOARD_HEALTH_URL=http://127.0.0.1:{dashboard_port}/healthz",
                "BITCOIN_SERVICE=bitcoind",
                f"BITCOIN_BIN_DIR={home}/bin",
                f"BITCOIN_DATADIR={bitcoin_datadir}",
                f"BITCOIN_COOKIE={bitcoin_cookie}",
                "BITCOIN_UPLOAD_DIR=/var/lib/bitcoin-dashboard/bitcoin-core-upload",
                "BITCOIN_MIN_VALID_SIGNATURES=2",
                "",
            )
        ),
        encoding="utf-8",
    )
    os.chown(updater_config, 0, 0)
    os.chmod(updater_config, 0o640)

    commands = (
        ("systemctl", "daemon-reload"),
        ("systemctl", "enable", "--now", "bitcoin-dashboard"),
        ("sh", str(PROJECT_DIR / "installer" / "bootstrap-admin.sh")),
    )
    output: list[str] = []
    for command in commands:
        result = subprocess.run(command, capture_output=True, text=True, check=False)
        output.append((result.stdout + result.stderr).strip())
        if result.returncode != 0:
            raise RuntimeError(f"Command failed: {' '.join(command)}\n{output[-1]}")
    return (
        "Installation erfolgreich.\n"
        f"Dashboard: http://127.0.0.1:{dashboard_port}\n"
        f"Installationspfad: {target}\n"
        f"{output[-1]}\n"
        "Als Nächstes einen HTTPS-Reverse-Proxy auf den lokalen Port einrichten."
    )


class Handler(BaseHTTPRequestHandler):
    def authenticated(self) -> bool:
        header = self.headers.get("Authorization", "")
        if not header.startswith("Basic "):
            return False
        try:
            decoded = base64.b64decode(header[6:], validate=True).decode()
            _, supplied = decoded.split(":", 1)
        except (ValueError, UnicodeDecodeError):
            return False
        return hmac.compare_digest(supplied, TOKEN)

    def require_auth(self) -> bool:
        if self.authenticated():
            return True
        self.send_response(HTTPStatus.UNAUTHORIZED)
        self.send_header("WWW-Authenticate", 'Basic realm="Dashboard installer"')
        self.send_header("Content-Length", "0")
        self.end_headers()
        return False

    def send_text(self, text: str, status: int = 200, content_type: str = "text/plain; charset=utf-8") -> None:
        body = text.encode()
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'self'; style-src 'unsafe-inline'; "
            "script-src 'unsafe-inline'; connect-src 'self'; "
            "frame-ancestors 'none'",
        )
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        if not self.require_auth():
            return
        if self.path == "/":
            self.send_text(PAGE, content_type="text/html; charset=utf-8")
        else:
            self.send_error(HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:  # noqa: N802
        if not self.require_auth():
            return
        if self.path != "/install" or self.headers.get("X-Installer-Action") != "install":
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0 or length > 16_384:
                raise ValueError("Invalid request size")
            raw = self.rfile.read(length).decode("utf-8")
            parsed = parse_qs(raw, strict_parsing=True)
            values = {key: items[0] for key, items in parsed.items() if items}
            result = install_dashboard(values)
            self.send_text(result)
        except Exception as exc:
            print(f"Installation failed: {exc}", file=sys.stderr, flush=True)
            self.send_text(f"Installation fehlgeschlagen: {html.escape(str(exc))}", 400)

    def log_message(self, fmt: str, *args: object) -> None:
        print(f"{self.address_string()} - {fmt % args}", flush=True)


if __name__ == "__main__":
    if os.geteuid() != 0:
        raise SystemExit("Run this one-time installer as root")
    print(f"Installer: http://{HOST}:{PORT}")
    print("SSH tunnel: ssh -L 8791:127.0.0.1:8791 YOUR_SERVER")
    print("Username: admin")
    print(f"Password: {TOKEN}")
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()
