# Benötigte Pakete nach Betriebsart und Architektur

Deutsch | [English](en/DEPENDENCIES.md)

Stand: 1. November 2026, AMD64 und ARM64. Paketbefehle beziehen sich auf Debian 12
(Bookworm). Andere Distributionen können andere Paketnamen und Python-Versionen
haben. Die folgenden Befehle sind Anleitungen; sie werden nicht automatisch auf
einem vorhandenen Server ausgeführt.

## Übersicht

| Betriebsart / Funktion | Benötigt | Zusätzlich auf ARM64 |
|---|---|---|
| Dashboard ohne Container | Python 3.11+ mit SQLite-/SSL-Modulen, CA-Zertifikate, lesender RPC-Zugang | dieselben Pakete aus dem ARM64-Repository |
| Lokale RPC-Abfrage | zur CPU passende `bitcoin-cli`-Binärdatei | `aarch64-linux-gnu` statt `x86_64-linux-gnu` |
| Direkter JSON-RPC-Zugang | `BITCOIN_RPC_URL` und geschützter Zugang zum Node | keine zusätzlichen Pakete |
| SQLite-Historie | Python-Modul `sqlite3` | keine zusätzlichen Pakete |
| ZMQ, optional | `python3-zmq` für Debian-Systempython; `pyzmq` für eigenes Python | native ARM64-Bindings/Wheels |
| SSE im Browser | Standardbibliothek und geeigneter Reverse Proxy | keine zusätzlichen Pakete |
| E-Mail-Alarme, optional | eingerichtetes, sendmail-kompatibles Versandprogramm | dieselbe Voraussetzung |
| HTTPS-Webhooks | Python-SSL und CA-Zertifikate | keine zusätzlichen Pakete |
| Docker-Betrieb | Docker Engine, CLI und Compose-Plugin auf dem Host | 64-Bit-Linux, ARM64-Images |
| Lokaler Container-Build | zusätzlich Buildx | QEMU nur bei architekturfremdem Build |

Für den Grundbetrieb werden weder `requests`, Flask, Node.js/npm noch MariaDB,
Redis oder Grafana benötigt. `sqlite3` als Kommandozeilenprogramm ist optional;
die Datenbank wird über Pythons Standardbibliothek angesprochen.

## Host-Installation mit systemd und Web-Updater

Auf einem bereits mit systemd laufenden Debian-Host:

```sh
sudo apt-get update
sudo apt-get install --no-install-recommends python3 ca-certificates systemd sudo util-linux coreutils findutils grep sed mawk tar gzip passwd curl gnupg
```

| Paket | Verwendung |
|---|---|
| `python3` | Dashboard, Web-Installer, Release-Downloader; einschließlich SQLite-/SSL-Standardmodule |
| `ca-certificates` | Zertifikatsprüfung bei GitHub-, Versions- und Webhook-Anfragen |
| `systemd` | Dienst, Journal und feste Update-Aufträge (`systemctl`, `journalctl`, `systemd-run`) |
| `sudo` | eng begrenzte Admin-Aufträge und `visudo` beim Bootstrap |
| `util-linux` | `flock` und `runuser` für gesperrte Updates und Benutzerwechsel |
| `coreutils`, `findutils`, `grep`, `sed`, `mawk` | Datei-, Rechte-, Prüfsummen- und Textoperationen der Installer/Updater |
| `tar`, `gzip` | Release-Archive, Core-Archive und Backups |
| `passwd` | Benutzer-/Gruppenwerkzeuge bei der Vorbereitung des Dienstbenutzers |
| `curl` | Update-Healthchecks und Download offizieller Core-Prüfsummen/Signaturen |
| `gnupg` | `gpg` für die Signaturprüfung; zusätzlich muss der dokumentierte vertrauenswürdige Keyring eingerichtet sein |

`systemd` zu installieren macht einen beliebigen Container nicht zu einem
unterstützten systemd-Host. Der Dienstbenutzer, sein RPC-Cookie-Zugriff und der
laufende Bitcoin Node müssen separat vorbereitet sein. Alternativ zu `mawk`
kann ein vorhandenes kompatibles `awk` verwendet werden.

