# Bitcoin Node Dashboard

[Deutsch](README.md) | English

A lightweight, read-only web dashboard for Bitcoin Core. It displays synchronization,
peers, the mempool, fee estimates, network traffic and the latest block. It also
provides host metrics, alerts and checks for new Bitcoin Core versions. BTCNodes
provides a separately identified external directory status, not our own live port test.

![Python](https://img.shields.io/badge/Python-3.11%2B-3776ab)
![Bitcoin Core](https://img.shields.io/badge/Bitcoin%20Core-31.x-f7931a)

## Features

- German and English UI with a language selector in the dashboard and admin area ([translations](docs/en/TRANSLATIONS.md)).
- No external Python packages for basic operation; real-time ZMQ optionally needs `python3-zmq`.
- Fixed, read-only RPC queries through `bitcoin-cli`; no general RPC forwarding to the browser.
- Local listener on `127.0.0.1:8787`; Bitcoin RPC and its authentication cookie stay on the server.
- External BTCNodes directory status with a five-minute cache; unlisted nodes are not treated as offline.
- SQLite history covering one hour through one year.
- Event timeline, known collection gaps and bounded read-only RPC backfill of missing block statistics.
- Chain tips from `getchaintips` as a snapshot, plus separately counted, locally observed block disconnections in the selected period.
- Optional local ZMQ block and mempool events, minute counters and live browser updates via SSE with polling fallback.
- Daily UTXO statistics, historical block sizes and confirmed transaction rates.
- Periodic mempool cluster, RBF and CPFP analysis, plus fee buckets by transactions and virtual bytes.
- Separate IPv4, IPv6 and Tor peer counts with in/out directions and addresses reported by the node; the configured public P2P IP is used as a labeled fallback.
- Peer quality by network: median connection duration and ping, most common P2P protocol version, v2 transport count and observed connections ended in the last hour. Other peers' IP addresses are not sent to the browser.
- Global server IPv6 displayed separately, even when Bitcoin Core does not report it as a P2P address.
- Tor onion address as node identity, explicitly distinguished from a Bitcoin protocol ID.
- Automatic retention and aggregation of chart data.
- Responsive desktop and mobile UI with a compact overview and separate Network, Analysis, History and System tabs.
- Systemd hardening and a Plesk reverse proxy example.
- Local web installer for systemd-based Linux servers.
- Integrated protected administration at `/admin`.
- Editable operational settings at `/admin`; `.env` in the dashboard state directory with protected confidential fields.
- Updates as isolated systemd jobs with validated helpers and rollback.
- Automatic dashboard downloads from verified GitHub release assets.
- Root-owned update cache at `/var/cache/bitcoin-dashboard-updates` rather than a user home directory.
- Bitcoin Core archive uploads with official GPG signature and SHA-256 verification.
- Docker Compose for host nodes, separate stacks and optional all-in-one nodes.
- CPU, RAM, disk and bitcoind uptime monitoring with history.
- Alerts with grace periods, repeat cooldowns, recovery messages, email and HTTPS webhooks.
- Version comparison against the official Bitcoin Core download page.

## Requirements

- Linux with Python 3.11 or newer.
- A running Bitcoin Core node with its RPC server enabled.
- Local `bitcoin-cli`.
- Service user access to the Bitcoin RPC cookie.
- Optional Plesk/Apache and an HTTPS subdomain.
- Optional `python3-zmq` and `zmqpubsequence` for real-time data.

The defaults match the original installation:

```text
User:         btc
bitcoin-cli:  /home/btc/bin/bitcoin-cli
Datadir:      /home/btc/bitcoin-data
RPC cookie:   /home/btc/bitcoin-core/.bitcoin/.cookie
Web service:  127.0.0.1:8787
P2P address:  217.160.16.224:8333
```

Dashboard configuration is stored at `/var/lib/bitcoin-dashboard/.env`, linked as
`.env` from the project directory. Operational settings can be edited through
`/admin`; protected service and RPC settings require local root access.

Container deployments can use `compose.host-node.yaml`, `compose.yaml` or
`compose.all-in-one.yaml`. See [Docker](docs/en/DOCKER.md) for differences and update commands.

## Quick installation

Check out the repository on the server:

```bash
sudo -u btc git clone https://github.com/todo1971/bitcoin-node-dashboard.git \
  /home/btc/bitcoin-dashboard
```

Configure the service using the bootstrap from a previously verified release
archive, rather than the checkout writable by `btc`:

```bash
tmpdir=$(mktemp -d)
tar -xzf ./bitcoin-node-dashboard-1.18.5.tar.gz -C "$tmpdir"
sudo sh "$tmpdir/bitcoin-dashboard/installer/bootstrap-admin.sh"
rm -rf -- "$tmpdir"
sudo systemctl enable --now bitcoin-dashboard
```

Local checks:

```bash
curl -fsS http://127.0.0.1:8787/healthz
curl -fsS http://127.0.0.1:8787/api/dashboard | python3 -m json.tool
```

See [Installation](docs/en/INSTALLATION.md) for the complete guide, including Plesk.

## Updating

```bash
cd /home/btc/bitcoin-dashboard
sudo -u btc git pull --ff-only
sudo cp bitcoin-dashboard.service /etc/systemd/system/bitcoin-dashboard.service
sudo systemctl daemon-reload
sudo systemctl restart bitcoin-dashboard
```

## HTTP endpoints

| Endpoint | Purpose |
|---|---|
| `/` | Dashboard |
| `/api/dashboard` | Aggregated node data as JSON |
| `/api/history?range=24h` | Aggregated historical samples |
| `/api/timeline?range=24h` | Events and data-quality notices for the selected period |
| `/api/analytics?range=24h` | Block, UTXO and mempool analysis |
| `/api/alerts` | Currently active alerts |
| `/api/admin/upload/bitcoin` | Protected Bitcoin Core archive upload |
| `/api/admin/logs/dashboard`, `/api/admin/logs/bitcoin` | Recent update log lines, admin authentication required |
| `/api/admin/config` | View and save permitted operational settings, admin authentication required |
| `/admin` | Password-protected administration |
| `/healthz` | Local functionality and RPC check |

There is no endpoint that accepts arbitrary Bitcoin Core RPC methods or arguments.

## Documentation

- [Installation and operation](docs/en/INSTALLATION.md)
- [Architecture](docs/en/ARCHITECTURE.md)
- [Database and data volume](docs/en/DATABASE.md)
- [Web installation](docs/en/WEB_INSTALLATION.md)
- [Docker](docs/en/DOCKER.md)
- [All-in-one shell installation](docs/en/SHELL_DOCKER.md)
- [All-in-one with Plesk](docs/en/PLESK_DOCKER.md)
- [Secure updates](docs/en/UPDATES.md)
- [Alerts and system monitoring](docs/en/ALERTS.md)
- [Configuration and .env migration](docs/en/CONFIGURATION.md)
- [Real-time local ZMQ and SSE](docs/en/REALTIME.md)
- [Security](docs/en/SECURITY.md)
- [Languages](docs/en/TRANSLATIONS.md)
- [Test coverage and public updates](docs/en/TESTING.md)
- [GitHub Packages / container images](docs/en/PACKAGES.md)
- [Roadmap](docs/en/ROADMAP.md)
- [Full changelog](CHANGELOG.en.md)

## Development and tests

```bash
python3 -m py_compile app.py
python3 -m unittest discover -s tests -v
python3 tools/check_documentation.py
```

## License

Copyright (C) 2026 Hardy (todo1971) <hb@308-arms.de>. Original project code and documentation are
licensed under the **GNU General Public License, version 3 only**
(`GPL-3.0-only`). Full text: [LICENSE](LICENSE); notices: [NOTICE](NOTICE).
The program is provided without warranty. Third-party components, including
Bitcoin Core, Python and base images, retain their respective licenses.
