# Web installation

[Deutsch](../WEB_INSTALLATION.md) | [English documentation](../../README.en.md#documentation)

## Security model

The installer is not served through a public domain. It binds to
`127.0.0.1:8791`, generates a random password on every start and is opened
only through an SSH tunnel. Stop the process with Ctrl+C after installation.

Supported systems are systemd-based Linux with Python 3.11 or newer.
Bitcoin Core must already be running, and the chosen service user must have
access to its RPC cookie.

## Start

Extract the release archive from the current directory into a temporary directory:

```bash
tmpdir=$(mktemp -d)
sudo tar -xzf ./bitcoin-node-dashboard-1.19.0.tar.gz -C "$tmpdir"
sudo python3 "$tmpdir/bitcoin-dashboard/installer/web_installer.py"
```

The process prints a username and one-time password. Open a tunnel in a second
local terminal:

```bash
ssh -L 8791:127.0.0.1:8791 trading-server
```

Then open the local browser:

```text
http://127.0.0.1:8791
```

The installer validates users, paths and numeric ranges, installs the application
in the service user's home, writes the environment file and a hardened systemd
unit, configures protected update helpers and starts the dashboard.
The printed admin password belongs to `/admin`. After installation and stopping
the installer, remove the temporary directory with
`sudo rm -rf -- "$tmpdir"`.

## New server with Bitcoin Core

For a new dedicated server, first create a system user:

```bash
sudo useradd --system --create-home --home-dir /home/btc \
  --shell /usr/sbin/nologin btc
sudo install -d -o btc -g btc -m 0750 /home/btc/bitcoin-data
sudo install -d -o root -g root -m 0755 /home/btc/bin
```

`installer/bitcoin.conf.example` and `installer/bitcoind.service.example`
provide a safe starting point. Review paths, pruning size and wallet settings
before starting.

Download Bitcoin Core binaries only from `bitcoincore.org` and verify them
against `SHA256SUMS` and a deliberately selected trusted signature.
The included update helper rejects packages without the required checks.

## Reverse proxy

After installation, the dashboard stays on `127.0.0.1`.
Use an HTTPS reverse proxy for public access. `plesk-apache.conf` is included
for Plesk. With nginx, Caddy or standalone Apache, forward HTTPS to the local
dashboard port. Never publish Bitcoin RPC port 8332.

If Plesk uses nginx, add `plesk-nginx.conf` for Bitcoin Core uploads.
The Apache example already includes the longer timeout for large archives.
