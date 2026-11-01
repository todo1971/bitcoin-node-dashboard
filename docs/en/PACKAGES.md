# GitHub Packages

[Deutsch](../PACKAGES.md) | [English documentation](../../README.en.md#documentation)

For every published stable release, `Publish GitHub Packages` automatically
builds two multi-platform images for Linux/AMD64 and Linux/ARM64 from the exact release tag and publishes them to
the GitHub Container Registry:

- `ghcr.io/todo1971/bitcoin-node-dashboard:VERSION`
- `ghcr.io/todo1971/bitcoin-node-dashboard-all-in-one:VERSION`

Only fixed version tags are published, without a moving `latest` tag.
The dashboard image needs an existing node. The all-in-one image contains both
Bitcoin Core and the dashboard; its Core version remains independently pinned
in the Dockerfile.

Use **Actions → Publish GitHub Packages → Run workflow** to backfill missing
images for an already published stable tag. The workflow checks release status,
source version equality, compilation and unit tests. It uses GitHub's short-lived
`GITHUB_TOKEN` with `packages: write`; no custom registry token secret is needed.

Example:

```bash
docker pull ghcr.io/todo1971/bitcoin-node-dashboard:1.21.0
docker pull ghcr.io/todo1971/bitcoin-node-dashboard-all-in-one:1.21.0
```

Images do not replace configuration, volumes or port bindings described in
the [Docker guide](DOCKER.md). Included Compose files still build from local
source. To use published images in your own stack, set the matching `image:`
and remove `build:`. Keep RPC port 8332 internal and bind the host dashboard
port locally.

Packages are linked to the repository. This workflow does not change visibility.
Private packages require registry authentication with read permissions.
Public packages can be pulled without a token. Before public distribution,
check the visibility of both packages separately in their package settings.

Successful uploads and manifest digests appear in the Actions run.
The release `tar.gz` and `tar.gz.sha256` assets remain available for the systemd
dashboard updater, which does not download container images.

ARM64 requirements and build tools: [Raspberry Pi / ARM64](ARM64.md).
