# Test coverage and public updates

[Deutsch](../TESTING.md) | [English documentation](../../README.en.md#documentation)

## Local environment on October 31, 2026

The inspected Windows machine has no Docker Desktop, Docker CLI or WSL Linux
distribution installed. No local container startup was performed. No container
environment was installed and no test was moved to the production server.

## Container checks in GitHub Actions

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

## Tokenless updates

See [Public repository without a token](UPDATES.md#public-repository-without-a-token).
A live test with the official public GitHub CLI repository anonymously downloaded
metadata and a checksum file using the existing downloader. While this dashboard
repository remains private, its own anonymous end-to-end test is not possible.

## Pre-publication checks

A read-only pattern scan of 499 historical Git file objects found no matches
before these testing changes for private keys, GitHub/AWS/Slack/Telegram tokens,
database password URLs, RPC auth hashes or typical sensitive filenames.
This is a limited check, not proof that every possible secret has been excluded.

The known server IP remains in examples and defaults. Git author information is
part of history. The README has not yet selected a license.
Repository visibility was not changed.
