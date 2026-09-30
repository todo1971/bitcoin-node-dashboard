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
| `BITCOIN_RPC_URL` | leer | optionaler direkter JSON-RPC-Endpunkt, insbesondere für Docker |
| `BITCOIN_DATADIR` | `/home/btc/bitcoin-data` | Bitcoin-Datadir |
| `BITCOIN_COOKIE` | `/home/btc/bitcoin-core/.bitcoin/.cookie` | RPC-Cookie |
| `PUBLIC_NODE_ADDRESS` | `217.160.16.224` | öffentliche P2P-Adresse |
| `PUBLIC_NODE_PORT` | `8333` | öffentlicher P2P-Port |
| `EXTERNAL_CACHE_SECONDS` | `300` | Cache externer Crawler-Daten |
| `DATABASE_PATH` | `/var/lib/bitcoin-dashboard/history.sqlite3` | SQLite-Datei |
| `MEMPOOL_ANALYSIS_SECONDS` | `300` | Mindestabstand der Mempool-Paketanalyse |
| `UTXO_SAMPLE_SECONDS` | `86400` | Mindestabstand der UTXO-Messung |
| `SAMPLE_INTERVAL_SECONDS` | `60` | Abstand der Messungen |
| `HISTORY_RETENTION_DAYS` | `365` | Aufbewahrungsdauer |
| `VERSION_CHECK_SECONDS` | `21600` | Cache der Versionsprüfung, mindestens eine Stunde |
| `ALERT_EMAIL` | leer | Empfänger für Versand über lokales `sendmail` |
| `ALERT_WEBHOOK_URL` | leer | optionaler HTTPS-Webhook für JSON-Alarme |
| `ALERT_GRACE_SECONDS` | `300` | Karenzzeit für allgemeine Alarme |
| `ALERT_NO_INBOUND_SECONDS` | `900` | Karenzzeit für fehlende Inbound-Peers |
| `ALERT_COOLDOWN_SECONDS` | `21600` | Abstand wiederholter Benachrichtigungen |
| `SYNC_LAG_BLOCKS` | `3` | maximal tolerierter Abstand zu den Headern |
| `DISK_MAX_USED_PERCENT` | `90` | Alarmgrenze für belegten Datenträgerplatz |
| `MEMORY_MAX_USED_PERCENT` | `90` | Alarmgrenze für RAM-Auslastung |
| `ADMIN_TOKEN` | leer | mindestens 32 Zeichen; wird durch den Admin-Bootstrap erzeugt |
| `ADMIN_UPDATES_ENABLED` | `1` | bei Docker `0`, da Updates extern verwaltet werden |
| `DASHBOARD_GITHUB_REPOSITORY` | `todo1971/bitcoin-node-dashboard` | Quelle für Dashboard-Releases |
| `DASHBOARD_GITHUB_TOKEN` | leer | nur lesendes Fine-grained Token; für private Repositorys erforderlich |
| `BITCOIN_UPLOAD_DIR` | `/var/lib/bitcoin-dashboard/bitcoin-core-upload` | isolierter Zwischenordner für Core-Uploads |
| `BITCOIN_UPLOAD_MAX_BYTES` | `209715200` | maximales Uploadvolumen (200 MiB) |

## 3. Systemd-Service installieren

```bash
sudo cp /home/btc/bitcoin-dashboard/bitcoin-dashboard.service \
  /etc/systemd/system/bitcoin-dashboard.service
sudo systemctl daemon-reload
sudo systemctl enable --now bitcoin-dashboard
```

Die integrierte Administration samt eng begrenzter Update-Berechtigungen wird
anschließend aus einem temporär entpackten Release eingerichtet. Unter
Das Release-Archiv liegt für diesen einmaligen Schritt im aktuellen Verzeichnis:

```bash
tmpdir=$(mktemp -d)
sudo tar -xzf ./bitcoin-node-dashboard-1.11.8.tar.gz -C "$tmpdir"
sudo sh "$tmpdir/bitcoin-dashboard/installer/bootstrap-admin.sh"
sudo rm -rf -- "$tmpdir"
```

`StateDirectory=bitcoin-dashboard` erzeugt automatisch das beschreibbare
Verzeichnis `/var/lib/bitcoin-dashboard` mit passenden Rechten für `btc`.

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
5. Den Inhalt von `plesk-nginx.conf` unter **Additional nginx directives**
   eintragen. Dadurch sind Bitcoin-Core-Uploads bis 200 MB erlaubt.
6. Plesk-Proxy-Modus aktiviert lassen.

Port 8787 bleibt ausschließlich an `127.0.0.1` gebunden. Weder Port 8787 noch
Bitcoin-RPC-Port 8332 dürfen in der Firewall öffentlich freigegeben werden.

Die vollständige Einrichtung des Fine-grained GitHub-Tokens für automatische
Dashboard-Updates steht in [UPDATES.md](UPDATES.md#fine-grained-github-token-einrichten).

## 6. Aktualisieren

```bash
cd /home/btc/bitcoin-dashboard
sudo -u btc git pull --ff-only
sudo cp bitcoin-dashboard.service /etc/systemd/system/bitcoin-dashboard.service
sudo systemctl daemon-reload
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

Alarmzustände und Benachrichtigungskanäle sind in [ALERTS.md](ALERTS.md)
beschrieben.

Die Datenbank kann separat geprüft werden:

```bash
sudo -u btc sqlite3 /var/lib/bitcoin-dashboard/history.sqlite3 \
  'SELECT COUNT(*), MIN(sampled_at), MAX(sampled_at) FROM node_samples;'
```
