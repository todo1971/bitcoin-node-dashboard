# Secure updates

[Deutsch](../UPDATES.md) | [English documentation](../../README.en.md#documentation)

## Integrated administration

Maintenance is integrated into the dashboard at `/admin`.
It uses a random password of at least 32 characters, HTTP Basic authentication,
an additional CSRF token, a global lockout after five failed attempts and size,
method and origin checks.

Install root helpers and the password from a temporarily extracted, previously
verified release archive in the current directory:

```bash
tmpdir=$(mktemp -d)
sudo tar -xzf ./bitcoin-node-dashboard-1.20.0.tar.gz -C "$tmpdir"
sudo sh "$tmpdir/bitcoin-dashboard/installer/bootstrap-admin.sh"
sudo rm -rf -- "$tmpdir"
```

The script prints the username and password. Administration is then available
at the dashboard HTTPS address plus `/admin`, or through an SSH tunnel to the
normal dashboard port. No second web process or port is used.

## Update the dashboard

The dashboard queries the GitHub Releases API. Private repositories require
a fine-grained Personal Access Token with read-only `Contents`
permission on this repository only. Since 1.13, enter it at
`/admin` → Dashboard configuration, or edit `.env` locally:

```bash
sudo editor /var/lib/bitcoin-dashboard/.env
```

```text
DASHBOARD_GITHUB_REPOSITORY=todo1971/bitcoin-node-dashboard
DASHBOARD_GITHUB_TOKEN=github_pat_...
```

Then restart the service:

```bash
sudo chmod 0600 /var/lib/bitcoin-dashboard/.env
sudo chown btc:btc /var/lib/bitcoin-dashboard/.env
sudo systemctl restart bitcoin-dashboard
```

`/admin` displays the installed and latest release versions.
**Update dashboard** sends no browser parameters to root: the application may
only start one precisely fixed transient systemd job. The root helper:

1. Locks against concurrent updates.
2. Finds the latest GitHub release.
3. Downloads its archive and separate SHA-256 file and verifies the checksum.
4. Rejects archives with unsafe paths or symbolic links.
5. Compiles and runs unit tests as the dashboard user.
6. Creates a backup at `/var/backups/bitcoin-dashboard`.
7. Installs only the permitted application files.
8. Restarts the service.
9. Checks `/healthz` and rolls back on failure.

Every release needs two assets named exactly:

```text
bitcoin-node-dashboard-VERSION.tar.gz
bitcoin-node-dashboard-VERSION.tar.gz.sha256
```

The updater deliberately does not overwrite the systemd unit, root helpers or
sudoers files from the archive. After upgrading to 1.11.6, run
`installer/bootstrap-admin.sh` from an extracted release as root once.
It updates helpers and moves staging into root-owned
`/var/cache/bitcoin-dashboard-updates`. The previous location is no longer
needed after this migration.

Since 1.11.7, `/admin` shows the last 80 journal lines of the two update units
in the browser, refreshed every five seconds. Admin authentication is required;
units and journal arguments cannot be freely selected. After upgrading to
1.11.7, run `installer/bootstrap-admin.sh` **once more as root**, because normal
updates deliberately leave sudoers unchanged. Only then can the dashboard user
read these fixed log outputs.

Since 1.11.8, a status above the output shows the latest run: green for successful
systemd completion, red for failure, and “Running” while active.
Without a definite result, it remains neutral.

## Public repository without a token

Public repositories do not require a GitHub token. Both version discovery and
the root downloader already support this mode. It does not work while the
repository is still private.

After publication, edit the dashboard .env locally as root:

```bash
sudoedit /var/lib/bitcoin-dashboard/.env
```

```text
DASHBOARD_GITHUB_REPOSITORY=todo1971/bitcoin-node-dashboard
DASHBOARD_GITHUB_TOKEN=
```

Explicitly empty an existing token or remove its line. An empty token field at
`/admin` instead means “keep the previous value”. Keep `ADMIN_TOKEN` configured:
admin authentication is independent of GitHub.

```bash
sudo systemctl restart bitcoin-dashboard
```

Then use version discovery and “Update dashboard” at `/admin`. The downloader
still fetches the two named release assets and verifies SHA-256; tests, backups
and rollback remain enabled. GitHub's automatically generated source archives
do not replace these release assets.

GitHub currently allows 60 anonymous REST requests per hour per public IP.
Version discovery is cached for six hours by default. Other traffic sharing
the IP may exhaust this budget; retry later or optionally use a read-only token.
See [GitHub documentation](https://docs.github.com/en/rest/using-the-rest-api/rate-limits-for-the-rest-api).

Read-only live check from a complete checkout using a public repository:

```bash
python3 tools/check_public_release.py --repo cli/cli
```

This uses the existing downloader without a token, reads metadata and a small
checksum file, and installs nothing. After publication, test
`--repo todo1971/bitcoin-node-dashboard`. The test suite additionally covers the
complete package-specific download with and without a token using controlled
responses. A live end-to-end check of this repository's public access is possible
only after its visibility changes.

## Update Bitcoin Core

At `/admin`, select or drop the Linux archive downloaded from
`bitcoincore.org`. Only stable release filenames in these forms are accepted:

```text
bitcoin-VERSION-x86_64-linux-gnu.tar.gz
bitcoin-VERSION-aarch64-linux-gnu.tar.gz
```

Uploads are limited to 200 MiB and the server's architecture.
Debug, source, Windows, macOS and release-candidate archives are rejected.
After upload, `/admin` displays filename, size and the beginning of the locally
calculated SHA-256 value. **Verify and install** starts the parameterless root job.

The root helper first copies the upload from
`/var/lib/bitcoin-dashboard/bitcoin-core-upload` into a root-owned temporary
directory. From the strictly validated version it constructs only these URLs:

```text
https://bitcoincore.org/bin/bitcoin-core-VERSION/SHA256SUMS
https://bitcoincore.org/bin/bitcoin-core-VERSION/SHA256SUMS.asc
```

It then verifies GPG signatures, SHA-256, archive paths, platform and version.
Installed or older versions are rejected. Only after verification does it stop
bitcoind, back up `/home/btc/bin`, install binaries and start the service.
Startup failure restores the backup. Successful installation removes the
upload and its metadata.

A manually prepared package can still be staged at
`/var/cache/bitcoin-dashboard-updates/bitcoin-core-update`; normal operation
uses the `/admin` upload.

### Reverse proxy uploads

Reapply `plesk-apache.conf` in Plesk's additional Apache directives for the
longer timeout. If nginx is installed, put `plesk-nginx.conf` in
**Additional nginx directives**. It raises the upload limit to 200 MB and
disables full nginx request buffering. Do not put nginx directives in Apache
configuration.

### Trusted signing keys

The updater requires:

```text
/usr/local/share/bitcoin-core/trustedkeys.gpg
```

At least two distinct valid signatures from this keyring are required by default.
`BITCOIN_MIN_VALID_SIGNATURES=2` in `/etc/bitcoin-dashboard-updater.conf`
controls the threshold; do not reduce it without consciously reviewing the risk.

Keys can be obtained from the official `bitcoin-core/guix.sigs` repository,
but import them only after checking each fingerprint through an independent
trusted source:

```bash
keywork=$(mktemp -d)
git clone --depth 1 https://github.com/bitcoin-core/guix.sigs.git \
  "$keywork/guix.sigs"
gpg --show-keys --with-fingerprint \
  "$keywork"/guix.sigs/builder-keys/*.gpg
```

After comparing fingerprints for at least two deliberately selected signers,
import their keys:

```bash
sudo install -d -o root -g root -m 0755 /usr/local/share/bitcoin-core
sudo gpg --batch --no-default-keyring \
  --keyring /usr/local/share/bitcoin-core/trustedkeys.gpg \
  --import /PFAD/ZU/SIGNER-1.gpg /PFAD/ZU/SIGNER-2.gpg
sudo chmod 0644 /usr/local/share/bitcoin-core/trustedkeys.gpg
rm -rf -- "$keywork"
```

The updater requires the configured number of valid trusted signatures and
an exactly matching SHA-256 checksum before stopping the node, backing up
existing binaries, installing and starting the release. Startup failure
restores the previous binaries.

Review major release notes for configuration, wallet and database format changes
before updating. Unattended automatic Bitcoin Core updates are deliberately
not provided.

## Root configuration

Paths and service names are configured in:

```text
/etc/bitcoin-dashboard-updater.conf
```

The file must belong to `root:root` and must not be writable by `btc` or the
selected dashboard user. Sudoers allows only two complete fixed `systemd-run`
calls without variable arguments. Updates run outside the dashboard control
group so a dashboard update can restart its calling web process.

```text
/usr/bin/systemd-run --unit=bitcoin-dashboard-update --collect --no-block /usr/local/sbin/update-bitcoin-dashboard
/usr/bin/systemd-run --unit=bitcoin-core-update --collect --no-block /usr/local/sbin/update-bitcoin-core
```

Never store the GitHub token in Git, logs or release packages.
Revoke it immediately at GitHub if exposed accidentally.

## Configure a fine-grained GitHub token

Open <https://github.com/settings/personal-access-tokens>, choose
**Generate new token**, and use:

| Setting | Value |
|---|---|
| Token name | `Bitcoin Dashboard Server` |
| Expiration | For example, 365 days |
| Resource owner | `todo1971` |
| Repository access | `Only select repositories` |
| Repository | `bitcoin-node-dashboard` |
| Repository permission | Only `Contents: Read-only` |

GitHub automatically adds `Metadata: Read-only`. No write, Actions,
Administration or account permissions are needed. The full token appears only
once. Do not copy it into chat, shell history, Git or documentation.

Since 1.13, enter the token at `/admin` → Dashboard configuration, or edit
`.env` locally:

```bash
sudoedit /var/lib/bitcoin-dashboard/.env
```

```text
DASHBOARD_GITHUB_REPOSITORY=todo1971/bitcoin-node-dashboard
DASHBOARD_GITHUB_TOKEN=github_pat_HIER_DAS_ECHTE_TOKEN
```

Replace the example placeholder entirely with the token issued by GitHub.
Then set permissions and restart:

```bash
sudo chown btc:btc /var/lib/bitcoin-dashboard/.env
sudo chmod 0600 /var/lib/bitcoin-dashboard/.env
sudo systemctl restart bitcoin-dashboard
```

Check that a value exists without printing the secret:

```bash
sudo awk -F= '
  /^DASHBOARD_GITHUB_TOKEN=/ {
    print length($2) >= 20 ? "GitHub-Token ist gesetzt" : "GitHub-Token fehlt"
  }
' /var/lib/bitcoin-dashboard/.env
```

The example command prints a configured/missing message in German.
Administration should then show, for example,
`Installed: 1.13.0 · GitHub: 1.13.0 · up to date` in the English UI.
If the check fails, inspect logs:

```bash
sudo journalctl -u bitcoin-dashboard -n 50 --no-pager
```

Before expiration, generate a replacement token with the same minimal
permissions, replace the value in `/var/lib/bitcoin-dashboard/.env` and restart
the service. Then revoke the old token at GitHub. If exposure is suspected,
revoke and replace it immediately.
