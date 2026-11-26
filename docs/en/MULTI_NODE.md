# Multiple Bitcoin nodes

[Deutsch](../MULTI_NODE.md) | English

Since version 1.27 one public dashboard can display multiple independent nodes.
The selector above the tabs reloads the page with `?node=ID`.
The active tab and language are preserved when switching nodes.

## Collection

Each node server runs its own dashboard instance as a collector.
It queries its local Bitcoin Core and stores samples in its own SQLite database.
CPU, memory and disk statistics therefore belong to the selected server.
Existing histories are kept separate. A new collector starts its history when
installed. An unavailable collector displays an error and unknown values.

The public primary server forwards public read requests and SSE events only.
Administration and updates apply to the primary node. The administration link is
hidden in remote node views. Operators update remote collectors over SSH.

## Connection

Both the collector and Bitcoin RPC listen on loopback only. A persistent SSH
tunnel forwards a local port on the primary server to the remote collector port.
The RPC port is kept private and is not forwarded. The collector requires a
dedicated RPC account with the read methods listed in [Security](SECURITY.md).
Its environment contains `ADMIN_UPDATES_ENABLED=0`, an empty `ADMIN_TOKEN`,
`BITCOIN_RPC_URL=http://127.0.0.1:8332` and `BITCOIN_COOKIE` pointing to its
protected RPC credentials file. `BITCOIN_DATADIR`, `DISK_MONITOR_PATH` and
`PUBLIC_NODE_ADDRESS` refer to the remote node. Optional ZMQ also stays local.

The supplied [collector service](../../installer/bitcoin-dashboard-collector.service)
uses the `bitcoin-dashboard` service user, root-owned code at
`/opt/bitcoin-dashboard` and writable state at `/var/lib/bitcoin-dashboard`.
The account needs neither sudo permissions nor access to the full Core cookie.
Python 3.11 or newer, CA certificates, systemd and OpenSSH are required.
PyZMQ is optional.

Use a dedicated SSH key pair and tunnel account. Restrict its public key with
`restrict,port-forwarding,permitopen="127.0.0.1:8787"`. In an SSH server
`Match User` block set `AllowTcpForwarding local`, `PermitTTY no` and
`AllowAgentForwarding no`. Verify and pin the server host key in advance with
`StrictHostKeyChecking=yes`. The private tunnel key stays on the primary server
and is unreadable to the dashboard process. SSH passwords do not belong in any
dashboard configuration.

Example tunnel process, managed by systemd with failure restart and automatic
startup after a server reboot. The key files belong to the separate tunnel account.

```sh
ssh -NT -o BatchMode=yes -o StrictHostKeyChecking=yes \
  -o ExitOnForwardFailure=yes -o ServerAliveInterval=30 \
  -o ServerAliveCountMax=3 \
  -o UserKnownHostsFile=/var/lib/bitcoin-node-tunnel/known_hosts \
  -i /var/lib/bitcoin-node-tunnel/id_ed25519 \
  -L 127.0.0.1:18787:127.0.0.1:8787 bitcoin-node-tunnel@NODE_HOST
```

## Configure the primary server

`/etc/bitcoin-dashboard/nodes.json` is owned by root and readable by the dashboard
user. `DASHBOARD_NODES_FILE` can select a different path. Administrators manage
this infrastructure file outside the web editor. Updaters preserve it.

```json
{
  "local_name": "Primary node",
  "nodes": [
    {
      "id": "second",
      "name": "Second node",
      "url": "http://127.0.0.1:18787"
    }
  ]
}
```

IDs must be unique and use lowercase letters, digits and hyphens, starting with
a letter. `local` is reserved. Up to 16 additional nodes are supported. URLs must
be HTTP loopback addresses with an explicit port. Public URLs, embedded
credentials and redirects are rejected. Without the file the existing
single-node view is retained. File changes take effect on the next request.

`/api/nodes` returns IDs and display names only. `/api/nodes/ID/history` and the
other allowed public read endpoints return the collector's data. Internal URLs
and RPC credentials are not exposed. Forwarding ignores client cookies and
Authorization headers, caps JSON responses at 4 MiB and allows up to eight
simultaneous remote SSE streams. Timeouts and request rate limits also apply to
remote requests. Aggregated measurements from all configured nodes are visible
on the public dashboard. Individual peer addresses are not exposed by this feature.

## Verify

```sh
curl --fail http://127.0.0.1:18787/healthz
curl --fail http://127.0.0.1:8787/api/nodes
curl --fail http://127.0.0.1:8787/api/nodes/second/dashboard
curl --fail 'http://127.0.0.1:8787/api/nodes/second/history?range=1h'
```

Check that each server's database receives new samples. The first collection may
take a few seconds. During Initial Block Download, fee and mempool analyses may
remain incomplete depending on Core state. Remote administration, POST requests
and unknown node IDs must fail.

Copyright (C) 2026 Hardy (todo1971) <hb@308-arms.de>
