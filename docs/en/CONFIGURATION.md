# Dashboard configuration

[Deutsch](../CONFIGURATION.md) | [English documentation](../../README.en.md#documentation)

Systemd installations read `/var/lib/bitcoin-dashboard/.env`.
`/home/btc/bitcoin-dashboard/.env` is a symbolic link to that file.
The real file belongs to service user `btc`, with mode `0600`;
the running web service has read-only access to the application directory.

At `/admin` → **Dashboard configuration**, edit the node address, ZMQ endpoint,
sampling intervals, retention, alert thresholds and destinations, and GitHub
repository and token. The editor validates allowed fields and values, writes
atomically and schedules a short delayed restart of the fixed dashboard service.
If restart scheduling fails, it restores the previous file. Valid admin
authentication, same-origin checks and a CSRF token are required.

Secret tokens are never sent back to the browser. An empty GitHub token field
means “keep the current value”. `ADMIN_TOKEN`, service binding, RPC paths,
database path and upload directory cannot be changed over the web.
Edit these locally as root in `.env`, then run
`sudo systemctl restart bitcoin-dashboard`.

## One-time migration of an existing installation

1. Update to dashboard 1.13.0 or newer. Migration also requires the **new**
   `installer/bootstrap-admin.sh` from the release archive; normal dashboard
   updates do not install root helpers.
2. Extract the release into a temporary directory as root and run bootstrap:

   ```sh
   tmpdir=$(mktemp -d)
   tar -xzf bitcoin-node-dashboard-1.13.0.tar.gz -C "$tmpdir"
   sudo sh "$tmpdir/bitcoin-dashboard/installer/bootstrap-admin.sh"
   rm -rf -- "$tmpdir"
   ```

3. Bootstrap copies the old `/etc/default/bitcoin-dashboard` into the new
   `.env` **only if** no configuration exists there. It reinstalls the service
   and narrowly scoped restart permission. The old file remains unchanged as
   a fallback copy but is no longer read by the service.
4. Check without printing secrets:

   ```sh
   systemctl show bitcoin-dashboard -p EnvironmentFiles
   stat -c '%U:%G %a %n' /var/lib/bitcoin-dashboard/.env
   readlink /home/btc/bitcoin-dashboard/.env
   curl -fsS http://127.0.0.1:8787/healthz
   ```

5. Open `/admin`, save a harmless setting and verify the restart.
   Only after successful verification, deliberately remove or securely archive
   the obsolete `/etc/default/bitcoin-dashboard` copy.

Never upload configuration files or GitHub tokens to a repository.
`.env` is excluded by `.gitignore`. In container installations, Compose
continues to manage `.env`; the web editor is disabled.
