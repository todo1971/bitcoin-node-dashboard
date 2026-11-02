# Bitcoin Node Dashboard

Deutsch | [English](README.en.md)

Ein leichtgewichtiges, nur lesendes Web-Dashboard für Bitcoin Core. Es zeigt
Synchronisation, Peers, Mempool, Gebührenschätzungen, Netzwerkverkehr und den
letzten Block. Hinzu kommen Host-Metriken, Alarmierung und die Prüfung auf neue
Bitcoin-Core-Versionen. BTCNodes liefert einen getrennt gekennzeichneten
externen Verzeichnisstatus, keine eigene Live-Portprüfung.

![Python](https://img.shields.io/badge/Python-3.11%2B-3776ab)
![Bitcoin Core](https://img.shields.io/badge/Bitcoin%20Core-31.x-f7931a)

[Benötigte Pakete für Host, Docker, AMD64 und ARM64](docs/DEPENDENCIES.md)

[Lokale ARM64- und Raspberry-Pi-Installationstests mit QEMU](docs/QEMU_TESTS.md)

## Eigenschaften

- Multi-Plattform-Container für AMD64 und ARM64 / Raspberry Pi mit 64-Bit-Linux ([Voraussetzungen und Build](docs/ARM64.md))
- Peer-Software, Service-Flags, Verbindungsarten, Verkehrsraten mit Messabdeckung und letzte 20 erfasste Blöcke ([Details](docs/NODE_INSIGHTS.md))
- Deutsch, Englisch, Spanisch, Portugiesisch (Brasilien), vereinfachtes Chinesisch und Russisch im Dashboard und Adminbereich (Details: [Übersetzungen](docs/TRANSLATIONS.md))

- keine externen Python-Pakete für den Grundbetrieb; Echtzeit-ZMQ benötigt optional `python3-zmq`
- feste, ausschließlich lesende RPC-Abfragen über `bitcoin-cli`
- keine universelle RPC-Weiterleitung an den Browser
- lokaler Listener auf `127.0.0.1:8787`
- Bitcoin-RPC und Authentifizierungs-Cookie bleiben serverseitig
- externer BTCNodes-Verzeichnisstatus mit fünf Minuten Cache; nicht gelistete Nodes gelten nicht als offline
- SQLite-Historie von der 1-Stunden- bis zur Jahresansicht
- Ereignis-Zeitleiste und Hinweise auf bekannte Erfassungslücken; begrenzter RPC-Nachtrag fehlender Blockstatistiken
- Chain-Tips aus `getchaintips` als Momentaufnahme und separat gezählte, lokal beobachtete Block-Trennungen im gewählten Zeitraum
- optionale lokale ZMQ-Ereignisse für Blöcke und Mempool, Minutenzähler und Browser-Liveaktualisierung per SSE mit Abfrage-Fallback
- tägliche UTXO-Statistik sowie historische Blockgrößen und Transaktionsraten
- periodische Mempool-Paketanalyse für Cluster, RBF und CPFP sowie Gebührenbereiche nach Transaktionen und virtuellen Bytes
- getrennte Live-Anzeige für IPv4-, IPv6- und Tor-Peers mit in/out-Verbindungen und den vom Node gemeldeten Adressen; ersatzweise die konfigurierte öffentliche P2P-IP
- Peer-Qualität nach Netz: mediane Verbindungsdauer und Pingzeit, häufigste P2P-Protokollversion, Transport-v2-Anteil und beobachtete beendete Verbindungen der letzten Stunde; keine fremden Peer-Adressen im Browser
- globale Server-IPv6 wird separat angezeigt, auch wenn Bitcoin Core sie noch nicht als P2P-Adresse meldet
- Tor-Onion-Adresse als Knotenkennung im Node-Bereich, klar von einer Bitcoin-Protokoll-ID unterschieden
- automatische Aufbewahrung und Verdichtung der Diagrammdaten
- responsive Oberfläche für Desktop und Mobilgeräte
- kompakte Startübersicht und getrennte Reiter für Netzwerk, Analyse, Historie und System
- Systemd-Härtung und Reverse-Proxy-Beispiel für Plesk
- lokaler Web-Installer für systemd-basierte Linux-Server
- integrierte, abgesicherte Administration unter `/admin`
- editierbare Betriebswerte unter `/admin`; `.env` im Dashboard-State-Verzeichnis, vertrauliche Felder geschützt
- Updates als isolierte systemd-Aufträge mit geprüften Helfern und Rollback
- automatische Dashboard-Updates aus verifizierten GitHub-Release-Assets
- root-eigener Update-Cache unter `/var/cache/bitcoin-dashboard-updates` statt eines Benutzer-Home-Verzeichnisses
- Bitcoin-Core-Upload mit offizieller GPG- und SHA-256-Prüfung
- Docker-Compose für Host-Nodes, getrennte Stacks und optionale All-in-one-Nodes
- CPU-, RAM-, Datenträger- und bitcoind-Laufzeitüberwachung mit Historie
- Alarme mit Karenzzeit, Wiederholsperre, Entwarnung, E-Mail und HTTPS-Webhook
- Versionsvergleich mit der offiziellen Bitcoin-Core-Downloadseite

## Voraussetzungen

- Linux mit Python 3.11 oder neuer
- laufender Bitcoin-Core-Node mit aktiviertem RPC-Server
- lokales `bitcoin-cli`
- Zugriff des Service-Benutzers auf den Bitcoin-RPC-Cookie
- optional Plesk/Apache und eine Subdomain für HTTPS
- optional `python3-zmq` und `zmqpubsequence` für Echtzeitdaten

Die Vorgabewerte passen zur ursprünglichen Installation:

```text
Benutzer:     btc
bitcoin-cli:  /home/btc/bin/bitcoin-cli
Datadir:      /home/btc/bitcoin-data
RPC-Cookie:   /home/btc/bitcoin-core/.bitcoin/.cookie
Webdienst:    127.0.0.1:8787
P2P-Adresse:  217.160.16.224:8333
```

Die Dashboard-Konfiguration liegt unter `/var/lib/bitcoin-dashboard/.env` und ist
im Projektverzeichnis als `.env` verlinkt. Betriebswerte lassen sich über `/admin`
bearbeiten; geschützte Dienst- und RPC-Einstellungen nur lokal als Root.

Für den Containerbetrieb stehen `compose.host-node.yaml`, `compose.yaml` und
`compose.all-in-one.yaml` bereit. Die Unterschiede und sicheren Updatebefehle beschreibt
[docs/DOCKER.md](docs/DOCKER.md).

## Schnellinstallation

Repository auf dem Server auschecken:

```bash
sudo -u btc git clone https://github.com/todo1971/bitcoin-node-dashboard.git \
  /home/btc/bitcoin-dashboard
```

Konfiguration und Service mit dem Bootstrap aus dem zuvor geprüften
Release-Archiv einrichten (nicht aus dem `btc`-schreibbaren Checkout):

```bash
tmpdir=$(mktemp -d)
tar -xzf ./bitcoin-node-dashboard-1.21.3.tar.gz -C "$tmpdir"
sudo sh "$tmpdir/bitcoin-dashboard/installer/bootstrap-admin.sh"
rm -rf -- "$tmpdir"
sudo systemctl enable --now bitcoin-dashboard
```

Lokaler Test:

```bash
curl -fsS http://127.0.0.1:8787/healthz
curl -fsS http://127.0.0.1:8787/api/dashboard | python3 -m json.tool
```

Eine vollständige Anleitung einschließlich Plesk-Konfiguration steht in
[docs/INSTALLATION.md](docs/INSTALLATION.md).

## Aktualisierung

```bash
cd /home/btc/bitcoin-dashboard
sudo -u btc git pull --ff-only
sudo cp bitcoin-dashboard.service /etc/systemd/system/bitcoin-dashboard.service
sudo systemctl daemon-reload
sudo systemctl restart bitcoin-dashboard
```

## HTTP-Endpunkte

| Endpunkt | Zweck |
|---|---|
| `/` | Dashboard |
| `/api/dashboard` | aggregierte Node-Daten als JSON |
| `/api/history?range=24h` | verdichtete historische Messwerte |
| `/api/timeline?range=24h` | Ereignisse und Datenqualitäts-Hinweise im gewählten Zeitraum |
| `/api/analytics?range=24h` | Block-, UTXO- und Mempool-Analysedaten |
| `/api/alerts` | derzeit aktive Alarme |
| `/api/admin/upload/bitcoin` | geschützter Bitcoin-Core-Archivupload |
| `/api/admin/logs/dashboard` und `/api/admin/logs/bitcoin` | letzte Update-Logzeilen, nur mit Admin-Anmeldung |
| `/api/admin/config` | erlaubte Dashboard-Betriebswerte anzeigen und speichern, nur mit Admin-Anmeldung |
| `/admin` | passwortgeschützte Administration |
| `/healthz` | lokaler Funktions- und RPC-Test |

Es gibt bewusst keinen Endpunkt, über den beliebige RPC-Methoden oder Argumente
an Bitcoin Core übergeben werden können.

## Dokumentation

- [Installation und Betrieb](docs/INSTALLATION.md)
- [Architektur](docs/ARCHITECTURE.md)
- [Datenbank und Datenmenge](docs/DATABASE.md)
- [Web-Installation](docs/WEB_INSTALLATION.md)
- [Docker-Betrieb](docs/DOCKER.md)
- [All-in-one per Shell](docs/SHELL_DOCKER.md)
- [All-in-one unter Plesk](docs/PLESK_DOCKER.md)
- [Sichere Updates](docs/UPDATES.md)
- [Alarme und Systemüberwachung](docs/ALERTS.md)
- [Konfiguration und Migration zur Dashboard-.env](docs/CONFIGURATION.md)
- [Echtzeit über lokales ZMQ und SSE](docs/REALTIME.md)
- [Sicherheitskonzept](docs/SECURITY.md)
- [Roadmap](docs/ROADMAP.md)
- [Änderungen](CHANGELOG.md)
- [Sprachen und Übersetzungen](docs/TRANSLATIONS.md)
- [Testumfang und öffentliche Updates](docs/TESTING.md)
- [GitHub Packages / Container-Images](docs/PACKAGES.md)

## Entwicklung und Tests

```bash
python3 -m py_compile app.py
python3 -m unittest discover -s tests -v
python3 tools/check_documentation.py
```

## Lizenz

Copyright (C) 2026 Hardy (todo1971) <hb@308-arms.de>. Der eigene Projektcode und die Dokumentation
stehen unter der **GNU General Public License, Version 3 ausschließlich**
(`GPL-3.0-only`). Vollständiger Text: [LICENSE](LICENSE); Hinweise: [NOTICE](NOTICE).
Das Programm wird ohne Gewährleistung bereitgestellt. Drittanbieterkomponenten
wie Bitcoin Core, Python und Basisimages behalten ihre jeweiligen Lizenzen.
