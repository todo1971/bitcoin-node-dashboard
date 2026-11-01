# Lokale Installationstests mit QEMU

Deutsch | [English](en/QEMU_TESTS.md)

Am 1. November 2026 wurde Release **1.21.1** auf einem lokalen Windows-11-x64-Rechner
in vollstÃ¤ndiger ARM64-Systememulation getestet. Release 1.21.2 dokumentiert diese
PrÃ¼fung; die Dashboard-Laufzeitlogik bleibt unverÃ¤ndert. ZusÃ¤tzlich bestehen die
nativen AMD64-/ARM64-PrÃ¼fungen in GitHub Actions.

## Testumgebungen

| Eigenschaft | Generische ARM64-VM | Raspberry-Pi-Modell |
|---|---|---|
| QEMU | 11.1.0, Windows-x64-Build, portable entpackt | derselbe Build |
| Maschine / CPU | `virt`, Cortex-A72, 2 CPUs | `raspi3b`, Cortex-A53, 4 CPUs |
| Arbeitsspeicher / virtuelles Laufwerk | 2 GiB / 16 GiB QCOW2 | 1 GiB / 8 GiB QCOW2-SD-Karte |
| Betriebssystem | Debian 12 nocloud ARM64 | Raspberry Pi OS Lite ARM64, Debian 13 |
| Kernel | 6.1.0-54-arm64 | 6.18.50+rpt-rpi-v8 |
| Python | 3.11.2 | 3.13.5 |
| Bitcoin Core | 31.1, offizielle AArch64-BinÃ¤rdateien | dieselben BinÃ¤rdateien |
| Beschleunigung | TCG-Softwareemulation | TCG-Softwareemulation |

QEMU wurde Ã¼ber WinGet heruntergeladen, anhand der hinterlegten SHA-256-PrÃ¼fsumme
geprÃ¼ft und mit dem vorhandenen 7-Zip entpackt. Die groÃŸen Images, VM-Laufwerke
und lokalen Steuerskripte bleiben auÃŸerhalb des Git-Repositorys. Es wurde kein
Produktivserver fÃ¼r diese Tests verwendet.

## GeprÃ¼fte Installationswege

| PrÃ¼fung | Debian-ARM64-VM | Raspberry Pi OS / Pi-3B-Modell |
|---|---|---|
| Dokumentierte Host-Pakete installieren | bestanden | bestanden |
| Web-Installer mit authentifiziertem HTTP-Aufruf | bestanden | bestanden |
| Node- und Dashboard-Dienst unter `btc` | bestanden | bestanden |
| Bitcoin-RPC und HTTP-Healthcheck | bestanden | bestanden |
| Admin-Anmeldung, anonymer Zugriff abgewiesen, CSRF-Schutz | bestanden | bestanden |
| Konfiguration speichern und Dienstneustart auslÃ¶sen | bestanden | bestanden |
| SSE und ZMQ-Blockereignis | bestanden | bestanden |
| SQLite-Historie und erfasste BlÃ¶cke | bestanden | bestanden |
| 86 Regressionstests aus dem vollstÃ¤ndigen Release | bestanden | bestanden |
| VollstÃ¤ndiger VM-Neustart: Autostart und Historie | bestanden | bestanden |
| All-in-one Ã¼ber Shell-Installer, einschlieÃŸlich Portschutz | bestanden | nicht ausgefÃ¼hrt |
| Getrennter Bitcoin-/Dashboard-Compose-Stack | bestanden | nicht ausgefÃ¼hrt |
| Dashboard-Container fÃ¼r vorhandenen Host-Node | bestanden | nicht ausgefÃ¼hrt |
| Container ohne Root, privates RPC, Admin-Schutz | bestanden | nicht ausgefÃ¼hrt |
| All-in-one-Daten nach `down` und erneutem `up` erhalten | bestanden | nicht ausgefÃ¼hrt |

Die Docker-PrÃ¼fung verwendete Engine 29.9.2, Compose 5.6.1 und Buildx 0.38.1.
Images wurden lokal aus dem Release gebaut. Beim Host-Node-Container wurden die
UID/GID des Dienstbenutzers sowie dessen tatsÃ¤chlicher Cookie-Pfad und RPC-Port
verwendet. Die Cookie-Einbindung blieb lesend. Das Ã¤ltere Debian-12-Paket
`docker-compose` allein liefert nicht das vorausgesetzte `docker compose`-Plugin.

Alle Bitcoin-Instanzen liefen ausschlieÃŸlich im **Regtest** mit ausgeschalteten
P2P-Verbindungen. FÃ¼r den All-in-one-Healthcheck blieb der interne RPC-Port 8332
mit einem ausdrÃ¼cklich gesetzten Cookie-Pfad erhalten. Es wurden lokale
TestblÃ¶cke erzeugt; kein Ã¶ffentlicher Blockchain-Sync und keine echten Wallets
oder Guthaben waren Teil der PrÃ¼fung.

Die Regressionstests benÃ¶tigen das vollstÃ¤ndige entpackte Release oder einen
Checkout. Eine schlanke Host-Installation enthÃ¤lt nicht alle Docker-/Installer-
Dateien, die einige der QuellcodeprÃ¼fungen lesen. Das ist von den Laufzeit-
Healthchecks des installierten Dashboards zu unterscheiden.

## Anpassungen fÃ¼r das emulierte Pi-Board

