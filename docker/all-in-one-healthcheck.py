#!/usr/bin/env python3
import subprocess
import urllib.request


subprocess.run(
    ["bitcoin-cli", "-datadir=/data/bitcoin", "getblockchaininfo"],
    check=True,
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL,
    timeout=5,
)
with urllib.request.urlopen("http://127.0.0.1:8787/healthz", timeout=5) as response:
    if response.status != 200:
        raise SystemExit(1)
