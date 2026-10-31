# Changelog

[Deutsch](CHANGELOG.md) | English

All significant project changes are recorded here.

## 1.18.2 – 2026-10-31

- Add tests and bilingual documentation for anonymous version discovery and package downloads from public GitHub releases.
- Add a read-only live check for public release metadata and small checksum assets.
- Replace outdated Compose versions with consistent image and build versions; exclude local previews from Docker build context.
- Extend CI with separate-container runtime checks, language-asset checks and unauthenticated admin-access checks.
- Record local testing limits without Docker installed and pre-publication findings.

## 1.18.1 – 2026-10-31

- Add English editions of the README, the full historical changelog and all 14 documentation pages.
- Link German and English editions in both directions.
- Include English README and changelog files in dashboard updates when the updated root helper is installed.
- Add documentation checks for language pairs, links, changelog versions and unchanged command examples; align outdated nginx, external-status and signature-count guidance.

## 1.18.0 – 2026-10-31

- Add German and English language catalogs under `static/locales/`.
- Add a dashboard and admin language selector, saved locally in the browser.
- Translate static labels and known dynamic status messages; format numbers and dates for the selected language.
- Preserve original logs, technical diagnostics and input values. Unknown messages fall back to German.
- Serve language files through a fixed public URL allowlist; admin authentication remains required.

## 1.17.0 – 2026-10-10

- Reduce the home page to node status, synchronization, connections and alerts.
- Split Network, Analysis, History and System into separate keyboard-accessible tabs.
- Preserve existing metrics and data sources; redraw charts at the visible width when opening their tab.
- Adapt tabs and period selectors for narrow displays.

## 1.16.0 – 2026-10-10

- Show the active chain tip and up to twelve other tips with status, height, branch length and block hash from `getchaintips`.
- Count all alternative tips by status; cache RPC responses for 60 seconds.
- Separately count ZMQ-observed block disconnections in the selected period and show the latest time.
- Explicitly distinguish snapshots from observed events; missing events during outages are not evidence of zero reorganizations.

## 1.15.0 – 2026-10-10

- Identify BTCNodes status as an external directory entry; `found=false` means unknown rather than “node offline” and does not trigger a port alert.
- Show mempool fee distribution in sat/vB with transaction counts and virtual bytes.
- Calculate fee buckets from the existing periodically cached `getrawmempool true` response, without an extra RPC call or storing individual transaction IDs.
- Count missing fee data separately and explain the limitations of individual transaction fee rates compared with CPFP package rates.

## 1.14.0 – 2026-10-01

- Add a public event timeline for blocks, alert transitions, node/dashboard restarts, major peer drops and dashboard version changes.
- Record ZMQ sequence gaps, connection interruptions and block statistics not backfilled as data-quality notices.
- Backfill at most twelve recent missed block statistics per cycle using read-only RPC; explicitly mark larger or unavailable gaps.
- Add `/api/timeline?range=24h`, linked to the history period, and mark interruptions in charts.
- Stop displaying missing chart values as zero and stop joining lines across sampling gaps.

## 1.13.0 – 2026-09-30

- Migrate systemd configuration from `/etc/default/bitcoin-dashboard` to the dashboard state directory's `.env`.
- Edit allowed settings at `/admin`, validate them, save atomically and restart the dashboard after a short delay.
- Show GitHub tokens only as configured/unconfigured; keep admin tokens and internal paths protected.
- Retain the old configuration location as a migration fallback copy.

## 1.12.0 – 2026-09-30

- Add an optional local `zmqpubsequence` subscriber counting block/mempool events and transport sequence gaps.
- Store minute counters in SQLite without transaction or block hashes.
- Update the browser through Server-Sent Events, retaining periodic polling as fallback.
- Move Telegram notifications to the roadmap for later implementation.

## 1.11.9 – 2026-09-30

- Add connection duration, ping, protocol version, v2 transport and ended connections by IPv4/IPv6/Tor.
- Exclude short-lived test connections from peer-change counts; node restarts reset counters.
- Document boot and service checks for bitcoind, Tor and the dashboard.

## 1.11.8 – 2026-09-30

- Show the latest admin update run as green “OK”, red “Not OK” or “Running”.
- Restrict output to the latest started update run.

## 1.11.7 – 2026-09-30

- Display dashboard and Bitcoin Core update journals directly at `/admin`, refreshed every five seconds.
- Limit journal access to two fixed units, 80 lines and a 32 KiB response.
- Document the one-time bootstrap for the new sudoers read permission.

## 1.11.6 – 2026-09-30

- Move update packages into a root-owned cache under `/var/cache`.
- Migrate existing updater configuration when rerunning bootstrap.
- Remove old home-directory paths from guides, examples and tests.

## 1.11.5 – 2026-09-30

- Show the complete Tor onion address as node identity in Node & Version.
- Explicitly distinguish it from a permanent Bitcoin protocol ID.

## 1.11.4 – 2026-09-30

- Also display globally routable IPv6 addresses from server network interfaces.
- Distinguish server IPs from Bitcoin Core-reported P2P addresses.

## 1.11.3 – 2026-09-30

- Label peer directions as `in` and `out`.
- Show Bitcoin Core-reported IPv4 and IPv6 addresses alongside the onion address; label the configured public P2P IP as fallback when absent.

## 1.11.2 – 2026-09-30

- Organize the home page into Node & Version, Network, System, and Statistics & Analysis.
- Move metrics into the appropriate sections and adjust card widths.

## 1.11.1 – 2026-09-30

- Show inbound and outbound connections separately for IPv4, IPv6 and Tor.
- Display the node's reported onion address.

## 1.11.0 – 2026-09-29