Der Pi-Test ist ein Software-Installationstest auf einem QEMU-Boardmodell, keine
unverÃ¤nderte Nachbildung eines physischen GerÃ¤ts. FÃ¼r diesen Lauf waren nÃ¶tig:

- `kernel8.img` fÃ¼r den direkten Kernelstart dekomprimieren und den passenden Pi-3B-Device-Tree verwenden.
- Bluetooth-Zugriff auf den Konsolen-UART und den ungenutzten Mini-UART im Test-Device-Tree deaktivieren; serielle Konsole auf `ttyAMA1` und Early Console auf `0x3f201000` setzen.
- Direktstart ohne die automatische Initramfs-Watchdog-Einrichtung und Abschalten des systemd-Hardware-Watchdogs innerhalb des Testgasts; dessen Aktivierung setzte das emulierte Board zurÃ¼ck.
- Cloud-init und die fÃ¼r dieses Testnetz unpassenden Start-/Wartepfade deaktivieren; DHCP fÃ¼r das emulierte `usb0` Ã¼ber systemd-networkd einrichten.
- Die virtuelle SD-Partition und das Dateisystem auf 8 GiB erweitern.
- Die groÃŸen, bereits auf dem Host geprÃ¼ften Core-BinÃ¤rdateien Ã¼ber ein schreibgeschÃ¼tztes virtuelles USB-Laufwerk bereitstellen. Der emulierte USB-Netzwerktransfer war fÃ¼r groÃŸe Dateien sehr langsam.

Diese Ã„nderungen gehÃ¶ren ausschlieÃŸlich zur QEMU-Testumgebung. Sie sind keine
Installationsvoraussetzungen fÃ¼r reale Raspberry Pis. Die SHA-256-Werte der beiden
Ã¼bertragenen Core-Programme wurden im Gast erneut geprÃ¼ft.

Beide Test-VMs und der temporÃ¤re Dateiserver wurden anschlieÃŸend kontrolliert beendet. Die geprÃ¼ften VM-Laufwerke bleiben lokal fÃ¼r Wiederholungen erhalten.

## Quellen und IntegritÃ¤t

- [QEMU fÃ¼r Windows](https://www.qemu.org/download/#windows), WinGet-Paket `SoftwareFreedomConservancy.QEMU`, Version 11.1.0.
- [Debian-12-Cloud-Images](https://cloud.debian.org/images/cloud/bookworm/latest/), `debian-12-nocloud-arm64.qcow2`, Download vom 1.11.2026, SHA-512 gegen die Anbieterdatei geprÃ¼ft.
- [Raspberry Pi OS Lite ARM64 vom 6.10.2026](https://downloads.raspberrypi.com/raspios_lite_arm64/images/raspios_lite_arm64-2026-10-06/), SHA-256 gegen die Anbieterdatei geprÃ¼ft.
- [Bitcoin Core 31.1](https://bitcoincore.org/bin/bitcoin-core-31.1/), AArch64-Archiv, SHA-256 gegen `SHA256SUMS` geprÃ¼ft.

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

Die JSON-Nachweise stehen beim [Release 1.21.2](https://github.com/todo1971/bitcoin-node-dashboard/releases/tag/v1.21.2).
VM-Images, Cookies, Admin-Zugangsdaten und SSH-SchlÃ¼ssel werden nicht als
Testartefakte verÃ¶ffentlicht. Shell-Skripte behalten beim Transfer von Windows
LF-Zeilenenden; die Release-Archive enthalten die Git-Dateien mit diesen Zeilenenden.

## Grenzen und Beobachtungen

TCG-Zeiten sind keine Leistungswerte realer ARM-GerÃ¤te. Bei gleichzeitigem
Paketinstallieren trat einmal der zehnsekÃ¼ndige Timeout des Admin-Neustarthelfers
auf; die abschlieÃŸenden FunktionsprÃ¼fungen erfolgten ohne diese Zusatzlast.
Mehrere zunÃ¤chst weiterlaufende alte Emulatorprozesse wurden beendet.
AbschlieÃŸende PrÃ¼fungen verwendeten ein frisches Pi-Overlay. Die Start-/Stopp-
Steuerung prÃ¼ft jetzt laufende PIDs und bestÃ¤tigt das tatsÃ¤chliche
Prozessende, bevor ein Laufwerk erneut gestartet wird.

Nicht geprÃ¼ft sind physische SD-Karten, Temperatur, Stromausfallverhalten, GPIO,
Kamera/Bluetooth, Pi 4/5, vollstÃ¤ndiger Mainnet-Sync und reale Plesk-/TLS-Domains.
QEMUs [Pi-Modelle](https://www.qemu.org/docs/master/system/arm/raspi.html) bilden
Peripherie nur teilweise nach; fÃ¼r allgemeine ARM-Linux-Tests empfiehlt QEMU die
[virt-Plattform](https://www.qemu.org/docs/master/system/target-arm.html).

[Paketvoraussetzungen](DEPENDENCIES.md) Â· [ARM64-Builds](ARM64.md) Â· [ZurÃ¼ck zur Ãœbersicht](../README.md)

Aufgezeichnete Ergebnisse im Repository: [Debian-Host](test-results/qemu-2026-11-01/qemu-debian12-arm64.json), [Docker-Varianten](test-results/qemu-2026-11-01/qemu-docker-arm64.json), [Raspberry Pi OS](test-results/qemu-2026-11-01/qemu-raspios-arm64.json).
