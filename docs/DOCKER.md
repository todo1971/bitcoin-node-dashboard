# Docker-Betrieb

Das Repository enthält zwei getrennte Compose-Varianten. Sie dürfen nicht
gleichzeitig gestartet werden.

## Vorhandenen Host-Node überwachen

`compose.host-node.yaml` ist für den bestehenden Server vorgesehen. bitcoind
läuft weiterhin als systemd-Dienst unter `btc`; nur das Dashboard wird in einen
Container verschoben. Der Container verwendet Host-Netzwerkbetrieb, bindet aber
weiterhin ausschließlich an `127.0.0.1:8787`. Blockchain-Verzeichnis und
RPC-Cookie werden nur lesbar eingebunden.

Die UID und GID des Containers müssen zum Host-Benutzer passen:

```bash
id btc
```

Auf dem aktuellen Server sind beide Werte `1010`. Konfiguration erzeugen:

```bash
cd /home/btc/bitcoin-dashboard
cp docker.env.example .env
python3 -c 'import secrets; print(secrets.token_urlsafe(32))'
sudo editor .env
```

Das erzeugte Token bei `ADMIN_TOKEN` eintragen. `.env` bleibt durch
`.gitignore` vom Repository ausgeschlossen. Vor dem Wechsel darf nicht zugleich
der systemd-Dashboarddienst laufen:

```bash
sudo systemctl disable --now bitcoin-dashboard
sudo install -d -o 1010 -g 1010 -m 0750 /var/lib/bitcoin-dashboard
sudo docker compose --env-file .env -f compose.host-node.yaml build --pull
sudo docker compose --env-file .env -f compose.host-node.yaml up -d
sudo docker compose --env-file .env -f compose.host-node.yaml ps
```

Bitcoin Core muss RPC an `127.0.0.1:8332` anbieten. Der RPC-Port darf nicht in
der Firewall oder im Reverse Proxy veröffentlicht werden.

## Vollständiger neuer Docker-Stack

`compose.yaml` startet Bitcoin Core und Dashboard gemeinsam. Der P2P-Port 8333
wird veröffentlicht; RPC-Port 8332 bleibt ausschließlich im privaten
Compose-Netz `172.30.0.0/24`. Das Dashboard authentifiziert sich mit dem
Cookie aus dem gemeinsamen, nur lesbar eingebundenen Bitcoin-Datenvolume.

```bash
cp docker.env.example .env
sudo editor .env
sudo docker compose --env-file .env config
sudo docker compose --env-file .env up -d --build
sudo docker compose --env-file .env ps
```

Diese Variante verwendet das Image `bitcoin/bitcoin` mit einer festen Version.
Das Image weist selbst darauf hin, dass es kein vom Bitcoin-Core-Projekt
offiziell unterstütztes Produktionsimage ist. Vor dem Einsatz muss dieses
Vertrauensmodell bewusst akzeptiert oder das Image intern reproduzierbar gebaut
und in einer eigenen Registry verwaltet werden.

Die Vorgabekonfiguration ist ein Pruned Node mit ungefähr 20 GB Zielgröße und
deaktivierter Wallet. Ein bestehendes Host-Datadir darf niemals gleichzeitig
vom Hostprozess und einem Bitcoin-Container geöffnet werden.

## Updates

Container erhalten absichtlich weder `/var/run/docker.sock` noch Zugriff auf
Host-systemd oder `sudo`. Deshalb zeigt `/admin` im Containerbetrieb nur den
Versionsstatus und erklärt, dass Updates extern verwaltet werden.

Dashboard aktualisieren:

```bash
git pull --ff-only
sudo docker compose --env-file .env -f compose.host-node.yaml build --pull
sudo docker compose --env-file .env -f compose.host-node.yaml up -d
```

Beim vollständigen Stack wird `BITCOIN_CORE_VERSION` in `.env` bewusst auf die
geprüfte Zielversion gesetzt. Anschließend:

```bash
sudo docker compose --env-file .env pull bitcoin-core
sudo docker compose --env-file .env up -d bitcoin-core dashboard
```

Keine automatischen Aktualisierungen mit `latest` verwenden. Major-Releases
können Verhalten, Konfiguration und Datenformate ändern.

## Betrieb und Diagnose

```bash
sudo docker compose --env-file .env ps
sudo docker compose --env-file .env logs --tail 100 dashboard
sudo docker compose --env-file .env logs --tail 100 bitcoin-core
curl -fsS http://127.0.0.1:8787/healthz
```

Persistente Daten liegen in `bitcoin-data` und `dashboard-data`. Volumes müssen
separat gesichert werden; `docker compose down` ohne `-v` lässt sie bestehen.
`docker compose down -v` würde sie dagegen löschen und gehört nicht in den
normalen Updateablauf.
