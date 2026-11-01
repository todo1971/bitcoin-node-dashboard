# Roadmap

[Deutsch](../ROADMAP.md) | [English documentation](../../README.en.md#documentation)

## Implemented in 1.20

- Aggregate peer software versions, service flags, and connection types.
- Traffic rates and measured period/day/month totals with coverage.
- Last 20 locally recorded blocks.

## Implemented in 1.2

- Regular SQLite sampling.
- Charts for 1, 6, 12 and 24 hours, 7 days, 30 days and 1 year.

## Implemented in 1.3

- Local web installer.
- Separate maintenance panel through an SSH tunnel.
- Dashboard and Bitcoin Core update helpers.
- Backups, health checks and automatic rollback on startup failures.

## Implemented in 1.5

- Administration integrated at `/admin`.
- Separate admin web service removed.
- Authentication, CSRF protection, rate limiting and fixed transient update jobs.

## Implemented in 1.6

- Discover the latest dashboard version through GitHub Releases.
- Automatically download release archives and verify SHA-256.
- Support private repositories with a minimally privileged fine-grained token.

## Implemented in 1.7

- Upload official Bitcoin Core archives by file selection or drag and drop.
- Automatically download checksums and signatures from `bitcoincore.org`.
- Verify platform, version, signatures and downgrade protection before root updates.

## Implemented in 1.8

- Hardened dashboard container image.
- Compose variant for an existing host node.
- Optional complete stack with Bitcoin Core and a private RPC network.
- Direct JSON-RPC without `bitcoin-cli` in the dashboard container.

## Implemented in 1.9

- Optional shared Bitcoin Core and dashboard container.
- Combined RPC and web health check.
- Controlled shutdown of both processes with sufficient grace time.

## Implemented in 1.10

- All-in-one shell installer with preparation and execution modes.
- Plesk installation as a stack or behind Apache without nginx.
- Protection against occupied ports and unsafe symbolic links.

## Implemented in 1.4

- Alerts for node outages, sync lag and missing inbound peers.
- Disk, CPU, RAM and process uptime monitoring.
- Bitcoin Core version checks.

## Next stage

- Implemented in 1.13: edit selected operational settings in the dashboard `.env` through `/admin`.
- Implemented in 1.14: event timeline, known collection gaps and bounded block RPC backfill.
- Implemented in 1.15: correctly identify BTCNodes as directory information and show local mempool fee distribution.
- Prometheus endpoint for external long-term monitoring.
- Optionally edit separate alert thresholds in the maintenance panel.
- More notification channels such as Telegram or ntfy.

## Network diagnosis

- Preserve ended-connection history across dashboard restarts.
- Mask peer addresses in public views.
- Implemented in 1.16: separately show `getchaintips` snapshots and ZMQ-observed block disconnections.
- Compare external reachability across multiple independent observers.

## Real time

- Implemented in 1.12: receive new blocks and mempool events through local `zmqpubsequence`.
- Implemented in 1.12: browser updates via SSE with polling fallback.
- Later: Telegram notifications; email and webhooks already exist.

## Advanced analysis

- Daily UTXO statistics.
- Historical block sizes, fees and transaction rates.
- Mempool cluster and RBF/CPFP package analysis.
- Prometheus endpoint and optional Grafana dashboards.

## Separate major projects

- Dedicated mempool/block explorer.
- Electrum server or Electrs indexer.
- Watch-only address monitoring.
- P2P anomaly detection with Bitcoin Core tracepoints.

A full explorer requires substantially more storage and indexes than the current
dashboard. Historical queries on a pruned node are limited.
