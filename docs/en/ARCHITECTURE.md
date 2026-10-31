# Architecture

[Deutsch](../ARCHITECTURE.md) | [English documentation](../../README.en.md#documentation)

```text
Browser
   | HTTPS
   v
Plesk / Apache reverse proxy
   | HTTP on 127.0.0.1:8787
   v
Python dashboard (user btc)
   +-- bitcoin-cli --> local Bitcoin Core RPC
   +-- SQLite ------> /var/lib/bitcoin-dashboard/history.sqlite3
   +-- HTTPS -------> public BTCNodes API / Bitcoin Core version
   +-- /admin ------> precisely defined transient systemd update job
                              |
                              +-- root-owned, parameterless update helper
```

## Local data

The dashboard only executes a fixed list of read-only calls:

- `getblockchaininfo`
- `getnetworkinfo`
- `getmempoolinfo`
- `getnettotals`
- `getpeerinfo`
- `getblockstats`
- `estimatesmartfee`
- `getblockcount` for health checks
- `uptime`

The browser cannot specify RPC methods or arguments. Responses are cached for
ten seconds so concurrent browser requests do not unnecessarily load the node.

## Administration

Administration runs in the same HTTP process, with separate strong authentication,
CSRF and origin checks, and login lockout. The browser can choose only the
`dashboard` or `bitcoin` action, mapped internally to two immutable command sequences.

Privileged work runs in a transient systemd service. Sudoers permits only those
two complete calls for the dashboard user. Root-owned helpers take no arguments
and read packages from fixed configured directories not writable by `btc`.

## External data

The public view queries only the configured address at `btcnodes.io`.
Results are cached for at least five minutes. External service outages do not
affect local node data.

## Historical data

A background thread stores one sample per minute in SQLite by default. HTTP
requests open their own short-lived connections. WAL mode and `busy_timeout`
allow reads during sampling. Systemd makes the remaining filesystem read-only;
only StateDirectory is writable.
