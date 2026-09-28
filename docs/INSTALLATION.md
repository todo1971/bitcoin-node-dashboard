# Installation und Betrieb

## 1. Repository installieren

```bash
sudo install -d -o btc -g btc -m 0750 /home/btc/bitcoin-dashboard
sudo -u btc git clone https://github.com/todo1971/bitcoin-node-dashboard.git \
  /home/btc/bitcoin-dashboard
```

Da das Repository privat ist, benötigt der Server einen GitHub Deploy Key oder
eine andere GitHub-Anmeldung. Alternativ kann ein Release-Archiv nach
`/home/btc/bitcoin-dashboard` entpackt werden.

## 2. Umgebung konfigurieren

```bash
sudo cp /home/btc/bitcoin-dashboard/bitcoin-dashboard.env.example \
  /etc/default/bitcoin-dashboard
sudo chown root:root /etc/default/bitcoin-dashboard
sudo chmod 0640 /etc/default/bitcoin-dashboard
sudo editor /etc/default/bitcoin-dashboard
```

Verfügbare Einstellungen:

| Variable | Vorgabe | Bedeutung |
|---|---|---|
| `DASHBOARD_HOST` | `127.0.0.1` | lokale Bind-Adresse |
| `DASHBOARD_PORT` | `8787` | lokaler HTTP-Port |
| `DASHBOARD_CACHE_SECONDS` | `10` | Cache lokaler RPC-Daten |
| `BITCOIN_CLI` | `/home/btc/bin/bitcoin-cli` | CLI-Programm |
| `BITCOIN_DATADIR` | `/home/btc/bitcoin-data` | Bitcoin-Datadir |
| `BITCOIN_COOKIE` | `/home/btc/bitcoin-core/.bitcoin/.cookie` | RPC-Cookie |
| `PUBLIC_NODE_ADDRESS` | `217.160.16.224` | öffentliche P2P-Adresse |
| `PUBLIC_NODE_PORT` | `8333` | öffentlicher P2P-Port |
| `EXTERNAL_CACHE_SECONDS` | `300` | Cache externer Crawler-Daten |

## 3. Systemd-Service installieren

```bash
sudo cp /home/btc/bitcoin-dashboard/bitcoin-dashboard.service \
  /etc/systemd/system/bitcoin-dashboard.service
sudo systemctl daemon-reload
sudo systemctl enable --now bitcoin-dashboard
```

Status und Logs:

```bash
sudo systemctl status bitcoin-dashboard --no-pager
sudo journalctl -u bitcoin-dashboard -f
```

## 4. Lokal testen

```bash
curl -fsS http://127.0.0.1:8787/healthz
curl -fsS http://127.0.0.1:8787/api/dashboard | python3 -m json.tool
```

## 5. Subdomain in Plesk

1. Subdomain anlegen, beispielsweise `node.example.de`.
2. Let's Encrypt aktivieren und HTTP auf HTTPS umleiten.
3. **Apache & nginx Settings** öffnen.
4. Den Inhalt von `plesk-apache.conf` unter **Additional Apache directives**
   für HTTP und HTTPS eintragen.
5. Plesk-Proxy-Modus aktiviert lassen.

Port 8787 bleibt ausschließlich an `127.0.0.1` gebunden. Weder Port 8787 noch
Bitcoin-RPC-Port 8332 dürfen in der Firewall öffentlich freigegeben werden.

## 6. Aktualisieren

```bash
cd /home/btc/bitcoin-dashboard
sudo -u btc git pull --ff-only
sudo systemctl restart bitcoin-dashboard
curl -fsS http://127.0.0.1:8787/healthz
```

## 7. Fehlerdiagnose

```bash
sudo journalctl -u bitcoin-dashboard --since '30 minutes ago'
sudo -u btc /home/btc/bin/bitcoin-cli \
  -datadir=/home/btc/bitcoin-data \
  -rpccookiefile=/home/btc/bitcoin-core/.bitcoin/.cookie \
  getblockchaininfo
```

Wenn `/healthz` den Status 503 liefert, zuerst Cookie-Pfad, Dateirechte,
Datadir und den Zustand von `bitcoind` prüfen.