Zusätzliche Werkzeuge nach Bedarf:

```sh
sudo apt-get install --no-install-recommends git iproute2 sqlite3
sudo apt-get install --no-install-recommends python3-zmq
/usr/bin/python3 -c 'import sqlite3, ssl; print(sqlite3.sqlite_version, ssl.OPENSSL_VERSION)'
/usr/bin/python3 -c 'import zmq; print(zmq.__version__, zmq.zmq_version())'
```

`git` wird nur zum Klonen benötigt, `iproute2` liefert `ss` für Portdiagnosen,
`sqlite3` ist ein optionales Datenbankwerkzeug. Die zweite Zeile installiert die
optionale ZMQ-Unterstützung; ohne sie genügt das normale Polling. Die letzte
Prüfung setzt ZMQ voraus. Für einen eigenen Python-Interpreter oder eine venv
müssen Bindings in genau dieser Umgebung installiert werden, nicht blind per
APT in einen anderen Interpreter.

Für E-Mail zuerst prüfen, ob der vorhandene Mailserver bereits `sendmail`
bereitstellt. Auf einem Plesk-/Mailserver keinen zweiten MTA ungeprüft installieren.
Postfix oder ein passend eingerichtetes sendmail-kompatibles Relay-Programm kann
den Versand bereitstellen. Webhooks benötigen kein lokales Mailprogramm.

Für eine öffentliche HTTPS-Domain kann ein vorhandener Reverse Proxy verwendet
werden. Bei einer eigenen Debian-Apache-Installation sind `apache2` sowie die
Module `proxy`, `proxy_http` und für TLS `ssl` nötig. Plesk verwaltet seine
Webserver selbst; dort keinen zweiten Webserver installieren. `tor` ist nur
optional für einen entsprechend konfigurierten Bitcoin-Onion-Dienst nötig,
nicht zum Anzeigen von Tor-Peers im Dashboard.

## Container-Host und Build

Nach Einrichtung des passenden offiziellen Docker-APT-Repositorys:

```sh
sudo apt-get install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
docker version
docker compose version
docker buildx version
```

