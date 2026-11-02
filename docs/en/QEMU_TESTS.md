# Local installation tests with QEMU

[Deutsch](../QEMU_TESTS.md) | English

On November 1, 2026, release **1.21.1** was tested on a local Windows 11 x64
machine using full ARM64 system emulation. Release 1.21.2 documents these checks;
dashboard runtime logic is unchanged. Native AMD64/ARM64 checks in GitHub Actions
also pass.

## Test environments

| Property | Generic ARM64 VM | Raspberry Pi model |
|---|---|---|
| QEMU | 11.1.0, Windows x64 build, extracted for portable use | same build |
| Machine / CPU | `virt`, Cortex-A72, 2 CPUs | `raspi3b`, Cortex-A53, 4 CPUs |
| Memory / virtual disk | 2 GiB / 16 GiB QCOW2 | 1 GiB / 8 GiB QCOW2 SD card |
| Operating system | Debian 12 nocloud ARM64 | Raspberry Pi OS Lite ARM64, Debian 13 |
| Kernel | 6.1.0-54-arm64 | 6.18.50+rpt-rpi-v8 |
| Python | 3.11.2 | 3.13.5 |
| Bitcoin Core | 31.1, official AArch64 binaries | same binaries |
| Acceleration | TCG software emulation | TCG software emulation |

QEMU was downloaded through WinGet, checked against its recorded SHA-256, and
extracted with the existing 7-Zip installation. Large images, VM disks, and local
control scripts remain outside the Git repository. No production server was
used for these tests.

## Tested installation paths

| Check | Debian ARM64 VM | Raspberry Pi OS / Pi 3B model |
|---|---|---|
| Install documented host packages | passed | passed |
| Web installer through authenticated HTTP | passed | passed |
| Node and dashboard services running as `btc` | passed | passed |
| Bitcoin RPC and HTTP health check | passed | passed |
| Admin login, anonymous access denied, CSRF protection | passed | passed |
| Save configuration and trigger service restart | passed | passed |
| SSE and ZMQ block event | passed | passed |
| SQLite history and recorded blocks | passed | passed |
| 86 regression tests from the complete release | passed | passed |
| Full VM restart: automatic startup and history | passed | passed |
| All-in-one shell installer, including occupied-port guard | passed | not run |
| Separate Bitcoin/dashboard Compose stack | passed | not run |
| Dashboard container for an existing host node | passed | not run |
| Non-root containers, private RPC, admin protection | passed | not run |
| All-in-one data retained across `down` and subsequent `up` | passed | not run |

Docker checks used Engine 29.9.2, Compose 5.6.1, and Buildx 0.38.1. Images were
built locally from the release. The host-node container used the service
account's UID/GID, actual cookie path, and RPC port. Cookie mounts remained
read-only. Debian 12's older `docker-compose` package alone does not provide the
required `docker compose` plugin.

Every Bitcoin instance ran exclusively in **regtest**, with P2P connections
disabled. All-in-one retained internal RPC port 8332 and an explicitly configured
cookie path for its health check. Local test blocks were generated; public
blockchain synchronization, real wallets, and funds were outside the test scope.

Regression tests need a complete extracted release or checkout. A slim host
installation does not contain every Docker/installer file read by source checks.
These tests are distinct from runtime health checks of the installed dashboard.

## Adaptations for the emulated Pi board

The Pi test checks software installation on a QEMU board model, rather than an
unchanged physical device. This run required:

- Decompressing `kernel8.img` for direct kernel boot and using the matching Pi 3B device tree.
- Disabling Bluetooth ownership of the console UART and the unused mini-UART in the test device tree; using `ttyAMA1` and early console address `0x3f201000`.
- Direct boot without automatic initramfs watchdog setup, and disabling systemd's hardware watchdog inside the test guest because enabling it reset the emulated board.
- Disabling cloud-init and startup/wait paths unsuitable for this test network; configuring DHCP for emulated `usb0` through systemd-networkd.
- Expanding the virtual SD partition and filesystem to 8 GiB.
- Providing large, host-verified Core binaries through a read-only virtual USB disk. Emulated USB networking was very slow for large transfers.

These changes belong exclusively to the QEMU test environment. They are not
installation requirements for physical Raspberry Pis. SHA-256 digests of both
transferred Core executables were checked again inside the guest.

Both test VMs and the temporary file server were subsequently shut down with process exit verified. Tested VM disks remain local for repeat runs.

## Sources and integrity

- [QEMU for Windows](https://www.qemu.org/download/#windows), WinGet package `SoftwareFreedomConservancy.QEMU`, version 11.1.0.
- [Debian 12 cloud images](https://cloud.debian.org/images/cloud/bookworm/latest/), `debian-12-nocloud-arm64.qcow2`, downloaded November 1, 2026; SHA-512 checked against the provider file.
- [Raspberry Pi OS Lite ARM64 dated October 6, 2026](https://downloads.raspberrypi.com/raspios_lite_arm64/images/raspios_lite_arm64-2026-10-06/); SHA-256 checked against the provider file.
- [Bitcoin Core 31.1](https://bitcoincore.org/bin/bitcoin-core-31.1/), AArch64 archive; SHA-256 checked against `SHA256SUMS`.

```text
QEMU installer SHA256:
f98a8aeb5f7faea9765b6dee28316c266cd179d80354a2fed8e50176f9a2e59f
Debian image SHA512:
f5889d18bbd59228c6cafce7ab98dfc01129aa62b4ca9be044ff5a2149c3880ad3d44eaf62f80f0f85d3ab026082aa929f5b71731b8098e3acd09edcf8615c38
Raspberry Pi OS compressed image SHA256:
483db18a48da399b5b7022ffae9a07bc6d99daab30e593aedac09b69ff422843
Bitcoin Core ARM64 archive SHA256:
dcf1873f2208ba4f962f3398d47e154c39c0084be8f4553e05c940d0ace3d004
```

JSON evidence is attached to [release 1.21.2](https://github.com/todo1971/bitcoin-node-dashboard/releases/tag/v1.21.2).
VM images, cookies, admin credentials, and SSH keys are not published as test
artifacts. Shell scripts retain LF line endings when transferred from Windows;
release archives contain the Git files with these line endings.

## Limitations and observations

TCG timings are not performance measurements of physical ARM devices. During
concurrent package installation, the admin restart helper once hit its ten-second
timeout; final functional checks ran without that additional load. Old emulator
processes that initially remained running were stopped. Final checks used a fresh
Pi overlay. VM control now checks
running PIDs and confirms process exit before starting a disk again.

Physical SD cards, temperature, power-loss behavior, GPIO, camera/Bluetooth,
Pi 4/5, full mainnet synchronization, and real Plesk/TLS domains were not tested.
QEMU's [Pi models](https://www.qemu.org/docs/master/system/arm/raspi.html) implement
only part of the peripherals; QEMU recommends the
[virt platform](https://www.qemu.org/docs/master/system/target-arm.html) for general
ARM Linux testing.

[Package requirements](DEPENDENCIES.md) · [ARM64 builds](ARM64.md) · [Back to overview](../../README.en.md)

Recorded repository results: [Debian host](../test-results/qemu-2026-11-01/qemu-debian12-arm64.json), [Docker variants](../test-results/qemu-2026-11-01/qemu-docker-arm64.json), [Raspberry Pi OS](../test-results/qemu-2026-11-01/qemu-raspios-arm64.json).
