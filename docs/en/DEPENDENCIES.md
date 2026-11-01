# Required packages by deployment and architecture

[Deutsch](../DEPENDENCIES.md) | English

As of November 1, 2026: AMD64 and ARM64. Package commands target Debian 12
(Bookworm). Other distributions may use different package names and Python
versions. These commands are instructions; they do not automatically run on an
existing server.

## Overview

| Deployment / feature | Required | Additional requirements on ARM64 |
|---|---|---|
| Dashboard without containers | Python 3.11+ with SQLite/SSL modules, CA certificates, read-only RPC access | same packages from the ARM64 repository |
| Local RPC queries | CPU-matching `bitcoin-cli` binary | `aarch64-linux-gnu` instead of `x86_64-linux-gnu` |
| Direct JSON-RPC | `BITCOIN_RPC_URL` and protected node access | no additional packages |
| SQLite history | Python `sqlite3` module | no additional packages |
| Optional ZMQ | `python3-zmq` for Debian system Python; `pyzmq` for custom Python | native ARM64 bindings/wheels |
| Browser SSE | standard library and suitable reverse proxy | no additional packages |
| Optional email alerts | configured sendmail-compatible delivery program | same requirement |
| HTTPS webhooks | Python SSL and CA certificates | no additional packages |
| Docker deployment | Docker Engine, CLI, and Compose plugin on the host | 64-bit Linux and ARM64 images |
| Local container builds | Buildx as well | QEMU only when building for a different architecture |

Basic operation requires neither `requests`, Flask, Node.js/npm, MariaDB, Redis,
nor Grafana. The `sqlite3` command-line program is optional; database access uses
Python's standard library.

## Host installation with systemd and web updates

On a Debian host already running systemd:

```sh
sudo apt-get update
sudo apt-get install --no-install-recommends python3 ca-certificates systemd sudo util-linux coreutils findutils grep sed mawk tar gzip passwd curl gnupg
```

| Package | Purpose |
|---|---|
| `python3` | dashboard, web installer, release downloader, including SQLite/SSL standard modules |
| `ca-certificates` | certificate validation for GitHub, version checks, and webhooks |
| `systemd` | service, journal, and fixed update jobs (`systemctl`, `journalctl`, `systemd-run`) |
| `sudo` | restricted admin jobs and bootstrap `visudo` validation |
| `util-linux` | `flock` and `runuser` for update locks and user switching |
| `coreutils`, `findutils`, `grep`, `sed`, `mawk` | file, permission, checksum, and text operations in installers/updaters |
| `tar`, `gzip` | release/Core archives and backups |
| `passwd` | user/group utilities when preparing the service account |
| `curl` | update health checks and downloading official Core checksums/signatures |
| `gnupg` | signature checking with `gpg`; the documented trusted keyring must also be configured |

Installing `systemd` does not turn an arbitrary container into a supported
systemd host. Prepare the service account, RPC cookie access, and running Bitcoin
node separately. An existing compatible `awk` can replace `mawk`.

Additional tools as needed:

```sh
sudo apt-get install --no-install-recommends git iproute2 sqlite3
sudo apt-get install --no-install-recommends python3-zmq
/usr/bin/python3 -c 'import sqlite3, ssl; print(sqlite3.sqlite_version, ssl.OPENSSL_VERSION)'
/usr/bin/python3 -c 'import zmq; print(zmq.__version__, zmq.zmq_version())'
```

`git` is only needed for cloning, `iproute2` provides `ss` for port diagnostics,
and `sqlite3` is an optional database utility. The second line installs optional
ZMQ support; normal polling works without it. The final check requires ZMQ.
Custom Python interpreters and virtual environments need bindings installed into
that specific environment, rather than blindly installing APT packages for a
different interpreter.

For email, first check whether the existing mail server provides `sendmail`.
Do not blindly install a second MTA on a Plesk/mail server. Postfix or an
appropriately configured sendmail-compatible relay program can provide delivery.
Webhooks do not need a local mail program.

A public HTTPS domain can use an existing reverse proxy. A standalone Debian
Apache installation needs `apache2` and the `proxy`, `proxy_http`, and, for TLS,
`ssl` modules. Plesk manages its own web servers; do not install a second one
there. `tor` is optional for a configured Bitcoin onion service, not for displaying
Tor peers in the dashboard.

## Container host and builds

After configuring the appropriate official Docker APT repository:

