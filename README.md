# Bitcoin Node Dashboard

Ein leichtgewichtiges, nur lesendes Web-Dashboard für Bitcoin Core. Es zeigt
Synchronisation, Peers, Mempool, Gebührenschätzungen, Netzwerkverkehr und den
letzten Block. Hinzu kommen Host-Metriken, Alarmierung und die Prüfung auf neue
Bitcoin-Core-Versionen. Über BTCNodes wird außerdem geprüft, ob der öffentliche
P2P-Port aus Sicht eines unabhängigen Crawlers erreichbar ist.

![Python](https://img.shields.io/badge/Python-3.11%2B-3776ab)
![Bitcoin Core](https://img.shields.io/badge/Bitcoin%20Core-31.x-f7931a)

## Eigenschaften

- keine externen Python-Pakete
- feste, ausschließlich lesende RPC-Abfragen über `bitcoin-cli`
- keine universelle RPC-Weiterleitung an den Browser
- lokaler Listener auf `127.0.0.1:8787`
- Bitcoin-RPC und Authentifizierungs-Cookie bleiben serverseitig
- externer Erreichbarkeitsstatus mit fünf Minuten Cache
- SQLite-Historie von der 1-Stunden- bis zur Jahresansicht
- tägliche UTXO-Statistik sowie historische Blockgrößen und Transaktionsraten
- periodische Mempool-Paketanalyse für Cluster, RBF und CPFP
- automatische Aufbewahrung und Verdichtung der Diagrammdaten
- responsive Oberfläche für Desktop und Mobilgeräte
- Systemd-Härtung und Reverse-Proxy-Beispiel für Plesk
- lokaler Web-Installer für systemd-basierte Linux-Server
- integrierte, abgesicherte Administration unter `/admin`
- Updates als isolierte systemd-Aufträge mit geprüften Helfern und Rollback
- automatische Dashboard-Updates aus verifizierten GitHub-Release-Assets
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

Die Vorgabewerte passen zur ursprünglichen Installation:

```text
Benutzer:     btc
bitcoin-cli:  /home/btc/bin/bitcoin-cli
Datadir:      /home/btc/bitcoin-data
RPC-Cookie:   /home/btc/bitcoin-core/.bitcoin/.cookie
Webdienst:    127.0.0.1:8787
P2P-Adresse:  217.160.16.224:8333
```

Alle Werte lassen sich über `/etc/default/bitcoin-dashboard` ändern.

Für den Containerbetrieb stehen `compose.host-node.yaml`, `compose.yaml` und
`compose.all-in-one.yaml` bereit. Die Unterschiede und sicheren Updatebefehle beschreibt
[docs/DOCKER.md](docs/DOCKER.md).

## Schnellinstallation

Repository auf dem Server auschecken:

```bash
sudo -u btc git clone https://github.com/todo1971/bitcoin-node-dashboard.git \
  /home/btc/bitcoin-dashboard
```

Service-Konfiguration installieren:

```bash
sudo cp /home/btc/bitcoin-dashboard/bitcoin-dashboard.env.example \
  /etc/default/bitcoin-dashboard
sudo chmod 0640 /etc/default/bitcoin-dashboard

sudo cp /home/btc/bitcoin-dashboard/bitcoin-dashboard.service \
  /etc/systemd/system/bitcoin-dashboard.service

sudo systemctl daemon-reload
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
| `/api/analytics?range=24h` | Block-, UTXO- und Mempool-Analysedaten |
| `/api/alerts` | derzeit aktive Alarme |
| `/api/admin/upload/bitcoin` | geschützter Bitcoin-Core-Archivupload |
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
- [Sicherheitskonzept](docs/SECURITY.md)
- [Roadmap](docs/ROADMAP.md)
- [Änderungen](CHANGELOG.md)

## Entwicklung und Tests

```bash
python3 -m py_compile app.py
python3 -m unittest discover -s tests -v
```

## Lizenz

Noch nicht festgelegt. Vor einer Veröffentlichung sollte bewusst entschieden
werden, ob das Projekt beispielsweise unter MIT, Apache-2.0 oder proprietär
bereitgestellt werden soll.
