# GitHub Packages

Deutsch | [English](en/PACKAGES.md)

Zu jedem veröffentlichten stabilen Release baut der Workflow
`Publish GitHub Packages` automatisch zwei Multi-Plattform-Images für Linux/AMD64 und Linux/ARM64 aus dem exakten
Release-Tag und veröffentlicht sie in der GitHub Container Registry:

- `ghcr.io/todo1971/bitcoin-node-dashboard:VERSION`
- `ghcr.io/todo1971/bitcoin-node-dashboard-all-in-one:VERSION`

Es gibt bewusst nur feste Versionstags, kein automatisch veränderliches `latest`.
Das Dashboard-Image benötigt einen vorhandenen Node. Das All-in-one-Image enthält
Bitcoin Core und Dashboard; seine Core-Version bleibt unabhängig von der
Dashboard-Version im Dockerfile festgelegt.

Unter **Actions → Publish GitHub Packages → Run workflow** können fehlende Images
für ein bereits veröffentlichtes stabiles Tag nachgebaut werden. Der Workflow
prüft Release-Status, Versionsgleichheit im Code, Kompilierung und Unit-Tests.
Er verwendet GitHubs kurzlebiges `GITHUB_TOKEN` mit `packages: write`; ein eigener
Registry-Token muss nicht als Repository-Secret eingerichtet werden.

Beispiel:

```bash
docker pull ghcr.io/todo1971/bitcoin-node-dashboard:1.21.1
docker pull ghcr.io/todo1971/bitcoin-node-dashboard-all-in-one:1.21.1
```

Images ersetzen nicht die Konfiguration, Volumes und Portbindungen der
[Docker-Anleitung](DOCKER.md). Die mitgelieferten Compose-Dateien bauen weiterhin
aus dem lokalen Quellcode. Wer veröffentlichte Images verwendet, muss im eigenen
Stack den passenden `image:`-Wert verwenden und den `build:`-Abschnitt entfernen.
RPC-Port 8332 bleibt intern, der Dashboard-Port bleibt am Host lokal gebunden.

Die Pakete sind mit dem Repository verknüpft. Ihre Sichtbarkeit wird nicht
automatisch von diesem Workflow geändert. Private Pakete erfordern eine
Registry-Anmeldung mit Leserechten. Öffentlich sichtbare Pakete lassen sich ohne
Token herunterladen. Vor einer allgemeinen Veröffentlichung die Sichtbarkeit
beider Pakete separat in deren Package-Einstellungen prüfen.

Der erfolgreiche Upload und die Manifest-Digests stehen im Actions-Lauf. Die
Release-Assets `tar.gz` und `tar.gz.sha256` bleiben zusätzlich für den
systemd-Dashboard-Updater erhalten; dieser lädt keine Container-Images.

ARM64-Voraussetzungen und Build-Werkzeuge: [Raspberry Pi / ARM64](ARM64.md).

Vollständige Laufzeit- und Paketvoraussetzungen: [Abhängigkeiten](DEPENDENCIES.md).
