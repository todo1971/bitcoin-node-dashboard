# Dashboard configuration

[Deutsch](../CONFIGURATION.md) | English

The systemd installation reads `/var/lib/bitcoin-dashboard/.env`, linked from `/opt/bitcoin-dashboard/.env`. The file belongs to the dedicated `bitcoin-dashboard` account with mode 0600; code belongs to root.

Edit the node address, ZMQ, sampling intervals, retention and alert settings under `/admin`. Allowed fields and values are validated, the file is replaced atomically, and only the fixed dashboard service is restarted. Failed restart scheduling restores the previous file. Admin authentication, same-origin and CSRF checks are required.

`ADMIN_TOKEN`, service binding, RPC and database paths are editable only locally by root. The root update repository and optional GitHub token are separate in `/etc/bitcoin-dashboard-updater.conf`; the browser cannot change them. Public downloads need no token. Dashboard `.env` changes require a dashboard restart.

The [one-time security migration since 1.24](SECURITY.md) preserves existing settings. `/etc/default/bitcoin-dashboard` is only used when no state `.env` exists. Existing secrets remain protected and are never printed.

```bash
systemctl show bitcoin-dashboard -p EnvironmentFiles
stat -c '%U:%G %a %n' /var/lib/bitcoin-dashboard/.env
readlink /opt/bitcoin-dashboard/.env
curl -fsS http://127.0.0.1:8787/healthz
```

Never commit configuration to Git. Containers manage environment settings through Compose; their web editor is disabled.
