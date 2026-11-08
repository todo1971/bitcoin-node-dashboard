# Secure updates

[Deutsch](../UPDATES.md) | English

## One-time security migration

Complete the [migration since 1.24](SECURITY.md) before using the new helpers. Regular updates do not replace root helpers, units or sudoers rules. Existing installations must not skip this step.

## Updating and selecting the source

`/admin` shows available versions, results and recent journal lines. The browser can only start fixed root jobs without variable arguments. Update manually and manage the source locally:

```bash
sudo /usr/local/sbin/update-bitcoin-dashboard
sudo journalctl -u bitcoin-dashboard-update -n 80 --no-pager
```

```bash
sudoedit /etc/bitcoin-dashboard-updater.conf
```

```text
DASHBOARD_GITHUB_REPOSITORY=todo1971/bitcoin-node-dashboard
DASHBOARD_GITHUB_TOKEN=
```

The public repository needs no token. Root reads its repository and optional token exclusively from this root-owned file (0600), never the dashboard `.env`. The web UI cannot edit this source. The separate unprivileged version display may still use `.env` values. Root configuration changes require no service restart.

For private forks create a fine-grained token at [GitHub](https://github.com/settings/personal-access-tokens): exactly one repository and only `Contents: Read-only`. Enter it locally, never in Git, chat or logs. Revoke immediately after disclosure.

The helper prevents concurrent updates, downloads both versioned release assets, verifies SHA-256 and all archive members before extraction, and tests without root privileges. It backs up and replaces the protected code tree, restarts the dashboard and checks `/healthz`. On failure it restores the old tree and attempts to start it. Root never imports application code. Backups: `/var/backups/bitcoin-dashboard`; root-owned download cache: `/var/cache/bitcoin-dashboard-updates`.

Required assets: `bitcoin-node-dashboard-VERSION.tar.gz` and `bitcoin-node-dashboard-VERSION.tar.gz.sha256`. GitHub's automatic source archives do not replace these assets. A checksum from the same release cannot protect against a compromised publisher account. Public API requests are subject to GitHub's rate limit; the version display uses a cache.

## Updating Bitcoin Core

Upload an official stable Linux archive under `/admin`: `bitcoin-VERSION-x86_64-linux-gnu.tar.gz` or `bitcoin-VERSION-aarch64-linux-gnu.tar.gz`. Only the server architecture and at most 200 MiB are allowed. Debug, source, Windows, macOS and prerelease packages are rejected.

The fixed root job copies uploads into protected storage without following symlinks. It downloads `SHA256SUMS` and `SHA256SUMS.asc` only from the official version-specific Bitcoin Core location. At least two distinct valid signatures from `/usr/local/share/bitcoin-core/trustedkeys.gpg`, SHA-256, archive paths, platform and version must match. Same and older versions are rejected.

Import signing keys from the official `bitcoin-core/guix.sigs` repository into the root-owned keyring only after independently comparing their fingerprints. Do not lower `BITCOIN_MIN_VALID_SIGNATURES=2` without assessing the risk. Tokens and private keys must never enter release packages.

After migration binaries reside under `/usr/local/lib/bitcoin-core/bin`. The helper stops Core, backs up and replaces binaries, starts Core and checks RPC using restricted credentials. Startup failures trigger recovery. Review configuration, wallet and database changes before major releases. Unattended automatic Core updates are not provided. Update remote nodes and containers on their respective host or by replacing their image.

## Proxy and troubleshooting

Adjust reverse proxy upload and time limits. `plesk-apache.conf` belongs to Apache; `plesk-nginx.conf` only to an actual nginx installation. Use HTTPS or an SSH tunnel for administration. Never expose port 8787 or RPC publicly.

After failures inspect separate update logs in the admin UI, service state and protected backups. [Security model and test coverage](SECURITY.md).
