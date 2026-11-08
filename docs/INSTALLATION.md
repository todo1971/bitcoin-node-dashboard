# Installation und Betrieb

Deutsch | [English](en/INSTALLATION.md)

## Voraussetzungen und Einrichtung

Linux mit systemd, Python 3.11 oder neuer und laufendem Bitcoin Core mit eigenem Dienstkonto. [Benötigte Pakete](DEPENDENCIES.md). Bei lokaler Migration muss `bitcoind.service` einen expliziten `-conf`-Pfad verwenden. Vorher Backup erstellen.

Die vollständigen Installations- und Migrationsbefehle stehen unter [Sicherheit](SECURITY.md). Sie richten root-eigenen Code unter `/opt/bitcoin-dashboard`, das Konto `bitcoin-dashboard`, eine eigene RPC-Leseberechtigung und die geschützten Root-Helfer ein. Der bestehende Datadir und die Historie bleiben erhalten. Die erste lokale Umstellung startet beide Dienste neu.

## Konfiguration

Die aktive Dashboard-Konfiguration liegt unter `/var/lib/bitcoin-dashboard/.env`, verlinkt aus `/opt/bitcoin-dashboard/.env`. Rechte: `bitcoin-dashboard:bitcoin-dashboard`, 0600. Betriebswerte sind im Adminbereich editierbar. Updatequelle und optionales GitHub-Token für Root-Updates ausschließlich in `/etc/bitcoin-dashboard-updater.conf` pflegen. Pfade in dieser Tabelle beschreiben die migrierte Host-Installation; Datadir und Netzwerkadresse an den eigenen Node anpassen.

| Variable | Vorgabe | Bedeutung |
|---|---|---|
| `DASHBOARD_HOST` | `127.0.0.1` | lokale Bind-Adresse |
| `DASHBOARD_PORT` | `8787` | lokaler HTTP-Port |
| `DASHBOARD_CACHE_SECONDS` | `10` | Cache lokaler RPC-Daten |
| `BITCOIN_CLI` | `/usr/local/lib/bitcoin-core/bin/bitcoin-cli` | CLI-Programm |
| `BITCOIN_RPC_URL` | leer | optionaler direkter JSON-RPC-Endpunkt, insbesondere für Docker |
| `BITCOIN_DATADIR` | `/home/btc/bitcoin-data` | Bitcoin-Datadir |
| `BITCOIN_COOKIE` | `/var/lib/bitcoin-dashboard/rpc.auth` | RPC-Cookie |
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

## Betrieb prüfen

```bash
sudo systemctl status bitcoin-dashboard --no-pager
sudo journalctl -u bitcoin-dashboard -n 50 --no-pager
curl -fsS http://127.0.0.1:8787/healthz
curl -fsS http://127.0.0.1:8787/api/dashboard | python3 -m json.tool
sudo -u bitcoin-dashboard sqlite3 /var/lib/bitcoin-dashboard/history.sqlite3 \
  'SELECT COUNT(*), MIN(sampled_at), MAX(sampled_at) FROM node_samples;'
```

Bei Status 503 zuerst Core-Zustand und RPC-Zugang prüfen. Admin-Zugangsdaten lokal in der geschützten `.env` verwalten. Keine Zugangsdaten in Logs oder Git kopieren.

## HTTPS und Updates

Plesk-Subdomain anlegen, Zertifikat und HTTPS-Weiterleitung aktivieren. `plesk-apache.conf` in die zusätzlichen Apache-Direktiven übernehmen. Nur bei tatsächlich installiertem nginx auch `plesk-nginx.conf` verwenden. Port 8787 bleibt lokal; RPC-Port 8332 niemals öffentlich freigeben.

[Updates](UPDATES.md), [Alarme](ALERTS.md), [Web-Installation](WEB_INSTALLATION.md) und [Containerbetrieb](DOCKER.md).
