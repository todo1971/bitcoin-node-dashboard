# Peer analysis and network traffic

[Deutsch](../NODE_INSIGHTS.md) | English

Since version 1.20.0, **Network** contains traffic rates and the collapsed
**Peer software and capabilities** tables. **History** shows traffic rates and
measured totals. **Analysis** lists the last 20 locally recorded blocks.
No additional RPC methods are required.

## Peers

Client names and software versions come from `getpeerinfo.subver`, rather than
the P2P protocol number. At most twelve client groups and a remainder group are
shown. Free-form comments and other peers' addresses are not published.
These values are self-reported, not verified software fingerprints.

Service flags advertise capabilities: NETWORK (full block history),
NETWORK_LIMITED (recent blocks), WITNESS (SegWit), BLOOM (Bloom filters),
COMPACT_FILTERS (compact block filters), P2P_V2 (encrypted transport).
A peer can advertise multiple capabilities, so the sum of flag counts may exceed
the number of peers. P2P_V2 means support; the existing transport-v2 display
instead counts connections actually using transport v2.

Connection types distinguish In, Out using full relay or block relay, manual
connections, and short-lived feeler/address-fetch connections. Unknown or
privacy-sensitive additional types are grouped rather than named individually.
The analysis uses existing snapshots and does not retain individual peer histories.

## Traffic and data quality

Live rates in KiB/s are differences of Core's `getnettotals` counters divided by
the time between two queries. The first query, missing values, decreasing counters,
a detected restart, or an excessive time gap produce **unknown**, not zero.
Zero means a valid measured interval without traffic. The existing cumulative
counters cover the time since Core last started.

History uses existing SQLite samples. Only intervals up to
`max(120, 3 × SAMPLE_INTERVAL_SECONDS)` seconds with continuous Core uptime and
nondecreasing counters count. The uptime change may differ from the sample interval
by at most five seconds. A chart bucket containing an invalid interval has an
unknown rate. Valid rates are weighted by measured duration.

Totals for the selected period, today, and the current month include only measured
intervals wholly within each period. Days and months start at 00:00 UTC; intervals
crossing boundaries are omitted rather than estimated. Measurement coverage is
valid measured seconds divided by the elapsed period duration. Missing samples,
retention limits, and offline nodes can reduce coverage. Totals are not billing
records or a substitute for provider traffic data. Counters and uptime alone
cannot detect every theoretically possible restart.

`GET /api/traffic?range=24h` accepts the same seven ranges as history; unknown
values fall back to 24h. SQLite calculates differences and buckets; at most seven
results are cached for 30 seconds each. The API does not read individual peer
addresses or allow caller-selected RPC methods.

## Recorded blocks

`GET /api/recent-blocks` returns at most 20 saved `block_observations`, ordered by
descending height: block time, transactions, size, and fees in BTC. Missing values
remain unknown. Existing recording and its limited backfill determine coverage;
new installations initially show fewer blocks. This table is not a complete
explorer or an immutable reorg history.

This implementation was developed independently using existing data and official
Bitcoin Core RPC interfaces. No third-party dashboard code is incorporated.

[Back to overview](../../README.en.md)
