# Peer analysis and network traffic

[Deutsch](../NODE_INSIGHTS.md) | English

Since version 1.20.0, **Network** contains traffic rates and the collapsed
**Peer software and capabilities** tables. **History** shows Bitcoin Core
traffic by calendar day. **Analysis** lists the last 20 locally recorded blocks.
Functions through 1.23 require no additional RPC methods; block utilization since 1.25 requires `getblock`.

## Charts since 1.25

**Network → Traffic by message type** contains stacked received/sent charts (decimal KB/s) and recorded byte totals for the selected range. Groups:

- Blocks: `block`, `cmpctblock`, `blocktxn`, `getblocktxn`.
- Transactions: `tx`.
- Announcements and requests: `inv`, `getdata`, `notfound`, `getblocks` (mixed content; `getblocks` requests block inventory).
- Block headers: `headers`, `getheaders`.
- Other messages: all remaining types, including protocol management.

Once per sampling interval, `getpeerinfo` and `uptime` are read. Deltas require matching peer IDs and connection start times, nondecreasing individual counters and consistent Core uptime. Restarts and excessive gaps are not bridged. New, disconnected or incomparable connections are excluded. Connections created and closed entirely between samples are also missed. These values are therefore a recorded subset of P2P application traffic, not complete node or provider traffic. Zero means measured inactivity; unknown values remain empty.

Only aggregated groups are stored in `message_traffic_samples`. Peer identities remain in the volatile comparison baseline; IP addresses are neither stored nor published for this feature. Dashboard restarts require two new samples. Chart buckets containing invalid samples remain unknown. Rates are weighted by valid measurement duration; boundary intervals are not invented proportionally. Totals may contain valid subintervals even when a chart bucket is unknown.

**Analysis → Fee bands and block utilization** shows transaction-weight-weighted P10/P25/P50/P75/P90 fee rates from `getblockstats` in sat/vB. P50 is the median; P10–P90 and P25–P75 appear as colored bands. These are confirmed fees, not recommendations or predictions. The last recorded block in each chart bucket is selected; percentiles are never averaged.

Full weight from `getblock` includes the coinbase transaction. Utilization = weight / 4,000,000 × 100%. `getblockstats.total_weight` alone would exclude coinbase. Missing or pruned blocks remain unknown. Existing observations are not given invented history; the current block can be enriched. The global range selector under **History** applies to both new views.

### Setup and updating

Rerun root bootstrap from the verified current release to allow the new read method `getblock`; see [security migration](SECURITY.md). It extends the existing RPC permissions without replacing credentials and only restarts local Core when the permissions change; the dashboard is also restarted. A dashboard-only update can collect fee bands, but block utilization remains unknown without the new permission. Remote nodes need the permission on their own host. No additional Python or system packages are needed. Containers with full cookie credentials need no additional RPC permission; extend restricted accounts accordingly.

## Peer details

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
by at most five seconds. The purple peak line shows the highest valid upload
rate between two samples for each day.

**Bitcoin Core traffic by day** shows download, upload, time-weighted connection
count, peak upload and coverage per calendar day. Volumes use decimal units
with 1 GB = 1,000 MB. The table follows the selected
range and the displayed browser time zone. Partial days show the portion within
the selected range. Intervals crossing boundaries are omitted. Daylight saving
transitions can make a day 23 or 25 hours long. Measurement coverage is
valid measured seconds divided by the elapsed period duration. Missing samples,
retention limits, and offline nodes can reduce coverage. Totals are not billing
records or a substitute for provider traffic data. Counters and uptime alone
cannot detect every theoretically possible restart.

### Weekly comparison and CSV report

The expandable weekly comparison covers the last seven completed calendar days
and the preceding seven days. It excludes today. Each period shows measured
download and upload, upload per day (measured upload divided by seven), the
highest measured upload day and time coverage. The upload percentage change
requires at least 90% coverage in both periods and a positive comparison value.
Missing data can reduce the measured volumes.

**Download CSV report** exports the days in the selected history range.
The UTF-8 download includes byte volumes, peak bytes per second, peer counts,
measurement duration, IPv4/IPv6/Tor averages and recorded block statistics.
Column names are language-independent English. Numbers use a decimal point
and unknown values remain empty. Time boundaries are local ISO timestamps
including UTC offset and time zone name. The export uses the data already loaded.

### Network history and daily block statistics

In History, **Network history** provides one chart each for IPv4, IPv6 and Tor
with In and Out. Values are average counts of saved snapshots per chart bucket.
Six additional nullable SQLite columns record these counts from version 1.23.0.
Earlier samples retain unknown network values. Known gaps break the lines.

**Daily block statistics** is available in Analysis. Each stored block height
counts once. The table groups by block time in the browser's time zone and shows
recorded blocks, transaction totals, average block size and total fees.
A missing individual value makes the corresponding daily metric unknown.
The table covers locally stored observations in the selected period.
Backfill limits and reorganizations constrain completeness.

`GET /api/traffic?range=24h` accepts the same seven ranges as history. Unknown
values fall back to 24h. The optional `timezone` parameter accepts an IANA time
zone such as `Europe/Berlin`. The API uses UTC if the zone is absent or invalid.
Existing range, day and month totals and finer rates remain available via the API.
SQLite calculates differences and buckets. The latest result per range is cached
for 30 seconds. The API does not read individual peer
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

## Known addresses and connected peers since 1.26

Under **Network**, independent bars compare `New` (address candidates), `Tried` (previously connected successfully) and active connections. Total stored addresses are also shown. These are P2P addresses, not unique node IDs: one node may have multiple addresses, and connections are not a third address group to add to New and Tried. Tried does not prove current reachability.

Data comes from `getaddrmaninfo` and `getnetworkinfo`, once per sampling interval. `all_networks` is used as the total and never added again to network subtotals. Older responses without this field are summed from fully readable known network groups. Only counts are retained, never addresses or peer IDs.

Two history charts use separate scales: address inventory (New/Tried) and active connections. Each bucket shows the arithmetic mean of recorded samples. A missing value makes its series unknown for that bucket. Zero is valid. Bars use only the latest sample; after more than three sampling intervals (at least 180 seconds), they are marked stale and no longer displayed as current. The History range selector applies here too.

Follow the [root bootstrap instructions](SECURITY.md) from the verified current release. Bootstrap adds `getaddrmaninfo` to the existing restricted RPC account, preserves its password and restarts Core when permissions change. The dashboard is also restarted. Remote nodes need this read permission on their own host. Without it, address counts remain unknown while active connections can still be recorded. No additional packages or blockchain index are required.
