#!/usr/bin/env python3
# Copyright (C) 2026 Hardy (todo1971) <hb@308-arms.de>
# SPDX-License-Identifier: GPL-3.0-only
"""Run inside a disposable image to report runtime dependencies without network I/O."""
import _sqlite3
import _ssl
import importlib.util
import json
import os
import platform
import shutil
import sqlite3
import ssl
import subprocess
import sys
from pathlib import Path


def audit():
    with sqlite3.connect(':memory:') as connection:
        assert connection.execute('SELECT sqlite_version()').fetchone()[0]
    context = ssl.create_default_context()
    certificates = context.cert_store_stats()['x509_ca']
    if not certificates:
        raise RuntimeError('No trusted CA certificates available')
    binaries = [sys.executable, _sqlite3.__file__, _ssl.__file__]
    bitcoin = shutil.which('bitcoind')
    if bitcoin:
        binaries.extend([bitcoin, shutil.which('bitcoin-cli')])
    libraries = {}
    for binary in binaries:
        result = subprocess.run(['ldd', binary], capture_output=True, text=True, check=True)
        if 'not found' in result.stdout:
            raise RuntimeError(f'Missing runtime library: {binary}')
        libraries[binary] = result.stdout.strip().splitlines()
    inventory = subprocess.run(['dpkg-query', '-W', '-f=${binary:Package}\t${Version}\t${Architecture}\n'],
                               capture_output=True, text=True, check=True).stdout
    packages = [dict(zip(('package', 'version', 'architecture'), line.split('\t')))
                for line in inventory.splitlines()]
    tools = {name:shutil.which(name) for name in
             ('bash', 'sh', 'install', 'groupadd', 'useradd', 'sendmail', 'curl', 'gpg', 'sqlite3')}
    return {'machine':platform.machine(), 'python':sys.version.split()[0],
            'sqlite':sqlite3.sqlite_version, 'openssl':ssl.OPENSSL_VERSION,
            'trusted_ca_count':certificates,
            'pyzmq_available':importlib.util.find_spec('zmq') is not None,
            'bitcoin_included':bitcoin is not None, 'tools':tools,
            'libraries':libraries, 'packages':packages}


if __name__ == '__main__':
    print(json.dumps(audit(), indent=2))
