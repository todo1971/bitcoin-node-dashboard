# Bitcoin Node Dashboard

Ein leichtgewichtiges, nur lesendes Web-Dashboard für Bitcoin Core. Es zeigt
Synchronisation, Peers, Mempool, Gebührenschätzungen, Netzwerkverkehr und den
letzten Block. Zusätzlich prüft es über BTCNodes, ob der öffentliche P2P-Port
aus Sicht eines unabhängigen Crawlers erreichbar ist.

![Python](https://img.shields.io/badge/Python-3.11%2B-3776ab)
![Bitcoin Core](https://img.shields.io/badge/Bitcoin%20Core-31.x-f7931a)

## Eigenschaften

- keine externen Python-Pakete
- feste, ausschließlich lesende RPC-Abfragen über `bitcoin-cli`
- keine universelle RPC-Weiterleitung an den Browser
- lokaler Listener auf `127.0.0.1:8787`
- Bitcoin-RPC und Authentifizierungs-Cookie bleiben serverseitig
- externer Erreichbarkeitsstatus mit fünf Minuten Cache
- responsive Oberfläche für Desktop und Mobilgeräte
- Systemd-Härtung und Reverse-Proxy-Beispiel für Plesk

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
sudo systemctl restart bitcoin-dashboard
```

## HTTP-Endpunkte

| Endpunkt | Zweck |
|---|---|
| `/` | Dashboard |
| `/api/dashboard` | aggregierte Node-Daten als JSON |
| `/healthz` | lokaler Funktions- und RPC-Test |

Es gibt bewusst keinen Endpunkt, über den beliebige RPC-Methoden oder Argumente
an Bitcoin Core übergeben werden können.

## Dokumentation

- [Installation und Betrieb](docs/INSTALLATION.md)
- [Architektur](docs/ARCHITECTURE.md)
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
