# Alerts and system monitoring

[Deutsch](../ALERTS.md) | [English documentation](../../README.en.md#documentation)

## Monitored conditions

Each sample checks:

- Local Bitcoin Core RPC availability.
- Block/header height difference and Initial Block Download.
- Inbound peer count.
- Free space on the Bitcoin data directory's filesystem.
- Host RAM utilization.
- External crawler reachability status of the public P2P endpoint, when reported.
- Availability of a newer stable Bitcoin Core version.

CPU, RAM, free space and bitcoind uptime are also stored in SQLite.
The dashboard displays disk space as the used percentage and alerts at
90 percent used by default. Stored free-space values are retained for
historical calculations. An absent external directory entry means unknown,
not offline; it is not a direct live port test.

## Alert behavior

A problem must persist beyond the configured grace period before it appears
and is sent as an active alert. While it persists, another notification is sent
at most after the repeat cooldown expires. Recovery sends a resolved notification
and closes the alert.

A version notice also appears as an alert, but never starts an update.
Bitcoin Core updates require an explicit administrator action.

## Configure notifications

Both channels can be enabled independently in the dashboard `.env`
(`/var/lib/bitcoin-dashboard/.env`) or at `/admin` → Dashboard configuration:

```text
ALERT_EMAIL=admin@example.com
ALERT_WEBHOOK_URL=https://monitoring.example.com/hooks/GEHEIMES-TOKEN
```

Email requires a working sendmail-compatible program, for example from an
existing Postfix installation. The webhook receives a JSON POST containing
`subject`, `message`, `host` and `timestamp`. Only HTTPS targets are accepted.

Restart the service after local configuration changes:

```bash
sudo systemctl restart bitcoin-dashboard
sudo journalctl -u bitcoin-dashboard -n 50 --no-pager
```

Active conditions are visible in the dashboard's red alert panel and at
`/api/alerts`, even without a notification channel.
