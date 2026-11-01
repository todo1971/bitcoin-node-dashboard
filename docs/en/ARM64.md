# ARM64 and Raspberry Pi

[Deutsch](../ARM64.md) | English

Since 1.21.0, both the dashboard and all-in-one images are built for `linux/amd64`
and `linux/arm64`. One version tag contains both architectures; Docker selects
the matching variant when pulling. Raspberry Pi requires an ARM64-capable device
running 64-bit Linux and Docker. These packages do not support a 32-bit system
(`armv7l`).

The ordinary dashboard archive contains Python source and is already architecture
independent. No second ARM64 tar.gz is needed. The additional binary packages are
the two versioned container images; see [GitHub Packages](PACKAGES.md).
Existing Compose files can build locally on both architectures without forcing
an AMD64 platform.

## Check base images first

`Dockerfile.all-in-one` copies Core from `bitcoin/bitcoin:31.1` and uses
`python:3.11-slim-bookworm`. Both registry indexes offered AMD64 and ARM64 when
checked on November 1, 2026. This checks the specific tags; it does not guarantee
future tags or immutable image contents.

```sh
python tools/check_container_platforms.py --output container-platforms.json
```

The tool only needs the Python standard library, downloads registry metadata,
and checks both required platforms. It reads versions from the Dockerfiles and
does not print registry access tokens. Optional `--output` records image and
platform digests as evidence. It does not download image layers.

## Tools and downloads

Builds run in GitHub Actions. Release jobs download QEMU for ARM64 through the
pinned `setup-qemu-action` and configure Docker Buildx/BuildKit. QEMU is set up
before the builder. BuildKit automatically downloads matching Bitcoin and Python
layers. No cross-compiler or custom
Bitcoin source build is required. Hardy's Windows machine does not need Docker
Desktop for these builds.

For a local multi-platform build, Docker Engine/Desktop, Buildx, and ARM64
emulation or a native ARM64 builder are required:

```sh
docker buildx build --platform linux/amd64,linux/arm64 -f Dockerfile --output type=oci,dest=dashboard-multiarch.tar .
docker buildx build --platform linux/amd64,linux/arm64 -f Dockerfile.all-in-one --output type=oci,dest=node-multiarch.tar .
```

These commands assume an appropriately configured builder. The OCI archives are
build outputs, not packages for the systemd web updater.

## Checks and limitations

CI runs natively on `ubuntu-24.04` and `ubuntu-24.04-arm`. It checks the downloaded
Bitcoin base image architecture and executes its `bitcoind --version`. It then
builds and starts all-in-one and separate stacks, including RPC/HTTP health
checks and admin access protection. After upload, the package workflow verifies
AMD64 and ARM64 in the combined manifest.

An ARM64 runner is not a physical Raspberry Pi: SD cards, thermal limits, memory
needs, full blockchain synchronization, and long-term device operation are not
tested. Existing package visibility is unchanged; private GHCR images still
require authentication.

Background: [Docker multi-platform builds](https://docs.docker.com/build/building/multi-platform/)
and [GitHub ARM64 runners](https://github.blog/changelog/2025-08-07-arm64-hosted-runners-for-public-repositories-are-now-generally-available/).

[Back to overview](../../README.en.md)

Verified package lists for AMD64 and ARM64: [Dependencies](DEPENDENCIES.md).

Local Debian ARM64 and Raspberry Pi 3B board-model tests are documented in the [QEMU report](QEMU_TESTS.md). These use emulation rather than physical hardware.
