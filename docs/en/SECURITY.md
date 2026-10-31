# Security model

[Deutsch](../SECURITY.md) | [English documentation](../../README.en.md#documentation)

## Principles

- Bind the web service only to `127.0.0.1` by default.
- Keep Bitcoin RPC port 8332 local and outside the reverse proxy.
- Never send the RPC cookie to browsers or external services.
- Browsers cannot execute arbitrary RPC commands.
- Start subprocesses without a shell and with fixed argument structures.
- Run the systemd service as unprivileged user `btc`.
- Use only `/var/lib/bitcoin-dashboard` for persistent writable data.
- Include CSP, frame, referrer and MIME security headers in browser responses.
- Bind the one-time installer to `127.0.0.1` and require a random access token.
- Protect `/admin` with a strong separate password, CSRF and origin checks.
- Lock administration for 15 minutes after five failed logins.
- Limit root actions to two complete fixed update commands and one delayed dashboard restart; do not forward browser arguments to root.
- Allow the admin log view to read only the last 80 lines from two fixed update units via sudo. Accept no arbitrary journal arguments and limit responses to 32 KiB.
- Root-owned helpers accept no arguments, validate package paths and run outside the web service's control group.
- Root owns `/var/cache/bitcoin-dashboard-updates`, with mode `0700`.
- Core uploads are the sole package-staging exception in the fixed StateDirectory path. The root updater copies them into its own temporary directory before verification.

If the dashboard process is fully compromised, an attacker can trigger the fixed
update jobs and dashboard restart and modify the service-user-writable `.env`,
but cannot choose root command arguments or package paths. Dashboard packages
are tested before installation. Bitcoin Core packages additionally require
matching SHA-256 checksums and the configured number of valid signatures from
the root-controlled keyring. This boundary depends on the update cache, root
helpers, sudoers rules and updater configuration remaining unwritable by `btc`.

A compromised dashboard can replace a Core archive in the upload directory and
start the fixed update job, but cannot choose its checksum or signature:
the root helper downloads both from fixed HTTPS addresses at `bitcoincore.org`.
The node is stopped only after trusted-signature and SHA-256 verification succeeds.

## Public information

Public instances intentionally expose some information already observable over
Bitcoin P2P, including node version, block height and public IP.
Other peers' IP addresses are currently not delivered to the browser.

## Recommended protection

- Enforce HTTPS with Let's Encrypt.
- Never use `/admin` over public unencrypted HTTP.
- Optionally enable Plesk password protection or an IP allowlist.
- Keep dashboard port 8787 and RPC port 8332 blocked by the public firewall.
- Keep `/var/lib/bitcoin-dashboard/.env` at mode `0600` for service user `btc`; edit only allowed settings through `/admin`.
- Regularly update Bitcoin Core and the operating system.
- Add reverse proxy rate limits for heavily used public deployments.
- Never publish one-time installer port 8791 through Plesk, the firewall or reverse proxy.
- Use only HTTPS webhook targets and treat the destination as a secret.

## Secrets

Never commit:

- RPC cookie contents.
- RPC passwords.
- Wallet files, seeds or private keys.
- TLS private keys.
- Personal access tokens.
- `DASHBOARD_GITHUB_TOKEN` from `/var/lib/bitcoin-dashboard/.env`.
- `ADMIN_TOKEN` from the same file.
- Production SQLite databases.
- Webhook URLs containing access tokens.

`.gitignore` therefore excludes `.env`.

The GitHub token receives only `Contents: Read-only` for the single
`bitcoin-node-dashboard` repository. Store it in
`/var/lib/bitcoin-dashboard/.env`, readable only by `btc`, with mode `0600`.
Replace expired or potentially exposed tokens and revoke the old token at GitHub.

## Reporting security issues

The repository is public. Report security problems privately to the repository
owner first; do not put credentials or exploitable details in public issues.