```sh
sudo apt-get install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
docker version
docker compose version
docker buildx version
```

Repository setup is described in the [official Debian guide](https://docs.docker.com/engine/install/debian/).
Do not blindly mix a distribution-provided Docker installation with Docker CE.
Running prebuilt images does not require a compiler. The shell installer also
expects the usual POSIX/Coreutils programs. Starting the matching container does
not require host Python, SQLite, or `bitcoin-cli`. Exception: the included shell
installer uses host `python3` to generate a token when `ADMIN_TOKEN` is omitted.
Install `python3` for this or supply a suitable token securely.

Only a local cross-build may need additional Debian emulation packages:

```sh
sudo apt-get install qemu-user-static binfmt-support
docker buildx inspect --bootstrap
```

The builder must actually list the desired target platform. A native ARM64 host
does not need QEMU to build ARM64. GitHub release builds set up QEMU and Buildx
automatically; native startup tests run on both architectures.

## What the finished images contain

Native CI checks both images on AMD64 and ARM64. The runtime audit tests SQLite
and the CA trust store, identifies dynamic dependencies of Python, SQLite, SSL,
and, for all-in-one, `bitcoind` and `bitcoin-cli`, and fails on missing libraries.
Complete package inventories are JSON CI artifacts named `dependency-audit-amd64`
and `dependency-audit-arm64`, retained for 30 days. Four reports are also attached
to release 1.21.1.

| Component | AMD64 and ARM64, checked November 1, 2026 |
|---|---|
| Python | 3.11.18, from the Python base image under `/usr/local` |
| SQLite library / OpenSSL | 3.40.1 / 3.0.22; linked and functional |
| Trusted CA certificates | present; 148 in the inspected SSL context |
| Base image library packages | `libc6`, `libgcc-s1`, `libstdc++6`, `libsqlite3-0`, `libssl3` |
| Shell/user utilities | `bash`, `coreutils`, `passwd` present |
| All-in-one Core 31.1 | `bitcoind` and `bitcoin-cli`; `ldd` needs glibc, libm, libpthread, and the architecture-specific loader, all present |
| Not included by default | `pyzmq`, `sendmail`, `curl`, `gpg`, SQLite command line |

These are measurements of current builds, not permanent version requirements.
Package names are the same on both architectures; library paths and ELF loaders
differ. No extra ARM64 runtime packages are required outside the images.
Containers use direct JSON-RPC and Python health checks, so neither `curl` nor
`gpg` is needed for those tasks. Container updates use Docker, not the host web
updater.

## Optional container ZMQ bindings

Standard images do not contain ZMQ bindings. Debian's `python3-zmq` alone does
not automatically serve the base image's `/usr/local` Python. A custom derived
variant can install a matching PyPI wheel:

```dockerfile
FROM ghcr.io/todo1971/bitcoin-node-dashboard:1.21.1
USER root
RUN python3 -m pip install --no-cache-dir --only-binary=:all: pyzmq==27.2.0
USER dashboard:dashboard
```

For all-in-one, use its image instead and finish with `USER node:node`.
CI checks wheel download, import, and ZMQ context creation with this version
natively on AMD64 and ARM64. `--only-binary` prevents an unexpected source build.
This path needs neither a compiler nor `libzmq3-dev`. Bitcoin's ZMQ publisher,
the dashboard endpoint, and private network access still need configuration;
never expose ZMQ publicly. See [Real time](REALTIME.md).

## Additional architectures

Currently published: `linux/amd64` and `linux/arm64`. ARMv7/ARMHF, ARMEL, RISC-V,
and other targets are not approved dashboard image architectures. Before adding
one, check base image manifests, matching Core binaries, runtime libraries,
Python/SQLite/SSL, optional ZMQ wheels, and native startup tests. Only then extend
package lists, reports, and the architecture table. An ARM64 runner does not
replace testing on a physical Raspberry Pi.

[Back to overview](../../README.en.md)

## Additional local check: Raspberry Pi OS / Debian 13

The QEMU Raspberry Pi OS Lite ARM64 run used the same host package names. Python 3.13.5, Debian `python3-zmq` 26.4.0, and libzmq 4.3.5 worked without a compiler or additional manually installed ARM64 libraries. Docker was checked separately in the Debian 12 ARM64 guest. See [scope and emulation adaptations](QEMU_TESTS.md).
