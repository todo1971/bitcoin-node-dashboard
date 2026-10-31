# Real-time Bitcoin Core ZMQ

[Deutsch](../REALTIME.md) | [English documentation](../../README.en.md#documentation)

The dashboard can receive block and mempool events from `zmqpubsequence`.
The ZMQ endpoint is **local only**; the browser connects exclusively to the
dashboard (`/api/events`, Server-Sent Events). Without ZMQ, periodic polling
remains active.

## Enable on the host

1. Install Python bindings: `sudo apt install python3-zmq`. The package must
   be available to the dashboard service's Python interpreter.
2. Add `zmqpubsequence=tcp://127.0.0.1:28332` to the **active** `bitcoin.conf`.
   Check the actual path against Bitcoin Core's startup arguments.
3. At `/admin` → Dashboard configuration, enter local ZMQ endpoint
   `tcp://127.0.0.1:28332`, or add it to `/var/lib/bitcoin-dashboard/.env`.
4. Schedule a Bitcoin Core restart, then restart the dashboard. First check
   service names with `systemctl list-units '*bitcoin*'`; do **not** assume
   `bitcoind.service`. Expect a brief interruption when restarting Core.
5. Check:

   ```sh
   sudo -u btc /home/btc/bin/bitcoin-cli -datadir=/home/btc/bitcoin-data -rpccookiefile=/home/btc/bitcoin-core/.bitcoin/.cookie getzmqnotifications
   ss -lntp | grep 28332
   curl -N http://127.0.0.1:8787/api/events
   curl -s http://127.0.0.1:8787/api/realtime
   ```

`getzmqnotifications` should report `pubsequence` at `tcp://127.0.0.1:28332`.
The SSE test produces `: connected` followed by regular heartbeats.
Behind Plesk/Apache, also test the public HTTPS `/api/events` path with
`curl -N`; proxy layers may buffer streams or limit connections.

## Meaning and limitations

- `block_connected` and `block_disconnected` count connected and disconnected blocks; a reorganization is possible.
- The chain tip view calls `getchaintips` at most once per minute. Alternative tips may be old branches and do not count new reorganizations. The separate disconnected-block counter includes only locally observed ZMQ events during dashboard operation in the selected period; interruptions make it incomplete.
- `mempool_added` and `mempool_removed` count events, not the current mempool population. Removal because a transaction was mined is not an `R` event.
- Dashboard tiles show the current minute, stored in SQLite. Transaction and block hashes from the ZMQ stream are not stored.
- The four-byte transport sequence detects gaps **during a running subscriber connection**. Restarts, broken connections and initial subscription can lose events without a reliably detectable sequence gap. The event timeline marks detected sequence gaps, connection interruptions and dashboard starts. Past mempool event counters are **not** reconstructed retrospectively; missed block statistics are backfilled separately through bounded RPC queries.
- When SSE fails, the UI falls back to periodic polling. At most twelve simultaneous SSE connections are allowed.
- ZMQ publishers do not authenticate subscribers. **Never** bind them to `0.0.0.0` or a public address.

Telegram remains a future extension on the roadmap.