Die Repository-Einrichtung steht in der [offiziellen Debian-Anleitung](https://docs.docker.com/engine/install/debian/).
Eine vorhandene distributionsseitige Docker-Installation nicht ungeprüft mit
Docker CE mischen. Für das Starten fertiger Images wird kein Compiler benötigt.
Der Shell-Installer erwartet außerdem die üblichen POSIX-/Coreutils-Werkzeuge.
Zum Starten des passenden Containers benötigt der Host kein Python, SQLite oder
`bitcoin-cli`. Ausnahme: Der mitgelieferte Shell-Installer verwendet Host-`python3`
zur Token-Erzeugung, wenn kein `ADMIN_TOKEN` vorgegeben wurde. Dafür zusätzlich
`python3` installieren oder ein geeignetes Token sicher vorgeben.

Nur für einen lokalen Cross-Build kann auf Debian zusätzlich Emulation nötig sein:

```sh
sudo apt-get install qemu-user-static binfmt-support
docker buildx inspect --bootstrap
```

Der Builder muss die gewünschte Zielplattform tatsächlich auflisten. Auf einem
nativen ARM64-Host ist für ARM64 kein QEMU nötig. GitHub-Release-Builds richten
QEMU und Buildx selbst ein; die nativen Starttests laufen auf beiden Architekturen.

## Was in den fertigen Images enthalten ist

Die native CI prüft beide Images auf AMD64 und ARM64. Der Laufzeit-Audit testet
SQLite und den CA-Zertifikatsspeicher, ermittelt die dynamischen Bibliotheken von
Python, SQLite, SSL sowie beim All-in-one von `bitcoind` und `bitcoin-cli` und
bricht bei nicht gefundenen Bibliotheken ab. Die vollständigen Paketlisten stehen
als JSON in den CI-Artefakten `dependency-audit-amd64` und `dependency-audit-arm64`.
Sie werden 30 Tage aufbewahrt; vier Berichte liegen zusätzlich beim Release 1.21.1.

| Bestandteil | AMD64 und ARM64, geprüft am 1.11.2026 |
|---|---|
| Python | 3.11.18, aus dem Python-Basisimage unter `/usr/local` |
| SQLite-Bibliothek / OpenSSL | 3.40.1 / 3.0.22; eingebunden und funktionsfähig |
| Vertrauenswürdige CA-Zertifikate | vorhanden; 148 im geprüften SSL-Kontext |
| Bibliothekspakete im Basisimage | `libc6`, `libgcc-s1`, `libstdc++6`, `libsqlite3-0`, `libssl3` |
| Shell-/Benutzerwerkzeuge | `bash`, `coreutils`, `passwd` vorhanden |
| All-in-one-Core 31.1 | `bitcoind` und `bitcoin-cli`; `ldd` benötigt glibc, libm, libpthread und den passenden dynamischen Loader, alles vorhanden |
| Nicht standardmäßig enthalten | `pyzmq`, `sendmail`, `curl`, `gpg`, SQLite-Kommandozeile |

Das sind gemessene Werte der aktuellen Builds, keine dauerhaft festgelegten
Versionsvorgaben. Die Paketnamen bleiben auf beiden Architekturen gleich;
Bibliothekspfade und ELF-Loader unterscheiden sich. Es sind keine zusätzlichen
ARM64-Laufzeitpakete außerhalb der Images nötig. Die Container verwenden direkte
JSON-RPC-Aufrufe und Python für Healthchecks; `curl` und `gpg` sind dafür nicht
nötig. Container-Updates laufen über Docker, nicht über den Host-Web-Updater.

## Optionale ZMQ-Bindings im Container

Die Standardimages enthalten keine ZMQ-Bindings. Debian-`python3-zmq` allein
versorgt nicht automatisch das `/usr/local`-Python des Basisimages. Für eine
eigene abgeleitete Variante kann ein passendes PyPI-Wheel installiert werden:

```dockerfile
FROM ghcr.io/todo1971/bitcoin-node-dashboard:1.21.1
USER root
RUN python3 -m pip install --no-cache-dir --only-binary=:all: pyzmq==27.2.0
USER dashboard:dashboard
```

Für All-in-one stattdessen dessen Image verwenden und am Ende `USER node:node`
setzen. Die CI prüft Download, Import und Erzeugung eines ZMQ-Kontexts mit dieser
Wheel-Version nativ auf AMD64 und ARM64. `--only-binary` verhindert einen
unbemerkten Quellcode-Build. Für diesen Weg sind weder Compiler noch
`libzmq3-dev` nötig. Bitcoin-ZMQ-Publisher, Dashboard-Endpunkt und privater
Netzwerkzugriff müssen trotzdem eingerichtet werden; ZMQ niemals öffentlich
freigeben. Details: [Echtzeit](REALTIME.md).

## Weitere Architekturen

Aktuell veröffentlicht: `linux/amd64` und `linux/arm64`. ARMv7/ARMHF, ARMEL,
RISC-V und weitere Ziele sind nicht als Dashboard-Images freigegeben. Vor einer
Erweiterung werden Basisimage-Manifeste, passende Core-Binärdateien, Bibliotheken,
Python/SQLite/SSL, optionale ZMQ-Wheels und native Starttests geprüft. Erst danach
werden die Paketliste, Berichte und Architekturtabelle erweitert. Ein ARM64-Runner
ersetzt keinen Test auf einem physischen Raspberry Pi.

[Zurück zur Übersicht](../README.md)

## Zusätzlich lokal geprüft: Raspberry Pi OS / Debian 13

Der QEMU-Lauf mit Raspberry Pi OS Lite ARM64 verwendete dieselben Host-Paketnamen. Python 3.13.5, Debian-`python3-zmq` 26.4.0 und libzmq 4.3.5 funktionierten ohne Compiler oder zusätzliche manuelle ARM64-Bibliotheken. Docker wurde separat im Debian-12-ARM64-Gast geprüft. [Umfang und Emulationsanpassungen](QEMU_TESTS.md).
