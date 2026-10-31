# All-in-one-Installation per Shell

Deutsch | [English](en/SHELL_DOCKER.md)

Das Installationsskript kopiert ausschließlich die für den All-in-one-Stack
benötigten Dateien nach `/opt/bitcoin-node-dashboard`, erzeugt bei der ersten
Installation ein zufälliges Admin-Token und validiert die Compose-Datei.
Vorhandene systemd-Dienste werden weder beendet noch verändert.

## Vorbereitung ohne Start

```bash
tmpdir=$(mktemp -d)
tar -xzf bitcoin-node-dashboard-1.18.1.tar.gz -C "$tmpdir"
sudo sh "$tmpdir/bitcoin-dashboard/installer/install-docker-all-in-one.sh" \
  --public-address 203.0.113.10 \
  --prepare-only
sudo rm -rf -- "$tmpdir"
```

Danach können `/opt/bitcoin-node-dashboard/.env`, die Bitcoin-Konfiguration und
die Portbelegung geprüft werden. `.env` gehört root und hat Modus `0600`.

## Direkte Installation und Start

Nur auf einem neuen Server verwenden, auf dem 8333 und 8787 noch frei sind:

```bash
sudo sh installer/install-docker-all-in-one.sh \
  --public-address 203.0.113.10
```

Bei belegten Ports bricht das Skript ab. Es stoppt keinen vorhandenen Node und
kein vorhandenes Dashboard.

## Status und Logs

```bash
cd /opt/bitcoin-node-dashboard
sudo docker compose --env-file .env -f compose.all-in-one.yaml ps
sudo docker compose --env-file .env -f compose.all-in-one.yaml logs --tail 100
curl -fsS http://127.0.0.1:8787/healthz
```

## Aktualisierung

Ein neues Release zunächst mit `--prepare-only` über dieselbe Installation
kopieren. Eine vorhandene `.env` wird dabei erhalten. Danach:

```bash
cd /opt/bitcoin-node-dashboard
sudo docker compose --env-file .env -f compose.all-in-one.yaml build --pull
sudo docker compose --env-file .env -f compose.all-in-one.yaml up -d
```

Die Bitcoin-Core-Version wird bewusst über `BITCOIN_CORE_VERSION` in `.env`
festgelegt. Sie darf erst nach Prüfung der Zielversion geändert werden.
