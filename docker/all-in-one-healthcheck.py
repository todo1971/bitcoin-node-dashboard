#!/usr/bin/env python3
# Copyright (C) 2026 Hardy (todo1971) <hb@308-arms.de>
# SPDX-License-Identifier: GPL-3.0-only
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
