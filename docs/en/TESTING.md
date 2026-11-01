# Test coverage and public updates

[Deutsch](../TESTING.md) | [English documentation](../../README.en.md#documentation)

## Local environment on October 31, 2026

The inspected Windows machine has no Docker Desktop, Docker CLI or WSL Linux
distribution installed. No local container startup was performed. No container
environment was installed and no test was moved to the production server.

## Container checks in GitHub Actions

Since 1.21.0 these checks run natively on AMD64 and ARM64. Before builds, both base image platforms are checked and the Bitcoin binary for the current architecture is executed. This is not a physical Raspberry Pi test; see [ARM64](ARM64.md).

CI validates all three Compose files and builds the dashboard and all-in-one
images. It starts the all-in-one container with Bitcoin Core and checks health,
the English language file and admin access denial without authentication.
It then builds and starts the separate Bitcoin Core/dashboard stack with the
same HTTP checks. Both variants use temporary runner volumes; cleanup removes
only those disposable test volumes.

The host-node variant is validated as Compose configuration but is not started
against a real host bitcoind. Passing CI does not replace a local Docker Desktop
test, full blockchain synchronization or production use with real wallets or
long-term data.

Compose image tags and build metadata share the same version default.
`DASHBOARD_VERSION` can override it when deliberately building another version.

## Peer and traffic checks since 1.20.0

Python tests cover bounded peer aggregates without addresses or free-form client
comments, decreasing counters and uptime restarts, sampling gaps, UTC boundaries,
unknown values, the 20-block limit, and the new read-only HTTP endpoints.
Optional Playwright tests require Playwright and a Chromium browser
(`QA_BROWSER=msedge` for Edge). They cover all six languages, safe text rendering,
zero versus unknown rates, tabs, and mobile widths. Browser data is mocked;
no production node is changed.

```sh
python -m unittest discover -s tests -q
python tools/check_documentation.py
node tools/test_languages.cjs
node tools/test_node_insights.cjs
```

## Tokenless updates

See [Public repository without a token](UPDATES.md#public-repository-without-a-token).
A live test with the official public GitHub CLI repository anonymously downloaded
metadata and a checksum file using the existing downloader. After publication,
run the same read-only check with `--repo todo1971/bitcoin-node-dashboard`.

## Pre-publication checks

A read-only pattern scan of 499 historical Git file objects found no matches
before these testing changes for private keys, GitHub/AWS/Slack/Telegram tokens,
database password URLs, RPC auth hashes or typical sensitive filenames.
This is a limited check, not proof that every possible secret has been excluded.

The known server IP remains in examples and defaults. Git author information is
part of history. Since 1.18.4 the license is GPL-3.0-only and the repository is
intended for public use.
