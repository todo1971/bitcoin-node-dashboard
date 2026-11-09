# Security and one-time migration since 1.24

[Deutsch](../SECURITY.md) | English

Copyright (C) 2026 Hardy (todo1971) <hb@308-arms.de>

## Trust boundaries

The host installation separates the `bitcoin-dashboard` service account from the Bitcoin Core account. Dashboard code is root-owned under `/opt/bitcoin-dashboard`. Writable state remains under `/var/lib/bitcoin-dashboard`; `.env` and `rpc.auth` belong to the dashboard account with mode 0600. Local nodes use dedicated RPC credentials instead of the full node cookie.

The local RPC account permits only: `getblockchaininfo`, `getnetworkinfo`, `getmempoolinfo`, `getnettotals`, `getpeerinfo`, `uptime`, `getblockstats`, `getblock`, `getaddrmaninfo`, `getrawmempool`, `getchaintips`, `gettxoutsetinfo`, `getblockcount`, `estimatesmartfee`. Existing RPC users retain their permissions. Remote node administrators must configure this restriction on their node themselves. This host bootstrap does not migrate containers; manage container updates externally and restrict their RPC credentials separately.

Root updates obtain their repository and optional GitHub token exclusively from `/etc/bitcoin-dashboard-updater.conf` (root:root, 0600). The web UI cannot edit them. Values in the dashboard `.env` may only influence the unprivileged version display. The public project needs no token. HTTPS and a trusted GitHub account remain part of the trust chain: a checksum from the same release is not an independent signature.

## One-time migration

A regular dashboard update does not replace root helpers. Run the bootstrap **once as root** from a deliberately selected and verified release. Never use a checkout writable by the dashboard account. Run these commands in a root shell:

```bash
install -d -m 0700 /root/bitcoin-dashboard-release
cd /root/bitcoin-dashboard-release
curl -fL -O https://github.com/todo1971/bitcoin-node-dashboard/releases/download/v1.26.0/bitcoin-node-dashboard-1.26.0.tar.gz
curl -fL -O https://github.com/todo1971/bitcoin-node-dashboard/releases/download/v1.26.0/bitcoin-node-dashboard-1.26.0.tar.gz.sha256
sha256sum -c bitcoin-node-dashboard-1.26.0.tar.gz.sha256
tmpdir=$(mktemp -d /root/bitcoin-dashboard-release/unpack.XXXXXX)
tar -xzf bitcoin-node-dashboard-1.26.0.tar.gz -C "$tmpdir"
sh "$tmpdir/bitcoin-dashboard/installer/bootstrap-admin.sh"
systemctl enable bitcoin-dashboard
curl -fsS http://127.0.0.1:8787/healthz
```

Create your own backup first. The bootstrap also saves state, original services and helpers under `/var/backups/bitcoin-dashboard/hardening-*`. Backups contain secrets and remain root-only. The first local migration **restarts both the dashboard and Bitcoin Core**, without rebooting the server. Existing history and a sufficiently long admin password are preserved. A new password is generated in the protected `.env` if needed and is never printed; manage it locally with `sudoedit /var/lib/bitcoin-dashboard/.env`.

A local systemd node requires an explicit `-conf=...` path and its own Core service account. Bootstrap preserves the existing configuration content, adds RPC permissions and writes `/etc/bitcoin-dashboard/bitcoin.conf` (root and Core group, 0640). A `bitcoind.service` drop-in uses this configuration and root-owned binaries copied to `/usr/local/lib/bitcoin-core/bin`. Existing `-datadir` arguments are preserved. Future Core configuration changes must target the new active file. The original file is retained. Review unusual configurations with includes, additional drop-ins or external nodes first.

On failure bootstrap restores saved service files, code, state and ownership, and attempts to restart the previously running service. Review backups and the journal afterwards; external failures can also prevent rollback. Repeated bootstrap retains the RPC credentials. Unchanged RPC permissions do not restart Core; since 1.25, bootstrap adds `getblock` when necessary and restarts Core to activate it.

## Web protection

Administration requires Basic authentication, a password of at least 32 characters, CSRF and Origin checks. Five incorrect logins temporarily lock only that client address. Only a loopback proxy may supply the last `X-Forwarded-For` address as the client identity. The reverse proxy must append the real client address or replace this header; never publish the dashboard port directly.

Each client is limited to 240 requests per minute and an additional twelve expensive history/analysis requests per minute. There are at most 48 concurrent HTTP handlers, a 15-second socket read timeout and 16 SSE connections. Excess requests receive 429 or 503. Content Security Policy blocks third-party scripts and inline JavaScript. HTTP server headers no longer disclose Python or dashboard versions.

Root helpers validate ownership and write permissions for every path component. All archive members are checked for paths, size, duplicates and file types before extraction starts. Links and special files are rejected. Application tests and Core version checks run without root privileges. Dashboard updates replace a protected code tree and roll back if the health check fails; root never imports dashboard code. Core uploads are copied without following symlinks into protected storage and still require valid GPG signatures and SHA-256.

## Verification and limits

Regression tests cover archive attacks, untrusted update sources, redirects, isolated login lockouts and bounded HTTP handlers. CI also runs real Bitcoin Core regtest in disposable AMD64 and ARM64 environments: separate accounts, permitted and rejected RPC calls, protected paths and recovery after a deliberately failed restart. This does not replace a penetration test or production backups.

GitHub protects `main` with required successful CI checks; Secret Scanning, Push Protection and Dependabot are enabled. Features are developed independently. Report security concerns without credentials to hb@308-arms.de.

Since 1.26 the same bootstrap also adds read-only `getaddrmaninfo` when needed for address inventory. Existing credentials are preserved; only changed permissions require a Core restart.