- Add daily UTXO statistics through `gettxoutsetinfo none`.
- Store historical block sizes and confirmed transaction rates.
- Add periodic mempool cluster, RBF eligibility and CPFP candidate analysis.
- Add an analysis view with metrics, charts, UTXO table and glossary.
- Add the `/api/analytics` JSON endpoint.

## 1.10.0 – 2026-09-29

- Add a secure shell installer for the all-in-one deployment.
- Support `--prepare-only` without starting services or changing service state.
- Add a Plesk guide for Compose stacks and Apache-only systems.
- Add a separate Apache template for the locally bound container dashboard.
- Protect existing services by checking occupied ports.

## 1.9.0 – 2026-09-29

- Add an optional all-in-one Bitcoin Core and dashboard container.
- Run both processes as an unprivileged user in the same container.
- Use a shared persistent volume with separate data directories.
- Keep RPC on container loopback only.
- Add combined health checking and orderly shutdown of both processes.

## 1.8.2 – 2026-09-29

- Wait up to 30 seconds for health checks following a restart.
- Avoid unnecessary rollback while Python is still opening its HTTP port.
- Check the restored service following rollback.

## 1.8.1 – 2026-09-29

- Run root updater Python tests with a separate bytecode directory writable by the unprivileged user.
- Fix `Permission denied: __pycache__` during dashboard updates.

## 1.8.0 – 2026-09-29

- Add a hardened dashboard image and Docker Compose files.
- Provide variants for an existing host node and a complete new Docker stack.
- Add direct JSON-RPC access with cookie authentication.
- Run containers without Docker socket access, host systemd, Linux capabilities or root.
- Disable integrated root updates in container mode and explain the limitation.
- Use a fixed Bitcoin Core version rather than uncontrolled `latest`.

## 1.7.0 – 2026-09-29

- Upload Bitcoin Core archives at `/admin` using file selection or drag and drop.
- Limit uploads to 200 MB, stable Linux filenames and the matching server architecture.
- Stage archives without root privileges in a fixed StateDirectory path.
- Download `SHA256SUMS` and `SHA256SUMS.asc` exclusively from `bitcoincore.org`.
- Verify GPG, SHA-256, platform, version and downgrade protection before stopping the node.
- Remove successful uploads while retaining backups and rollback.
- Add reverse proxy examples for large, slower uploads.

## 1.6.2 – 2026-09-28

- Allow user `btc` to traverse the temporary update directory for tests.
- Keep write permissions restricted to root.
- Add a regression test for directory access being granted before tests.

## 1.6.1 – 2026-09-28

- Document setup of a minimally privileged fine-grained GitHub token.
- Describe secure storage, checks, expiration and revocation.
- Document the planned signature-verified admin Bitcoin Core upload.

## 1.6.0 – 2026-09-28

- Discover the latest dashboard release through the GitHub Releases API.
- Support private repositories with a read-only fine-grained token.
- Download the release archive and separate SHA-256 file and verify before installation.
- Display installed and latest dashboard versions at `/admin`.
- Retain a parameterless, narrowly scoped root update job with backup and rollback.

## 1.5.2 – 2026-09-28

- Remove systemd options that indirectly enabled `NoNewPrivileges`.
- Allow integrated update jobs to use the exact permitted sudo rules.

## 1.5.1 – 2026-09-28

- Enforce Linux line endings for all shell scripts in release archives.

## 1.5.0 – 2026-09-28

- Integrate administration at `/admin`.
- Remove the separate permanently running admin web service.
- Add strong Basic authentication, CSRF checks and login lockout.
- Limit admin POST types and sizes and block cross-origin requests.
- Permit only two exact parameterless update jobs through `sudo`.
- Run updates as isolated transient systemd services.
- Remove the old admin service installation during bootstrap.

## 1.4.2 – 2026-09-28

- Express the disk-space alert as 90 percent used.
- Add `DISK_MAX_USED_PERCENT`.
- Keep `DISK_MIN_FREE_PERCENT` as a compatible fallback.

## 1.4.1 – 2026-09-28

- Change disk cards and history from free to used space.
- Keep the alert threshold equivalent to less than 10 percent free.

## 1.4.0 – 2026-09-28

- Add alerts for RPC outages, sync lag and missing inbound peers.
- Measure CPU, RAM, disk space and bitcoind uptime.
- Add system metrics to SQLite history and charts.
- Add optional local sendmail and HTTPS webhook notifications.
- Check versions against the official Bitcoin Core release index.
- Add alert grace periods, repeat cooldowns and recovery messages.

## 1.3.0 – 2026-09-28

- Add a local token-protected web installer and a separate local maintenance UI.
- Add dashboard updates with tests, backups, health checks and rollback.
- Add Bitcoin Core updates with GPG and SHA-256 verification.
- Add example configuration for new Bitcoin nodes.
- Restrict update privileges to two fixed root helpers.

## 1.2.1 – 2026-09-28

- Add 1-, 6- and 12-hour history views.
- Use hour/minute axes for short periods.

## 1.2.0 – 2026-09-28

- Add SQLite history in WAL mode.
- Make sampling intervals and retention configurable.
- Add peer and fee estimate charts with fixed periods from 24 hours to one year.
- Configure systemd StateDirectory for persistent data.
- Add database tests.

## 1.1.0 – 2026-09-28

- Add external reachability checks through BTCNodes.
- Add direct BTCNodes and Bitnodes search links.
- Make public address and port configurable.
- Limit external queries to once every five minutes.
- Add browser security headers.
- Establish documentation and CI structure.

## 1.0.0 – 2026-09-28

- Initial read-only dashboard.
- Node, network, mempool, fee and block data.
- Systemd service and Plesk reverse proxy example.
