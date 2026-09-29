# All-in-one-Docker unter Plesk

Diese Anleitung betrifft ausschließlich die optionale Containerinstallation.
Eine vorhandene systemd-Installation wird nicht automatisch abgeschaltet oder
migriert.

## Empfohlener Weg ohne nginx

Auf einem Plesk-Server ohne nginx wird der Stack über die Shell installiert und
Apache leitet HTTPS an den ausschließlich lokal gebundenen Dashboard-Port
`127.0.0.1:8787` weiter. Bitcoin P2P bleibt direkt über TCP 8333 erreichbar;
RPC-Port 8332 wird nicht veröffentlicht.

Archiv entpacken und zunächst nur vorbereiten:

```bash
tmpdir=$(mktemp -d)
tar -xzf bitcoin-node-dashboard-1.10.0.tar.gz -C "$tmpdir"
sudo sh "$tmpdir/bitcoin-dashboard/installer/install-docker-all-in-one.sh" \
  --public-address 203.0.113.10 \
  --prepare-only
sudo rm -rf -- "$tmpdir"
```

Die Dateien liegen danach unter `/opt/bitcoin-node-dashboard`. Vor dem ersten
Start müssen die Ports 8333 und 8787 frei sein. Der Installer beendet oder
verändert keine bereits laufenden Dienste.

Start:

```bash
cd /opt/bitcoin-node-dashboard
sudo docker compose --env-file .env -f compose.all-in-one.yaml up -d --build
sudo docker compose --env-file .env -f compose.all-in-one.yaml ps
```

In Plesk unter **Websites & Domains → Domain → Apache & nginx Settings** den
Inhalt von `plesk-apache-docker.conf` sowohl bei den zusätzlichen
Apache-Anweisungen für HTTP als auch HTTPS eintragen. Es werden keine
nginx-Direktiven benötigt.

Konfiguration prüfen:

```bash
sudo /usr/local/psa/admin/sbin/httpdmng --reconfigure-domain example.org
sudo apache2ctl configtest
sudo systemctl reload apache2
curl -fsS http://127.0.0.1:8787/healthz
```

## Plesk Docker Stacks

Aktuelle Plesk-Versionen können
[Compose-Dateien als Stack aus einem Webspace laden](https://docs.plesk.com/en-US/obsidian/administrator-guide/plesk-administration/using-docker.75823/).
Weil dieser Stack ein eigenes Dockerfile und weitere Build-Dateien benötigt,
muss das vollständige Projekt vorher in das private Verzeichnis des Webspaces
kopiert werden, beispielsweise nach:

```text
/var/www/vhosts/example.org/private/bitcoin-node-dashboard
```

Nicht unter `httpdocs` ablegen: `.env`, Builddateien und Konfiguration gehören
nicht in ein öffentlich auslieferbares Verzeichnis. Im Projektverzeichnis:

```bash
cp docker.env.example .env
python3 -c 'import secrets; print(secrets.token_urlsafe(32))'
sudo editor .env
chmod 600 .env
```

Das ausgegebene Token bei `ADMIN_TOKEN` eintragen. Anschließend in Plesk unter
**Docker → Stacks → Add Stack → Webspace** die Datei
`compose.all-in-one.yaml` auswählen.

Plesks Docker-Proxyregeln setzen einen laufenden nginx voraus. Auf einem Server
ohne nginx deshalb keine Docker-Proxyregel anlegen, sondern die oben gezeigten
Apache-Direktiven verwenden.

## Betrieb

```bash
cd /opt/bitcoin-node-dashboard
sudo docker compose --env-file .env -f compose.all-in-one.yaml logs --tail 100
sudo docker compose --env-file .env -f compose.all-in-one.yaml restart
sudo docker compose --env-file .env -f compose.all-in-one.yaml down
```

`down` löscht das Datenvolume nicht. `down -v` würde Blockchain und
Dashboard-Historie löschen und darf nicht für normale Updates benutzt werden.
