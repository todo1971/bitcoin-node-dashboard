# ARM64 und Raspberry Pi

Deutsch | [English](en/ARM64.md)

Ab 1.21.0 werden das Dashboard und das All-in-one-Image für `linux/amd64` und
`linux/arm64` gebaut. Ein gemeinsames Versionstag enthält beide Architekturen;
Docker wählt beim Pull die passende Variante. Auf einem Raspberry Pi ist ein
ARM64-fähiges Gerät mit 64-Bit-Linux und Docker erforderlich. Ein 32-Bit-System
(`armv7l`) wird mit diesen Paketen nicht unterstützt.

Das normale Dashboard-Archiv ist Python-Quellcode und bereits architekturunabhängig.
Es braucht keine zweite ARM64-tar.gz-Datei. Die zusätzlichen Binärpakete sind die
beiden versionierten Container-Images, siehe [GitHub Packages](PACKAGES.md).
Die bestehenden Compose-Dateien können auf beiden Architekturen lokal bauen;
sie erzwingen keine AMD64-Plattform.

## Basisimages zuerst prüfen

`Dockerfile.all-in-one` kopiert Core aus `bitcoin/bitcoin:31.1` und verwendet
`python:3.11-slim-bookworm`. Beide Registry-Indizes boten bei der Prüfung am
1. November 2026 AMD64 und ARM64 an. Das ist eine Prüfung des konkreten Tags,
keine Zusicherung für zukünftige Tags oder unveränderliche Image-Inhalte.

```sh
python tools/check_container_platforms.py --output container-platforms.json
```

Das Werkzeug braucht nur Python-Standardbibliotheken, lädt Registry-Metadaten
und prüft beide benötigten Plattformen. Es liest Versionen aus den Dockerfiles
und gibt keinen Registry-Zugangstoken aus. `--output` speichert auf Wunsch
Image-Digests und Plattform-Digests zur Nachvollziehbarkeit. Es lädt keine Layer.

## Werkzeuge und Downloads

Builds erfolgen in GitHub Actions. Die Release-Jobs laden QEMU für ARM64 über
die festgelegte `setup-qemu-action` und richten Docker Buildx/BuildKit ein.
QEMU wird vor dem Builder eingerichtet. BuildKit lädt die passenden Bitcoin-
und Python-Layer automatisch.
Ein Cross-Compiler oder ein eigener Bitcoin-Quellcode-Build ist nicht nötig.
Auf Hardys Windows-Rechner muss dafür kein Docker Desktop installiert werden.

Lokal sind für einen eigenen Multi-Plattform-Build Docker Engine/Desktop,
Buildx und ARM64-Emulation oder ein nativer ARM64-Builder erforderlich:

```sh
docker buildx build --platform linux/amd64,linux/arm64 -f Dockerfile --output type=oci,dest=dashboard-multiarch.tar .
docker buildx build --platform linux/amd64,linux/arm64 -f Dockerfile.all-in-one --output type=oci,dest=node-multiarch.tar .
```

Diese Befehle setzen einen bereits entsprechend eingerichteten Builder voraus.
Die OCI-Archive sind Build-Ausgaben, keine Pakete für den systemd-Web-Updater.

## Prüfungen und Grenzen

Die CI läuft nativ auf `ubuntu-24.04` und `ubuntu-24.04-arm`. Sie prüft die
Architektur des geladenen Bitcoin-Basisimages und führt dessen `bitcoind --version`
aus. Danach baut und startet sie All-in-one und getrennten Stack einschließlich
RPC-/HTTP-Healthchecks und Admin-Zugriffsschutz. Der Package-Workflow prüft nach
dem Upload AMD64 und ARM64 im gemeinsamen Manifest.

Ein ARM64-Runner ist kein physischer Raspberry Pi: SD-Karten, thermische Grenzen,
RAM-Bedarf, vollständiger Blockchain-Sync und Langzeitbetrieb auf dem Gerät sind
damit nicht geprüft. Die vorhandene Package-Sichtbarkeit bleibt unverändert;
private GHCR-Images benötigen weiterhin eine Anmeldung.

Grundlagen: [Docker Multi-Plattform-Builds](https://docs.docker.com/build/building/multi-platform/)
und [GitHub ARM64-Runner](https://github.blog/changelog/2025-08-07-arm64-hosted-runners-for-public-repositories-are-now-generally-available/).

[Zurück zur Übersicht](../README.md)

Geprüfte Paketlisten für AMD64 und ARM64: [Abhängigkeiten](DEPENDENCIES.md).

Lokale Tests mit Debian ARM64 und einem Raspberry-Pi-3B-Boardmodell sind im [QEMU-Testbericht](QEMU_TESTS.md) dokumentiert. Es handelt sich um Emulation, nicht um physische Hardwaretests.
