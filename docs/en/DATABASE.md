# Database and data volume

[Deutsch](../DATABASE.md) | [English documentation](../../README.en.md#documentation)

## Why SQLite?

The dashboard has exactly one writing process. At 60-second sampling intervals
it produces about 1,440 samples per day or 525,600 per year, well within a
reasonable SQLite workload. Adding MariaDB for this volume would increase
administration, user management, network exposure and backup work without
a measurable advantage.

The database uses WAL mode, so chart queries do not block ongoing sampling.
Retention defaults to 365 days.

## Schema

For each sample, `node_samples` contains:

- Block height and synchronization progress.
- Used blockchain storage.
- Peer counts by direction.
- Mempool transaction count, size and memory usage.
- Mempool minimum fee.
- Fee estimates for 2, 6 and 12 blocks.
- Cumulative network traffic.
- Transactions and total fees of the latest block.
- Latest block size and confirmed transaction rate.
- CPU and RAM utilization.
- Free space on the Bitcoin data directory filesystem.
- bitcoind process uptime.

`alert_states` tracks alert start, active state and last notification,
preserving grace periods and cooldowns across dashboard restarts.

`dashboard_events` stores the public event timeline: timestamp, type and a
short address-free message. `dashboard_meta` remembers the last dashboard
version so changes can be detected. `block_observations` stores block statistics
by height. If blocks are missed between samples, at most twelve recent heights
per cycle are backfilled with `getblockstats`. Larger gaps or unavailable RPC
data remain visible as data-quality notices. This does not reconstruct historical
mempool ZMQ events. Reorganizations are marked on the timeline, but previously
stored statistics at a given height are not an immutable chain history.

`utxo_samples` stores the UTXO count, block height, database size and total
amount from `gettxoutsetinfo none`, by default at most daily. Mode `none`
avoids expensive UTXO set hash calculation. Change the interval with
`UTXO_SAMPLE_SECONDS`.

Mempool analysis is not permanently stored. It groups current parent/child
relationships into clusters and identifies RBF-eligible transactions and CPFP
candidates whose child fee rate exceeds the parent's. The same
`getrawmempool true` response produces the fee distribution: individual
transaction rates `fees.base / vsize` are placed into fixed sat/vB buckets,
showing counts and summed virtual bytes. Missing or invalid values are counted
separately. This local snapshot does not represent effective CPFP package rates.
It refreshes at most every five minutes by default
(`MEMPOOL_ANALYSIS_SECONDS`); transaction IDs are not stored.

The API does not send half a million raw samples to the browser. It aggregates
into fixed time buckets according to the selected period:

| View | Bucket | Approximate maximum |
|---|---:|---:|
| 1 hour | 1 minute | 60 points |
| 6 hours | 2 minutes | 180 points |
| 12 hours | 5 minutes | 144 points |
| 24 hours | 5 minutes | 288 points |
| 7 days | 30 minutes | 336 points |
| 30 days | 2 hours | 360 points |
| 1 year | 1 day | 365 points |

## Backup

Use SQLite's backup function for a consistent online backup:

```bash
sudo -u btc sqlite3 /var/lib/bitcoin-dashboard/history.sqlite3 \
  ".backup '/var/lib/bitcoin-dashboard/history-backup.sqlite3'"
```

## When MariaDB makes sense

Consider switching if several nodes write concurrently, sampling happens multiple
times per second, multiple dashboard processes run in parallel or external
analysis tools continuously run complex queries. The API already separates
collection from presentation so an alternative storage backend can be added later.
